import json
import time
import uuid
import pytest
from app.groups import LocalGroups
from app.live import dispatch

ORIGIN = 'https://test.example'
PASSWORD = 'a long test password only'


@pytest.fixture
def app(tmp_path):
    store = LocalGroups(tmp_path / 'groups.sqlite3')
    def request(path, data=None, cookie='', **headers):
        method = 'POST' if data is not None else 'GET'
        return dispatch(store, store.key, method, path,
            {'cookie': cookie, 'origin': ORIGIN, 'content-type': 'application/json', **headers},
            json.dumps(data) if data is not None else '', ORIGIN)
    request.store = store
    return request


def unpack(result):
    assert result['statusCode'] == 200, result
    return json.loads(result['body'])


def register(app, username='alice'):
    response = app('/api/groups/create', {'username': username, 'password': PASSWORD,
        'name': username.title(), 'group_name': 'Maple House', 'meeting': 'Lobby reception',
        'places': ['Actual grocery shop', 'Neighbourhood print shop']})
    unpack(response)
    cookie = response['cookies'][0].split(';')[0]
    board = unpack(app('/api/board', cookie=cookie))
    return cookie, board


def join(app, group, username='bob'):
    response = app('/api/groups/join', {'group_code': group, 'username': username,
        'password': PASSWORD, 'name': username.title()})
    unpack(response)
    return response['cookies'][0].split(';')[0]


def test_new_group_is_empty_and_accounts_are_private(app):
    cookie, board = register(app)
    assert board['trips'] == board['requests'] == board['loops'] == []
    assert len(board['members']) == 1
    assert board['members'][0]['name'] == 'Alice'
    assert [p['name'] for p in board['places']] == ['Actual grocery shop', 'Neighbourhood print shop']
    assert 'accounts' not in board
    assert PASSWORD not in json.dumps(board)
    stored = app.store.transact(board['group']['id'], lambda s: json.dumps(s))
    assert PASSWORD not in stored
    assert 'hash' in stored
    assert 'Demo seat' not in app('/', cookie=cookie)['body']
    assert 'data-mode="live"' in app('/', cookie=cookie)['body']


def test_real_two_account_exchange_and_actor_spoofing(app):
    alice, initial = register(app)
    bob = join(app, initial['group']['id'])
    now = int(time.time())
    a, b = [p['id'] for p in initial['places']]
    def board(cookie): return unpack(app('/api/board', cookie=cookie))
    def act(cookie, action, **fields):
        return app('/api/actions/' + action, {'operation': uuid.uuid4().hex,
            'version': board(cookie)['version'], **fields}, cookie=cookie, **{'x-demo-member': 'you'})
    for cookie, going, need in [(alice,a,b),(bob,b,a)]:
        unpack(act(cookie, 'trip', destination=going, depart=now+1200, returns=now+2400, capacity=1))
        unpack(act(cookie, 'request', destination=need, item='My prepared order', ready=now, deadline=now+3600, units=1))
    assert board(alice)['actor'] != board(bob)['actor']
    assert board(alice)['trips'][0]['member'] == board(alice)['actor']
    candidate = board(alice)['matching']['candidates'][0]
    unpack(act(alice, 'propose', id=candidate['id']))
    loop = board(alice)['loops'][0]
    assert len(loop['accepted']) == 1
    assert act(alice, 'collected', id=loop['id'], request=loop['edges'][0]['request'])['statusCode'] in (400,403)
    unpack(act(bob, 'accept', id=loop['id']))
    for edge in loop['edges']:
        giver = alice if edge['giver'] == board(alice)['actor'] else bob
        receiver = bob if giver == alice else alice
        unpack(act(giver, 'collected', id=loop['id'], request=edge['request']))
        assert act(giver, 'received', id=loop['id'], request=edge['request'])['statusCode'] == 403
        unpack(act(receiver, 'received', id=loop['id'], request=edge['request']))
    assert board(alice)['loops'][0]['status'] == 'completed'


def test_separate_groups_cannot_read_or_mutate_each_other(app):
    alice, first = register(app)
    other, second = register(app, 'charlie')
    assert first['group']['id'] != second['group']['id']
    attempted = unpack(app('/api/board', cookie=other, **{'x-demo-member': first['actor'], 'x-group-id': first['group']['id']}))
    assert attempted['group']['id'] == second['group']['id']
    assert attempted['members'][0]['name'] == 'Charlie'
    forged = alice.replace(first['group']['id'], second['group']['id'])
    assert app('/api/board', cookie=forged)['statusCode'] == 401


def test_login_and_persistence_without_sample_data(app):
    cookie, board = register(app)
    response = app('/api/session', {'group_code': board['group']['id'], 'username': 'ALICE', 'password': PASSWORD})
    unpack(response)
    new = LocalGroups(app.store.path)
    assert new.key == app.store.key
    assert new.transact(board['group']['id'], lambda s: len(s['members'])) == 1
    assert app('/api/reset', {}, cookie=cookie)['statusCode'] == 404
    assert 'Max-Age=0' in app('/api/logout', {}, cookie=cookie)['cookies'][0]


def test_only_owner_can_add_real_pickup_locations(app):
    cookie, board = register(app)
    bob = join(app, board['group']['id'])
    assert app('/api/places', {'name': 'Town library'}, cookie=bob)['statusCode'] == 403
    result = unpack(app('/api/places', {'name': 'Town library'}, cookie=cookie))
    assert result['places'][-1]['name'] == 'Town library'
    assert app('/api/places', {'name': 'town library'}, cookie=cookie)['statusCode'] == 400


def test_repeated_failed_login_locks_account_and_persists(app):
    _, board = register(app)
    data = {'group_code': board['group']['id'], 'username': 'alice', 'password': 'incorrect long password'}
    for _ in range(5): assert app('/api/session', data)['statusCode'] == 401
    assert app('/api/session', {**data, 'password': PASSWORD})['statusCode'] == 401
    assert app.store.transact(board['group']['id'], lambda s: s['accounts']['alice']['locked_until']) > time.time()


def test_group_join_validates_invites_and_unique_accounts(app):
    _, board = register(app)
    data = {'group_code': board['group']['id'], 'username': 'alice', 'password': PASSWORD, 'name': 'Another person'}
    assert app('/api/groups/join', data)['statusCode'] == 400
    assert app('/api/groups/join', {**data, 'username': 'bob', 'group_code': '0'*32})['statusCode'] == 400
    assert app('/api/groups/create', {**data, 'group_name': 'Test', 'meeting': 'Lobby', 'places': ['Shop','shop']})['statusCode'] == 400


def test_csrf_missing_session_and_weak_password(app):
    assert app('/api/groups/create', {}, origin='https://evil.example')['statusCode'] == 403
    assert app('/api/board', **{'x-demo-member': 'you'})['statusCode'] == 401
    assert app('/api/groups/create', {'username': 'alice', 'password': 'short'})['statusCode'] == 400


def test_cloud_group_key_and_revision_guard(monkeypatch):
    from app.groups import CloudGroups
    from botocore.stub import Stubber
    from app.service import Conflict
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test-only')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test-only')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'ap-south-1')
    store = CloudGroups('LiveGroupsTest')
    group = 'a' * 32
    state = {'version': 1}
    with Stubber(store.table.meta.client) as stub:
        stub.add_response('get_item', {'Item': {'id': {'S': 'group:' + group},
            'payload': {'S': json.dumps(state)}, 'revision': {'N': '3'}}},
            {'TableName': 'LiveGroupsTest', 'Key': {'id': 'group:' + group}, 'ConsistentRead': True})
        stub.add_client_error('put_item', 'ConditionalCheckFailedException', 'Race', expected_params={
            'TableName': 'LiveGroupsTest', 'Item': {'id': 'group:' + group, 'payload': json.dumps({'version': 2}), 'revision': 4},
            'ConditionExpression': 'revision = :old', 'ExpressionAttributeValues': {':old': 3}})
        with pytest.raises(Conflict):
            store.transact(group, lambda s: s.update(version=2))
        stub.assert_no_pending_responses()


def test_lambda_live_entry_uses_signed_cookie_identity(app, monkeypatch):
    from app import live_handler
    monkeypatch.setenv('ERRANDLOOP_TABLE', 'test')
    monkeypatch.setenv('ERRANDLOOP_ACCESS_HASH', app.store.key)
    monkeypatch.setattr(live_handler, 'CloudGroups', lambda _: app.store)
    cookie, board = register(app)
    event = {'rawPath': '/api/board', 'cookies': [cookie],
             'headers': {'x-demo-member': 'you'},
             'requestContext': {'domainName': 'test.example', 'http': {'method': 'GET'}}}
    result = unpack(live_handler.handler(event, None))
    assert result['actor'] == board['actor']
    assert 'accounts' not in result
    event['cookies'] = []
    assert live_handler.handler(event, None)['statusCode'] == 401
