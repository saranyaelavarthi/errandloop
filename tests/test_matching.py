from copy import deepcopy
import itertools
import random
from app.seed import seed
from app.matching import compatible, find_matches

NOW = 1_000_000


def test_seed_packs_five_requests_and_never_reuses_a_member():
    result = find_matches(seed(NOW), NOW)
    selected = [c for c in result['candidates'] if c['recommended']]
    members = [m for c in selected for m in c['members']]
    assert result['potentialTripsAvoided'] == 5
    assert len(members) == len(set(members))
    assert any(set(c['members']) == {'you', 'asha', 'ravi'} for c in selected)


def test_every_edge_satisfies_actual_constraints():
    state = seed(NOW)
    for cycle in find_matches(state, NOW)['candidates']:
        assert 2 <= len(cycle['members']) <= 4
        for edge in cycle['edges']:
            t = next(t for t in state['trips'] if t['id'] == edge['trip'])
            r = next(r for r in state['requests'] if r['id'] == edge['request'])
            assert compatible(t, r, NOW)
        assert {e['giver'] for e in cycle['edges']} == {e['receiver'] for e in cycle['edges']}


def test_capacity_ready_time_and_deadline_are_hard_constraints():
    state = seed(NOW)
    t, r = state['trips'][0], state['requests'][2]
    assert compatible(t, r, NOW)
    for key, value in [('units', 3), ('ready', t['depart']+1), ('deadline', t['returns']-1)]:
        changed = dict(r, **{key: value})
        assert not compatible(t, changed, NOW)
    assert not compatible(dict(t, depart=NOW), r, NOW)
    assert not compatible(t, dict(r, member=t['member']), NOW)


def test_matching_is_stable_under_input_reordering():
    state = seed(NOW)
    expected = find_matches(state, NOW)['candidates']
    state['trips'].reverse(); state['requests'].reverse()
    assert find_matches(state, NOW)['candidates'] == expected


def test_missing_return_favour_does_not_create_a_one_way_circle():
    state = seed(NOW)
    state['requests'] = [state['requests'][2]]
    assert not find_matches(state, NOW)['candidates']


def test_global_packing_matches_independent_brute_force_on_small_random_boards():
    rng = random.Random(14)
    for _ in range(30):
        state = seed(NOW)
        for t in state['trips']:
            t['destination'] = rng.choice(['grocery', 'print', 'library', 'canteen'])
        for r in state['requests']:
            r['destination'] = rng.choice(['grocery', 'print', 'library', 'canteen'])
        result = find_matches(state, NOW)
        candidates = result['candidates']
        # Six participants means at most three disjoint circles; enumerate those sets.
        best = 0
        for count in range(min(3, len(candidates))+1):
            for subset in itertools.combinations(candidates, count):
                ids = [m for c in subset for m in c['members']]
                if len(ids) == len(set(ids)):
                    best = max(best, len(ids))
        assert result['potentialTripsAvoided'] == best
        selected = {m for c in candidates if c['recommended'] for m in c['members']}
        assert len(selected) == best
        assert not selected.intersection(u['member'] for u in result['unmatched'])


def test_four_person_circle_is_supported():
    state = seed(NOW)
    state['trips'] = state['trips'][:4]
    state['requests'] = state['requests'][:4]
    destinations = ['grocery', 'print', 'library', 'canteen']
    for i in range(4):
        state['trips'][i]['destination'] = destinations[i]
        state['requests'][i]['destination'] = destinations[(i-1)%4]
    result = find_matches(state, NOW)
    assert result['potentialTripsAvoided'] == 4
    assert len(result['candidates']) == 1
