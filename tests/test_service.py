from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import uuid
import pytest
from app.seed import seed
from app.matching import find_matches
from app.service import mutate, expire, Conflict
from app.store import SQLiteStore
from app.auth import authorize, ref
from app.http_api import handle
from app.lambda_handler import handler

NOW = 1_000_000


def command(s, member, action, **fields):
    return mutate(s, member, action, {'operation': uuid.uuid4().hex, 'version': s['version'], **fields}, NOW)


def proposed():
    s = seed(NOW)
    c = next(c for c in find_matches(s, NOW)['candidates'] if c['recommended'] and 'you' in c['members'])
    command(s, 'you', 'propose', id=c['id'])
    return s, s['loops'][0]


def active():
    s, l = proposed()
    for member in l['members']:
        if member not in l['accepted']:
            command(s, member, 'accept', id=l['id'])
    return s, l


def test_everyone_must_consent_before_collecting():
    s, l = proposed()
    assert l['status'] == 'awaiting'
    e = l['edges'][0]
    with pytest.raises(ValueError, match='All members'):
        command(s, e['giver'], 'collected', id=l['id'], request=e['request'])


def test_complete_circle_requires_each_receiver_confirmation():
    s, l = active()
    for e in l['edges']:
        command(s, e['giver'], 'collected', id=l['id'], request=e['request'])
    assert l['status'] == 'active'
    for e in l['edges']:
        command(s, e['receiver'], 'received', id=l['id'], request=e['request'])
    assert l['status'] == 'completed'
    assert all(next(r for r in s['requests'] if r['id'] == e['request'])['status'] == 'completed' for e in l['edges'])


def test_cedar_blocks_outsider_acceptance_and_wrong_receiver():
    s, l = active()
    with pytest.raises(PermissionError):
        command(s, 'kabir', 'cancel_loop', id=l['id'])
    e = l['edges'][0]
    command(s, e['giver'], 'collected', id=l['id'], request=e['request'])
    with pytest.raises(PermissionError):
        command(s, e['giver'], 'received', id=l['id'], request=e['request'])


def test_cedar_default_denies_unspecified_actions():
    with pytest.raises(PermissionError):
        authorize('you', 'approve_for_everyone', 'Group', 'courtyard', {'id': 'courtyard'})


def test_cedar_blocks_deleting_someone_elses_post():
    s = seed(NOW)
    with pytest.raises(PermissionError):
        command(s, 'you', 'cancel_post', id='trip-asha')


def test_request_cannot_be_marked_received_before_collection():
    s, l = active(); e = l['edges'][0]
    with pytest.raises(ValueError, match='collected first'):
        command(s, e['receiver'], 'received', id=l['id'], request=e['request'])


def test_pre_collection_cancellation_releases_others_but_removes_cancelled_trip():
    s, l = active()
    command(s, 'you', 'cancel_loop', id=l['id'])
    assert l['status'] == 'cancelled'
    assert next(t for t in s['trips'] if t['member']=='you')['status'] == 'cancelled'
    assert next(t for t in s['trips'] if t['member']=='asha')['status'] == 'open'
    assert next(r for r in s['requests'] if r['member']=='you')['status'] == 'open'


def test_post_collection_cancellation_does_not_rematch_goods_in_transit():
    s, l = active(); e = l['edges'][0]
    command(s, e['giver'], 'collected', id=l['id'], request=e['request'])
    command(s, 'you', 'cancel_loop', id=l['id'])
    assert l['status'] == 'needs_handoff'
    candidates = find_matches(s, NOW)['candidates']
    assert not any(set(c['members']) & set(l['members']) for c in candidates)
    command(s, e['receiver'], 'received', id=l['id'], request=e['request'])
    assert e['received']


def test_declining_cannot_silently_reenter_same_circle():
    s, l = proposed()
    command(s, 'asha', 'decline', id=l['id'])
    assert not any('asha' in c['members'] for c in find_matches(s, NOW)['candidates'])


def test_expiry_releases_posts_and_blocks_late_acceptance():
    s, l = proposed()
    assert expire(s, l['expires'])
    assert l['status'] == 'expired'
    with pytest.raises(ValueError):
        command(s, 'asha', 'accept', id=l['id'])


def test_stale_version_is_rejected_and_repeat_operation_is_idempotent():
    s = seed(NOW)
    payload = {'operation': 'same-operation', 'version': 1, 'id': 'trip-you'}
    assert mutate(s, 'you', 'cancel_post', payload, NOW)
    assert not mutate(s, 'you', 'cancel_post', payload, NOW)
    assert s['version'] == 2
    with pytest.raises(Conflict):
        mutate(s, 'asha', 'cancel_post', {'operation':'different','version':1,'id':'trip-asha'}, NOW)


@pytest.mark.parametrize('change', [{'capacity':True}, {'capacity':0}, {'returns':NOW+1}, {'destination':'anywhere'}, {'depart':NOW-1}])
def test_invalid_trip_is_rejected(change):
    s = seed(NOW)
    payload={'destination':'grocery','depart':NOW+1000,'returns':NOW+2000,'capacity':1,'note':'Small item'}
    with pytest.raises(ValueError):
        command(s, 'kabir', 'trip', **(payload|change))


def test_duplicate_open_post_is_rejected():
    s = seed(NOW)
    with pytest.raises(ValueError, match='existing post'):
        command(s, 'you', 'trip', destination='grocery',depart=NOW+1000,returns=NOW+2000,capacity=1)


def test_new_member_posts_can_form_a_real_match():
    s = seed(NOW)
    command(s,'kabir','trip',destination='library',depart=NOW+1800,returns=NOW+3600,capacity=1)
    command(s,'kabir','request',destination='grocery',item='Prepared order',ready=NOW,deadline=NOW+7200,units=1)
    assert any('kabir' in c['members'] for c in find_matches(s,NOW)['candidates'])


def test_sqlite_transaction_rolls_back_failed_mutation(tmp_path):
    store = SQLiteStore(tmp_path/'board.sqlite3')
    before = store.transact(lambda s: json.dumps(s), NOW)
    def fail(s):
        s['members'].clear()
        raise ValueError('fail')
    with pytest.raises(ValueError):
        store.transact(fail, NOW)
    assert store.transact(lambda s: json.dumps(s),NOW)==before


def test_concurrent_reservations_only_one_succeeds(tmp_path):
    store = SQLiteStore(tmp_path/'board.sqlite3')
    store.transact(lambda s:s.update(seed(NOW)),NOW)
    c=next(c for c in find_matches(seed(NOW),NOW)['candidates'] if 'you' in c['members'])
    def propose(actor):
        try:
            store.transact(lambda s:mutate(s,actor,'propose',{'id':c['id'],'operation':uuid.uuid4().hex,'version':1},NOW),NOW)
            return True
        except Conflict:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(propose,c['members'][:2]))
    assert sum(results)==1
    assert store.transact(lambda s:len(s['loops']),NOW)==1


def test_lambda_rejects_unsigned_invocation():
    result=handler({'requestContext':{},'headers':{}},None)
    assert result['statusCode']==403
