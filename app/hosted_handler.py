"""Password-protected, single-group demo for API Gateway HTTP API v2.

The access code admits demonstrators, not real residents. Cedar still enforces
the selected fictional actor's permissions. Never use this as resident identity.
"""
import base64
import hashlib
import hmac
from http.cookies import SimpleCookie, CookieError
import json
import os
from pathlib import Path
import re
import secrets
import time

from .http_api import handle, SECURITY_HEADERS
from .seed import seed
from .store import DynamoStore

STATIC = Path(__file__).with_name('static')
ASSETS = {
    '/app.js': ('app.js', 'text/javascript'),
    '/style.css': ('style.css', 'text/css'),
    '/favicon.svg': ('favicon.svg', 'image/svg+xml'),
    '/manifest.json': ('manifest.json', 'application/manifest+json'),
    '/login.js': ('login.js', 'text/javascript'),
}
COOKIE = '__Host-errandloop'
LIFETIME = 12 * 3600


def response(status, body, content_type='application/json', cookie=None):
    result = {'statusCode': status, 'headers': {
        **SECURITY_HEADERS, 'Content-Type': content_type + '; charset=utf-8',
        'Strict-Transport-Security': 'max-age=31536000'},
        'body': json.dumps(body) if isinstance(body, (dict, list)) else body}
    if cookie:
        result['cookies'] = [cookie]
    return result


def signature(payload, key):
    return hmac.new(bytes.fromhex(key), payload.encode(), hashlib.sha256).hexdigest()


def authenticated(event, key, now):
    try:
        cookies = SimpleCookie()
        cookies.load('; '.join(event.get('cookies') or []))
        value = cookies[COOKIE].value
        expires, nonce, signed = value.split('.')
        payload = expires + '.' + nonce
        return (now < int(expires) <= now + LIFETIME
                and bool(re.fullmatch(r'[0-9a-f]{32}', nonce))
                and hmac.compare_digest(signature(payload, key), signed))
    except (CookieError, KeyError, TypeError, ValueError):
        return False


def handler(event, context):
    now = int(time.time())
    key = os.environ.get('ERRANDLOOP_ACCESS_HASH', '')
    if not re.fullmatch(r'[0-9a-f]{64}', key):
        return response(503, {'error': 'Demo access is not configured.'})
    path = event.get('rawPath', '/')
    request_context = event.get('requestContext', {})
    method = request_context.get('http', {}).get('method', 'GET')
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    admitted = authenticated(event, key, now)
    if method == 'GET':
        if path in ('/', '/index.html'):
            html = (STATIC / ('index.html' if admitted else 'login.html')).read_text()
            html = html.replace('Local demo', 'Hosted demo <button data-action="sign-out">Sign out</button>')
            return response(200, html, 'text/html')
        if path in ASSETS:
            filename, content_type = ASSETS[path]
            return response(200, (STATIC / filename).read_text(), content_type)
        if path == '/api/health':
            return response(200, {'ok': True, 'policyEngine': 'Cedar', 'mode': 'protected-hosted-demo'})
    if method not in ('GET', 'POST'):
        return response(405, {'error': 'Method not supported.'})
    body = None
    if method == 'POST':
        # Use Gateway's trusted domain, never a caller-supplied Host header.
        expected_origin = 'https://' + request_context.get('domainName', '')
        if headers.get('origin') != expected_origin:
            return response(403, {'error': 'Use this demo from its own website.'})
        if headers.get('content-type', '').split(';')[0].strip() != 'application/json':
            return response(415, {'error': 'Send application/json.'})
        try:
            raw = event.get('body') or ''
            if len(raw) > 24000:
                raise ValueError()
            if event.get('isBase64Encoded'):
                raw = base64.b64decode(raw, validate=True).decode()
            if len(raw.encode()) > 16000:
                raise ValueError()
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise ValueError()
        except (ValueError, UnicodeError, TypeError):
            return response(400, {'error': 'Invalid request body.'})
    if path == '/api/session' and method == 'POST':
        supplied = body.get('code')
        if not isinstance(supplied, str) or not hmac.compare_digest(hashlib.sha256(supplied.encode()).hexdigest(), key):
            return response(401, {'error': 'That access code did not match.'})
        payload = f'{now + LIFETIME}.{secrets.token_hex(16)}'
        cookie = f'{COOKIE}={payload}.{signature(payload, key)}; Path=/; Max-Age={LIFETIME}; HttpOnly; Secure; SameSite=Strict'
        return response(200, {'ok': True}, cookie=cookie)
    if path == '/api/logout' and method == 'POST':
        return response(200, {'ok': True}, cookie=f'{COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict')
    if not admitted:
        return response(401, {'error': 'Enter the demo access code to continue.'})
    try:
        store = DynamoStore(os.environ['ERRANDLOOP_TABLE'])
        actor = headers.get('x-demo-member', 'you')
        if path == '/api/reset' and method == 'POST':
            def reset(state):
                fresh = seed(now)
                fresh['version'] = state['version'] + 1
                state.clear()
                state.update(fresh)
            store.transact(reset, now)
            status, result = handle(store, 'GET', '/api/board', actor)
        else:
            status, result = handle(store, method, path, actor, body)
        return response(status, result)
    except Exception:
        # Do not expose AWS errors, request bodies, or access codes to visitors.
        return response(503, {'error': 'The board is temporarily unavailable. Please retry.'})
