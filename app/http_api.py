import json
import time
from .service import mutate, view, Conflict


def handle(store, method, path, member, body=None):
    now = int(time.time())
    try:
        if method == 'GET' and path == '/api/health':
            return 200, {'ok': True, 'policyEngine': 'Cedar', 'mode': 'trusted-group-demo'}
        if method == 'GET' and path == '/api/board':
            def read(state):
                if member not in {m['id'] for m in state['members']}:
                    raise PermissionError('Unknown demo participant.')
                return view(state, now, member)
            return 200, store.transact(read, now)
        if method == 'POST' and path.startswith('/api/actions/'):
            command = path.rsplit('/', 1)[-1]
            def update(state):
                mutate(state, member, command, body, now)
                return view(state, now, member)
            return 200, store.transact(update, now)
        return 404, {'error': 'Not found.'}
    except PermissionError as exc:
        return 403, {'error': str(exc)}
    except Conflict as exc:
        return 409, {'error': str(exc)}
    except (ValueError, KeyError, TypeError) as exc:
        return 400, {'error': str(exc) if isinstance(exc, ValueError) else 'Invalid request fields.'}


SECURITY_HEADERS = {
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Cache-Control': 'no-store',
}
