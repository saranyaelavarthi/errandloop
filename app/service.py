from copy import deepcopy
import re
import uuid
from .matching import find_matches
from .auth import authorize, ref


class Conflict(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identifier():
    return uuid.uuid4().hex[:16]


def text(value, label, maximum=180):
    require(isinstance(value, str) and 0 < len(value.strip()) <= maximum,
            f'{label} must contain 1–{maximum} characters.')
    require(not re.search(r'[\x00-\x08\x0b-\x1f]', value), f'{label} contains unsupported characters.')
    return value.strip()


def integer(value, label, low, high):
    require(type(value) is int and low <= value <= high, f'{label} must be between {low} and {high}.')
    return value


def record(state, member, message, now):
    state['activity'].insert(0, {'id': identifier(), 'member': member, 'message': message, 'at': now})
    state['activity'] = state['activity'][:100]


def release(state, loop, now, cancelled_member=None):
    for edge in loop['edges']:
        trip = next(t for t in state['trips'] if t['id'] == edge['trip'])
        request = next(r for r in state['requests'] if r['id'] == edge['request'])
        trip['status'] = 'cancelled' if trip['member'] == cancelled_member else ('open' if trip['depart'] > now else 'expired')
        request['status'] = 'open' if request['deadline'] > now else 'expired'


def expire(state, now):
    changed = False
    for loop in state['loops']:
        if loop['status'] == 'awaiting' and loop['expires'] <= now:
            loop['status'] = 'expired'
            release(state, loop, now)
            record(state, 'system', 'An unconfirmed circle expired. Available requests were reopened.', now)
            changed = True
    for t in state['trips']:
        if t['status'] == 'open' and t['depart'] <= now:
            t['status'] = 'expired'; changed = True
    for r in state['requests']:
        if r['status'] == 'open' and r['deadline'] <= now:
            r['status'] = 'expired'; changed = True
    return changed


def view(state, now, member='you'):
    # A copy also protects callers from mutating storage through a returned response.
    result = deepcopy(state)
    result.pop('operations', None)
    result.pop('accounts', None)
    result['matching'] = find_matches(state, now)
    result['now'] = now
    result['actor'] = member
    result['metrics'] = {'completed': sum(l['status'] == 'completed' for l in state['loops']),
                         'handovers': sum(e.get('received', False) for l in state['loops'] for e in l['edges'])}
    return result


def mutate(state, member, command, data, now):
    require(isinstance(data, dict), 'Request must be a JSON object.')
    require(any(m['id'] == member for m in state['members']), 'Unknown member.')
    group = state.get('group', {}).get('id', 'courtyard')
    def check(member, action, kind, rid, attrs):
        return authorize(member, action, kind, rid, attrs, group=group)
    op = text(data.get('operation'), 'Operation ID', 80)
    require(re.fullmatch(r'[A-Za-z0-9-]+', op), 'Invalid operation ID.')
    previous = next((x for x in state['operations'] if x['id'] == op and x['member'] == member), None)
    if previous:
        require(previous['command'] == command, 'Operation ID already belongs to another action.')
        return False
    if data.get('version') != state['version']:
        raise Conflict('The board changed. We refreshed it; please review and try again.')
    if command in ('trip', 'request'):
        check(member, 'post', 'Group', group, {'id': group})
        collection = state['trips' if command == 'trip' else 'requests']
        require(not any(x['member'] == member and x['status'] in ('open', 'reserved', 'active') for x in collection),
                'Finish or cancel your existing post before adding another.')
        destination = data.get('destination')
        require(destination in [p['id'] for p in state['places']], 'Choose a listed destination.')
        item = {'id': identifier(), 'member': member, 'destination': destination, 'status': 'open',
                'note': text(data.get('note') or ('Meet at ' + state.get('group', {}).get('meeting', 'the courtyard') + '.'), 'Note')}
        if command == 'trip':
            item.update(depart=integer(data.get('depart'), 'Departure', now + 60, now + 86400),
                        returns=integer(data.get('returns'), 'Return', now + 120, now + 86400),
                        capacity=integer(data.get('capacity'), 'Capacity', 1, 5))
            require(item['returns'] > item['depart'], 'Return time must be after departure.')
        else:
            item.update(item=text(data.get('item'), 'Pickup description', 90),
                        ready=integer(data.get('ready'), 'Ready time', now - 86400, now + 86400),
                        deadline=integer(data.get('deadline'), 'Deadline', now + 60, now + 86400),
                        units=integer(data.get('units'), 'Bag space', 1, 5))
            require(item['ready'] < item['deadline'], 'Ready time must be before the deadline.')
        collection.append(item)
        record(state, member, 'Posted a planned trip.' if command == 'trip' else 'Posted a pickup request.', now)
    elif command == 'cancel_post':
        collection = state['trips'] + state['requests']
        post = next((p for p in collection if p['id'] == data.get('id')), None)
        require(post is not None, 'Post not found.')
        check(member, command, 'Post', post['id'], {'owner': ref('Member', post['member']), 'group': group})
        require(post['status'] == 'open', 'A matched post must be cancelled through its circle.')
        post['status'] = 'cancelled'
        record(state, member, 'Removed an open post.', now)
    elif command == 'propose':
        candidate = next((c for c in find_matches(state, now)['candidates'] if c['id'] == data.get('id')), None)
        require(candidate is not None, 'This circle is no longer available. Refresh the board.')
        check(member, command, 'Loop', candidate['id'],
                  {'members': [ref('Member', m) for m in candidate['members']], 'group': group})
        loop = deepcopy(candidate)
        loop.update(id=identifier(), status='awaiting', accepted=[member], created=now)
        for edge in loop['edges']:
            edge.update(collected=False, received=False)
            next(t for t in state['trips'] if t['id'] == edge['trip'])['status'] = 'reserved'
            next(r for r in state['requests'] if r['id'] == edge['request'])['status'] = 'reserved'
        state['loops'].insert(0, loop)
        record(state, member, f"Proposed a {len(loop['members'])}-person circle and accepted their part.", now)
    else:
        loop = next((l for l in state['loops'] if l['id'] == data.get('id')), None)
        require(loop is not None, 'Circle not found.')
        if command in ('accept', 'decline', 'cancel_loop'):
            check(member, command, 'Loop', loop['id'],
                      {'members': [ref('Member', m) for m in loop['members']], 'group': group})
            if command == 'accept':
                require(loop['status'] == 'awaiting' and loop['expires'] > now, 'This circle is no longer awaiting replies.')
                if member not in loop['accepted']:
                    loop['accepted'].append(member)
                    record(state, member, 'Accepted their part of the circle.', now)
                if set(loop['accepted']) == set(loop['members']):
                    loop['status'] = 'active'
                    for edge in loop['edges']:
                        next(t for t in state['trips'] if t['id'] == edge['trip'])['status'] = 'active'
                        next(r for r in state['requests'] if r['id'] == edge['request'])['status'] = 'active'
                    record(state, 'system', 'Everyone agreed. The circle is ready to go.', now)
            else:
                require(loop['status'] in ('awaiting', 'active'), 'This circle cannot be cancelled.')
                require(command != 'decline' or loop['status'] == 'awaiting', 'Use cancellation for an active circle.')
                if any(e['collected'] for e in loop['edges']):
                    # Never rematch goods already in somebody's possession.
                    loop['status'] = 'needs_handoff'
                    record(state, member, 'Reported a problem after collection. Finish the existing handovers; no automatic rematch.', now)
                else:
                    loop['status'] = 'cancelled'
                    release(state, loop, now, cancelled_member=member)
                    record(state, member, 'Left the circle. Their trip was removed; remaining requests reopened.', now)
        elif command in ('collected', 'received'):
            edge = next((e for e in loop['edges'] if e['request'] == data.get('request')), None)
            require(edge is not None, 'Handover not found.')
            check(member, command, 'Handover', edge['request'],
                      {'giver': ref('Member', edge['giver']), 'receiver': ref('Member', edge['receiver']), 'group': group})
            require(loop['status'] in ('active', 'needs_handoff'), 'All members must accept before collection.')
            if command == 'received':
                require(edge['collected'], 'The collector must mark this item collected first.')
            if not edge[command]:
                edge[command] = True
                record(state, member, ('Marked an item collected.' if command == 'collected' else 'Confirmed receiving their item.'), now)
            if all(e['received'] for e in loop['edges']):
                loop['status'] = 'completed'
                for edge in loop['edges']:
                    next(t for t in state['trips'] if t['id'] == edge['trip'])['status'] = 'completed'
                    next(r for r in state['requests'] if r['id'] == edge['request'])['status'] = 'completed'
                record(state, 'system', 'Circle closed. Every receiver confirmed their handover.', now)
        else:
            raise ValueError('Unknown action.')
    state['operations'].append({'id': op, 'member': member, 'command': command})
    state['operations'] = state['operations'][-300:]
    state['version'] += 1
    return True
