import hashlib
import json
import time
import uuid

import pytest

from app import hosted_handler as web
from app.store import SQLiteStore

CODE = 'only-a-test-code-not-a-deployed-secret'
DOMAIN = 'example.execute-api.ap-south-1.amazonaws.com'


@pytest.fixture
def hosted(monkeypatch, tmp_path):
    monkeypatch.setenv('ERRANDLOOP_ACCESS_HASH', hashlib.sha256(CODE.encode()).hexdigest())
    monkeypatch.setenv('ERRANDLOOP_TABLE', 'test')
    database = SQLiteStore(tmp_path / 'test.sqlite3')
    monkeypatch.setattr(web, 'DynamoStore', lambda _: database)
    return database


def call(path, body=None, cookies=None, actor='you', origin=DOMAIN, method=None):
    return web.handler({
        'rawPath': path, 'requestContext': {'domainName': DOMAIN, 'http': {
            'method': method or ('POST' if body is not None else 'GET')}},
        'headers': {'origin': 'https://' + origin, 'content-type': 'application/json', 'x-demo-member': actor},
        'cookies': cookies or [], 'body': json.dumps(body) if body is not None else ''}, None)


def login():
    result = call('/api/session', {'code': CODE})
    assert result['statusCode'] == 200
    return [result['cookies'][0].split(';')[0]]


def test_board_and_mutations_require_demo_access(hosted):
    assert 'login-form' in call('/')['body']
    assert call('/api/board')['statusCode'] == 401
    assert call('/api/reset', {})['statusCode'] == 401
    assert call('/api/actions/propose', {})['statusCode'] == 401
    assert call('/app.js')['headers']['Content-Type'].startswith('text/javascript')
    assert call('/../../requirements.txt')['statusCode'] == 401


def test_wrong_code_and_malformed_code_are_rejected(hosted):
    for code in ('wrong', None, {'code': CODE}):
        result = call('/api/session', {'code': code})
        assert result['statusCode'] == 401
        assert 'cookies' not in result


def test_login_cookie_is_secure_and_opens_full_interface(hosted):
    result = call('/api/session', {'code': CODE})
    cookie = result['cookies'][0]
    for flag in ('__Host-', 'Secure', 'HttpOnly', 'SameSite=Strict', 'Path=/'):
        assert flag in cookie
    page = call('/', cookies=[cookie.split(';')[0]])
    assert 'Going anyway?' in page['body']
    assert 'Hosted demo' in page['body']
    assert 'sign-out' in page['body']
    assert CODE not in page['body']


def test_cookie_tampering_expiry_and_key_rotation_are_rejected(hosted, monkeypatch):
    cookies = login()
    assert call('/api/board', cookies=cookies)['statusCode'] == 200
    assert call('/api/board', cookies=[cookies[0] + 'f'])['statusCode'] == 401
    current = int(time.time())
    monkeypatch.setattr(web.time, 'time', lambda: current + web.LIFETIME + 1)
    assert call('/api/board', cookies=cookies)['statusCode'] == 401
    monkeypatch.setattr(web.time, 'time', lambda: current)
    monkeypatch.setenv('ERRANDLOOP_ACCESS_HASH', 'a' * 64)
    assert call('/api/board', cookies=cookies)['statusCode'] == 401


def test_cross_origin_login_and_authenticated_mutations_are_rejected(hosted):
    assert call('/api/session', {'code': CODE}, origin='evil.example')['statusCode'] == 403
    assert call('/api/reset', {}, cookies=login(), origin='evil.example')['statusCode'] == 403


def test_hosted_three_party_exchange_and_shared_reset(hosted):
    cookies = login()
    def board():
        return json.loads(call('/api/board', cookies=cookies)['body'])
    def act(actor, action, **fields):
        result = call('/api/actions/' + action, {'version': board()['version'],
                      'operation': uuid.uuid4().hex, **fields}, cookies, actor)
        assert result['statusCode'] == 200, result
    candidate = next(c for c in board()['matching']['candidates'] if 'you' in c['members'] and c['recommended'])
    act('you', 'propose', id=candidate['id'])
    loop = board()['loops'][0]
    for member in loop['members']:
        if member not in loop['accepted']:
            act(member, 'accept', id=loop['id'])
    assert call('/api/actions/cancel_loop', {'id': loop['id'], 'version': board()['version'],
                'operation': uuid.uuid4().hex}, cookies, 'kabir')['statusCode'] == 403
    for edge in loop['edges']:
        act(edge['giver'], 'collected', id=loop['id'], request=edge['request'])
        act(edge['receiver'], 'received', id=loop['id'], request=edge['request'])
    assert board()['loops'][0]['status'] == 'completed'
    previous_version = board()['version']
    reset = call('/api/reset', {}, cookies)
    assert reset['statusCode'] == 200
    assert board()['loops'] == []
    assert board()['version'] > previous_version


def test_fail_closed_without_access_configuration(hosted, monkeypatch):
    monkeypatch.delenv('ERRANDLOOP_ACCESS_HASH')
    assert call('/')['statusCode'] == 503


def test_logout_clears_browser_cookie(hosted):
    result = call('/api/logout', {}, login())
    assert result['statusCode'] == 200
    assert 'Max-Age=0' in result['cookies'][0]


def test_invalid_json_and_oversized_bodies_are_rejected(hosted):
    for body in ('{broken', '"' + 'a' * 16001 + '"'):
        result = web.handler({'rawPath': '/api/session', 'body': body,
            'headers': {'origin': 'https://' + DOMAIN, 'content-type': 'application/json'},
            'requestContext': {'domainName': DOMAIN, 'http': {'method': 'POST'}}}, None)
        assert result['statusCode'] == 400
