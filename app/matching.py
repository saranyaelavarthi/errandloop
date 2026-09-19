"""Deterministic, exact disjoint-cycle packing for small trusted groups.

An edge A -> B means A's existing trip can fulfil B's request. Enumerate
cycles of length 2–4, then choose disjoint cycles that serve the most people.
Ties prefer less total waiting, then a stable lexical ordering.
"""
from functools import lru_cache
import hashlib

MAX_MEMBERS = 16


def compatible(trip, request, now):
    return (trip['member'] != request['member']
            and trip['status'] == 'open' and request['status'] == 'open'
            and trip['destination'] == request['destination']
            and trip['capacity'] >= request['units']
            and now < trip['depart']
            and request['ready'] <= trip['depart']
            and trip['returns'] <= request['deadline'])


def find_matches(state, now):
    trips = {t['member']: t for t in state['trips'] if t['status'] == 'open' and t['depart'] > now}
    requests = {r['member']: r for r in state['requests'] if r['status'] == 'open' and r['deadline'] > now}
    members = sorted(set(trips) & set(requests))
    if len(members) > MAX_MEMBERS:
        raise ValueError('The prototype supports at most 16 simultaneous participants.')
    graph = {a: [b for b in members if compatible(trips[a], requests[b], now)] for a in members}
    candidates = []

    def visit(path):
        tail, start = path[-1], path[0]
        if len(path) >= 2 and start in graph[tail]:
            edges = []
            for a, b in zip(path, path[1:] + path[:1]):
                t, r = trips[a], requests[b]
                edges.append({'giver': a, 'receiver': b, 'trip': t['id'], 'request': r['id'],
                              'destination': t['destination'], 'item': r['item'], 'units': r['units'],
                              'depart': t['depart'], 'returns': t['returns'], 'deadline': r['deadline']})
            key = '|'.join(e['trip'] + ':' + e['request'] for e in edges)
            candidates.append({'id': hashlib.sha256(key.encode()).hexdigest()[:14],
                               'members': path[:], 'edges': edges,
                               'waiting': sum(e['returns'] - now for e in edges),
                               'expires': min(e['depart'] for e in edges)})
        if len(path) < 4:
            for nxt in graph[tail]:
                # The smallest member is the canonical start: no rotated duplicates.
                if nxt > start and nxt not in path:
                    visit(path + [nxt])

    for member in members:
        visit([member])
    candidates.sort(key=lambda c: c['id'])
    positions = {m: 1 << i for i, m in enumerate(members)}
    masks = [sum(positions[m] for m in c['members']) for c in candidates]
    by_member = {m: [i for i, c in enumerate(candidates) if m in c['members']] for m in members}

    @lru_cache(None)
    def pack(available):
        if not available:
            return (0, 0, ())
        first = next(m for m in members if positions[m] & available)
        best = pack(available & ~positions[first])
        for i in by_member[first]:
            mask = masks[i]
            if available & mask == mask:
                count, wait, chosen = pack(available ^ mask)
                option = (count + len(candidates[i]['members']),
                          wait - candidates[i]['waiting'], tuple(sorted(chosen + (i,))))
                if option[:2] > best[:2] or (option[:2] == best[:2] and option[2] < best[2]):
                    best = option
        return best

    served, _, chosen = pack((1 << len(members)) - 1)
    selected = {candidates[i]['id'] for i in chosen}
    for c in candidates:
        c['recommended'] = c['id'] in selected
    candidates.sort(key=lambda c: (not c['recommended'], -len(c['members']), c['id']))
    unmatched = []
    covered = {m for c in candidates if c['recommended'] for m in c['members']}
    for m, r in requests.items():
        if m in covered:
            continue
        alternatives = any(m in c['members'] for c in candidates)
        same_stop = [t for t in trips.values() if t['member'] != m
                     and t['destination'] == r['destination']]
        possible = any(compatible(t, r, now) for t in same_stop)
        reason = ('A valid circle is available as an alternative. Review it in My circles.' if alternatives else
                  'Add a planned trip to offer something in return.' if m not in trips else
                  'A compatible pickup exists, but a complete exchange circle is still missing.' if possible else
                  'Nobody else has posted an upcoming trip to your pickup location.' if not same_stop else
                  'Trips reach your pickup location, but their timing or carrying space does not fit yet.')
        checks = []
        for t in sorted(same_stop, key=lambda t: (t['returns'], t['id'])):
            blockers = []
            if r['ready'] > t['depart']:
                minutes = (r['ready'] - t['depart'] + 59) // 60
                blockers.append(f'Leaves {minutes} min before your item is ready.')
            if t['returns'] > r['deadline']:
                minutes = (t['returns'] - r['deadline'] + 59) // 60
                blockers.append(f'Returns {minutes} min after your deadline.')
            if t['capacity'] < r['units']:
                blockers.append(f"Available space: {t['capacity']}; your request needs {r['units']}.")
            checks.append({'member': t['member'], 'trip': t['id'], 'blockers': blockers,
                           'pickupFits': not blockers})
        unmatched.append({'member': m, 'request': r['id'], 'reason': reason,
                          'checks': checks})
    return {'candidates': candidates, 'unmatched': unmatched,
            'potentialTripsAvoided': served,
            'candidateCount': len(candidates), 'recommendedCount': len(chosen)}
