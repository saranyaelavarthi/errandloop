"""Real-group routes shared by local HTTP and AWS Lambda. No demo impersonation."""
import hashlib
import hmac
from http.cookies import SimpleCookie, CookieError
import json
from pathlib import Path
import re
import secrets
import time
from .hosted_handler import response, ASSETS
from .service import view, mutate, expire, Conflict

STATIC = Path(__file__).with_name('static')
ASSETS = {**ASSETS, '/onboarding.js': ('onboarding.js', 'text/javascript')}
LIFETIME = 12 * 3600


def clean(value, label, minimum=1, maximum=80):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f'{label} must contain {minimum}–{maximum} characters.')
    return value.strip()


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32).hex()


def credentials(data):
    username = clean(data.get('username'), 'Username', 3, 30).lower()
    if not re.fullmatch(r'[a-z0-9_.-]+', username):
        raise ValueError('Use letters, numbers, dots, underscores, or hyphens in your username.')
    password = data.get('password')
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ValueError('Use a password with 12–128 characters.')
    return username, password


def member_account(data, username, password):
    name = clean(data.get('name'), 'Your name', 2, 60)
    uid, salt = secrets.token_hex(16), secrets.token_hex(16)
    member = {'id': uid, 'name': name, 'initials': ''.join(p[0] for p in name.split())[:2].upper(), 'color': 'green', 'room': 'Group member'}
    return member, {'member': uid, 'salt': salt, 'hash': password_hash(password, salt), 'failures': 0, 'locked_until': 0}


def group_code(data):
    code = str(data.get('group_code', '')).strip().lower()
    if not re.fullmatch(r'[0-9a-f]{32}', code):
        raise ValueError('Enter the 32-character group code from your group owner.')
    return code


def session_cookie(group, member, key, secure, clear=False):
    name = '__Host-errandloop-live' if secure else 'errandloop-local'
    if clear:
        value, age = '', 0
    else:
        payload = f'{group}.{member}.{int(time.time()) + LIFETIME}.{secrets.token_hex(16)}'
        value = payload + '.' + hmac.new(bytes.fromhex(key), payload.encode(), hashlib.sha256).hexdigest()
        age = LIFETIME
    return f'{name}={value}; Path=/; Max-Age={age}; HttpOnly; SameSite=Strict' + ('; Secure' if secure else '')


def identity(headers, key, secure):
    try:
        cookies = SimpleCookie()
        cookies.load(headers.get('cookie', ''))
        value = cookies['__Host-errandloop-live' if secure else 'errandloop-local'].value
        group, member, expires, nonce, signature = value.split('.')
        payload = '.'.join((group, member, expires, nonce))
        expected = hmac.new(bytes.fromhex(key), payload.encode(), hashlib.sha256).hexdigest()
        if (not all(re.fullmatch(r'[0-9a-f]{32}', x) for x in (group, member, nonce))
                or not int(time.time()) < int(expires) <= int(time.time()) + LIFETIME
                or not hmac.compare_digest(signature, expected)):
            return None
        return group, member
    except (KeyError, ValueError, CookieError, TypeError):
        return None


def app_html():
    html = (STATIC / 'index.html').read_text().replace('<body>', '<body data-mode="live">')
    html = html.replace('A little campus experiment. <strong>Fictional people, working exchanges.</strong>', 'Your neighbourhood. <strong>Real plans, shared favours.</strong>')
    html = html.replace('Demo seat', 'Signed in as').replace('Choose a fictional participant', 'Your account')
    html = html.replace('The Courtyard · Local demo <button data-action="reset-prompt">Start fresh</button>', '<button data-action="group">Your group</button> <button data-action="sign-out">Sign out</button>')
    return html


def dispatch(store, key, method, path, headers, raw='', origin='', secure=True):
    if not re.fullmatch(r'[0-9a-f]{64}', key):
        return response(503, {'error': 'Server sessions are not configured.'})
    headers = {k.lower(): v for k, v in headers.items()}
    who = identity(headers, key, secure)
    if method == 'GET':
        if path in ('/', '/index.html'):
            return response(200, app_html() if who else (STATIC / 'onboarding.html').read_text(), 'text/html')
        if path in ASSETS:
            filename, mime = ASSETS[path]
            return response(200, (STATIC / filename).read_text(), mime)
        if path == '/api/health':
            return response(200, {'ok': True, 'policyEngine': 'Cedar', 'mode': 'live-groups'})
    if method not in ('GET', 'POST'):
        return response(405, {'error': 'Method not supported.'})
    try:
        data = None
        if method == 'POST':
            if headers.get('origin') != origin:
                return response(403, {'error': 'Use the app from its own website.'})
            if headers.get('content-type', '').split(';')[0].strip() != 'application/json':
                return response(415, {'error': 'Send application/json.'})
            if len(raw.encode()) > 16000:
                raise ValueError('Request is too large.')
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError('Send a JSON object.')
        now = int(time.time())
        if method == 'POST' and path in ('/api/groups/create', '/api/groups/join', '/api/session'):
            username, password = credentials(data)
            if path == '/api/groups/create':
                group = secrets.token_hex(16)
                member, account = member_account(data, username, password)
                title = clean(data.get('group_name'), 'Group name', 2, 60)
                meeting = clean(data.get('meeting'), 'Handover point', 2, 120)
                places = data.get('places')
                if not isinstance(places, list) or not 2 <= len(places) <= 20:
                    raise ValueError('Add between 2 and 20 pickup locations.')
                names = [clean(p, 'Pickup location', 2, 60) for p in places]
                if len({n.casefold() for n in names}) != len(names):
                    raise ValueError('Each pickup location must have a different name.')
                state = {'version': 1, 'created': now, 'members': [member],
                    'places': [{'id': secrets.token_hex(8), 'name': n, 'color': 'green'} for n in names],
                    'trips': [], 'requests': [], 'loops': [], 'activity': [], 'operations': [],
                    'accounts': {username: account},
                    'group': {'id': group, 'name': title, 'meeting': meeting, 'owner': member['id']}}
                store.transact(group, lambda s: None, initial=state)
                uid = member['id']
            else:
                group = group_code(data)
                def enter(state):
                    if path == '/api/groups/join':
                        if username in state['accounts']:
                            raise ValueError('That username is taken in this group. Sign in or choose another.')
                        if len(state['members']) >= 16:
                            raise ValueError('This small-group version supports at most 16 members.')
                        member, account = member_account(data, username, password)
                        state['members'].append(member)
                        state['accounts'][username] = account
                        state['version'] += 1
                        return member['id']
                    account = state['accounts'].get(username)
                    if not account or account['locked_until'] > now:
                        return None
                    valid = hmac.compare_digest(password_hash(password, account['salt']), account['hash'])
                    if not valid:
                        account['failures'] += 1
                        if account['failures'] >= 5:
                            account['locked_until'] = now + 900
                            account['failures'] = 0
                        return None
                    account.update(failures=0, locked_until=0)
                    return account['member']
                uid = store.transact(group, enter)
                if uid is None:
                    return response(401, {'error': 'Sign-in failed. Check your details; after repeated attempts, wait 15 minutes.'})
            return response(200, {'ok': True}, cookie=session_cookie(group, uid, key, secure))
        if method == 'POST' and path == '/api/logout':
            return response(200, {'ok': True}, cookie=session_cookie('', '', key, secure, clear=True))
        if not who:
            return response(401, {'error': 'Sign in to your group to continue.'})
        group, uid = who
        def action(state):
            if not any(m['id'] == uid for m in state['members']):
                raise PermissionError('Your account is not a member of this group.')
            if expire(state, now):
                state['version'] += 1
            if method == 'GET' and path == '/api/board':
                return view(state, now, uid)
            if method == 'POST' and path == '/api/places':
                if uid != state['group']['owner']:
                    raise PermissionError('Only the group owner can add pickup locations.')
                name = clean(data.get('name'), 'Pickup location', 2, 60)
                if len(state['places']) >= 20 or any(p['name'].casefold() == name.casefold() for p in state['places']):
                    raise ValueError('Use a new location name; a group can have at most 20 locations.')
                state['places'].append({'id': secrets.token_hex(8), 'name': name, 'color': 'green'})
                state['version'] += 1
                return view(state, now, uid)
            if method == 'POST' and path.startswith('/api/actions/'):
                mutate(state, uid, path.rsplit('/', 1)[-1], data, now)
                return view(state, now, uid)
            raise LookupError('Not found.')
        return response(200, store.transact(group, action))
    except Conflict as exc:
        return response(409, {'error': str(exc)})
    except PermissionError as exc:
        return response(403, {'error': str(exc)})
    except LookupError:
        return response(404, {'error': 'Not found.'})
    except (ValueError, TypeError, UnicodeError) as exc:
        return response(400, {'error': str(exc) if isinstance(exc, ValueError) else 'Invalid request.'})
    except Exception:
        return response(503, {'error': 'The group is temporarily unavailable. Please retry.'})
