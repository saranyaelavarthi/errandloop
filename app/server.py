"""Local demo server. Explicit member switching is for demo use, not authentication."""
import argparse
import os
import json
import mimetypes
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qs
import time
import threading
import tempfile
import webbrowser
from .store import get_store
from .http_api import handle, SECURITY_HEADERS

STATIC = Path(__file__).with_name('static')
ASSETS = {'/': 'index.html', '/index.html': 'index.html', '/app.js': 'app.js',
          '/boot.js': 'boot.js', '/style.css': 'style.css', '/favicon.svg': 'favicon.svg', '/manifest.json': 'manifest.json'}


def main():
    parser = argparse.ArgumentParser(description='ErrandLoop local demo')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--open', action='store_true', help='Open the app in your default browser')
    parser.add_argument('--demo', action='store_true', help='Use the fictional sample board')
    parser.add_argument('--rehearsal', action='store_true', help='Temporary three-account test group; no changes to real groups')
    args = parser.parse_args()
    if args.rehearsal and args.demo:
        parser.error('Choose either --rehearsal or --demo.')
    if args.rehearsal and args.host not in ('127.0.0.1', 'localhost', '::1'):
        parser.error('Rehearsal account switching is restricted to localhost.')
    rehearsal_dir = None
    if args.rehearsal and args.port == 8000:
        args.port = 8001
    if args.demo:
        store = get_store()
    else:
        from .groups import LocalGroups
        from .live import dispatch
        if args.rehearsal:
            from .rehearsal import prepare
            rehearsal_dir = tempfile.TemporaryDirectory(prefix='errandloop-rehearsal-')
            store = LocalGroups(Path(rehearsal_dir.name) / 'rehearsal.sqlite3')
            group_code, accounts = prepare(store)
        else:
            store = LocalGroups(os.environ.get('ERRANDLOOP_LIVE_DB', 'errandloop-groups.sqlite3'))

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, payload, content_type='application/json; charset=utf-8'):
            if isinstance(payload, (dict, list)):
                payload = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            for name, value in SECURITY_HEADERS.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def live_request(self, method):
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size < 0 or size > 16000:
                    self.send(413, {'error': 'Request is too large.'}); return
                raw = self.rfile.read(size).decode() if method == 'POST' else ''
                path = urlsplit(self.path).path
                origin = 'http://' + self.headers.get('Host', '')
                headers = dict(self.headers)
                login_cookie = None
                if args.rehearsal:
                    if self.headers.get('Host', '').split(':')[0] not in ('localhost', '127.0.0.1'):
                        self.send(403, {'error': 'Use localhost for rehearsal.'}); return
                    switching = method == 'POST' and path == '/rehearsal/switch'
                    if switching and self.headers.get('Origin') != origin:
                        self.send(403, {'error': 'Open rehearsal on this computer.'}); return
                    first_visit = method == 'GET' and path == '/' and dispatch(store, store.key, 'GET', '/api/board', headers, '', origin, secure=False)['statusCode'] == 401
                    if switching or first_visit:
                        username = parse_qs(raw).get('username', ['asha'])[0] if switching else 'asha'
                        account = next((a for a in accounts if a['username'] == username), None)
                        if account is None:
                            self.send(400, {'error': 'Choose a prepared test participant.'}); return
                        login = dispatch(store, store.key, 'POST', '/api/session',
                            {'origin': origin, 'content-type': 'application/json'},
                            json.dumps({**account, 'group_code': group_code}), origin, secure=False)
                        login_cookie = login['cookies'][0]
                        if switching:
                            self.send_response(303)
                            self.send_header('Location', '/')
                            self.send_header('Set-Cookie', login_cookie)
                            self.send_header('Content-Length', '0')
                            self.end_headers(); return
                        headers['Cookie'] = login_cookie.split(';')[0]
                result = dispatch(store, store.key, method, path, headers, raw, origin, secure=False)
                if login_cookie:
                    result.setdefault('cookies', []).append(login_cookie)
                if args.rehearsal and result['headers'].get('Content-Type', '').startswith('text/html'):
                    import re
                    result['body'] = re.sub(r'<div class="demo-strip">.*?</div>', '<div class="demo-strip"><span><strong>Rehearsal</strong> · Simulated pickups</span><form method="post" action="/rehearsal/switch" class="rehearsal-seats" aria-label="Choose test participant"><span>Continue as</span><button name="username" value="asha">Asha</button><button name="username" value="ravi">Ravi</button><button name="username" value="meena">Meena</button></form></div>', result['body'], count=1, flags=re.S)
                    if '/onboarding.js' in result['body']:
                        result['body'] = result['body'].replace('<form id="account-form">', '<div class="callout"><strong>Your three-person circle is ready.</strong><p>Choose Asha, Ravi or Meena in the banner above. No manual sign-in is needed.</p></div><form id="account-form">')
                body = result['body'].encode()
                self.send_response(result['statusCode'])
                for key, value in result['headers'].items(): self.send_header(key, value)
                for cookie in result.get('cookies', []): self.send_header('Set-Cookie', cookie)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (ValueError, UnicodeError):
                self.send(400, {'error': 'Invalid request.'})

        def do_GET(self):
            if not args.demo:
                self.live_request('GET'); return
            path = urlsplit(self.path).path
            if path in ASSETS:
                file = STATIC / ASSETS[path]
                mime = {'.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html', '.svg': 'image/svg+xml', '.json': 'application/json'}[file.suffix]
                self.send(200, file.read_bytes(), mime + '; charset=utf-8')
            else:
                self.send(*handle(store, 'GET', path, self.headers.get('X-Demo-Member', 'you')))

        def do_POST(self):
            if not args.demo:
                self.live_request('POST'); return
            # JSON + custom header + same-origin guard prevents cross-origin form writes.
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                self.send(403, {'error': 'Cross-origin writes are disabled.'}); return
            if not self.headers.get('Content-Type', '').startswith('application/json'):
                self.send(415, {'error': 'Send application/json.'}); return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 16000:
                    self.send(413, {'error': 'Request is too large or empty.'}); return
                body = json.loads(self.rfile.read(size))
                path = urlsplit(self.path).path
                if path == '/api/reset':
                    store.reset(int(time.time()))
                    self.send(*handle(store, 'GET', '/api/board', self.headers.get('X-Demo-Member', 'you')))
                else:
                    self.send(*handle(store, 'POST', path, self.headers.get('X-Demo-Member', 'you'), body))
            except (ValueError, json.JSONDecodeError):
                self.send(400, {'error': 'Invalid JSON request.'})
            except Exception:
                self.send(500, {'error': 'Unable to save. Your previous board is unchanged; try again.'})

        def log_message(self, format, *values):
            # Never log request bodies or pickup notes.
            pass

    try:
        server = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as error:
        parser.exit(1, f'Cannot start on {args.host}:{args.port}: {error}\n'
                    'If another ErrandLoop window is running, stop it with Ctrl+C.\n'
                    'Or choose another port: python scripts/run_local.py --port 8001\n')
    browser_host = 'localhost' if args.rehearsal and args.host == '127.0.0.1' else args.host
    print(f'ErrandLoop is running at http://{browser_host}:{args.port}', flush=True)
    print(('Temporary rehearsal group.' if args.rehearsal else 'Fictional sample board.' if args.demo else 'Create a group or sign in. Your data is saved locally.') + ' Press Ctrl+C to stop.', flush=True)
    if args.rehearsal:
        print('REHEARSAL ONLY: test accounts and simulated goods. Data is temporary.', flush=True)
        print('Opens as Asha automatically. Use the banner to switch to Ravi or Meena. Group code: ' + group_code, flush=True)
        for account in accounts:
            print('Test username: ' + account['username'] + ' | Test password: ' + account['password'], flush=True)
        print('One browser is enough. Use the participant buttons in the rehearsal banner.', flush=True)
    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(f'http://{browser_host}:{args.port}')).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped. Real group data is preserved.')
    finally:
        server.server_close()
        if rehearsal_dir:
            rehearsal_dir.cleanup()


if __name__ == '__main__':
    main()
