"""Local demo server. Explicit member switching is for demo use, not authentication."""
import argparse
import os
import json
import mimetypes
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit
import time
import threading
import webbrowser
from .store import get_store
from .http_api import handle, SECURITY_HEADERS

STATIC = Path(__file__).with_name('static')
ASSETS = {'/': 'index.html', '/index.html': 'index.html', '/app.js': 'app.js',
          '/style.css': 'style.css', '/favicon.svg': 'favicon.svg', '/manifest.json': 'manifest.json'}


def main():
    parser = argparse.ArgumentParser(description='ErrandLoop local demo')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--open', action='store_true', help='Open the app in your default browser')
    parser.add_argument('--demo', action='store_true', help='Use the fictional sample board')
    args = parser.parse_args()
    if args.demo:
        store = get_store()
    else:
        from .groups import LocalGroups
        from .live import dispatch
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
                result = dispatch(store, store.key, method, urlsplit(self.path).path, dict(self.headers), raw, 'http://' + self.headers.get('Host', ''), secure=False)
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
                self.send(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
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

    print(f'ErrandLoop is running at http://{args.host}:{args.port}', flush=True)
    print(('Fictional sample board.' if args.demo else 'Create a group or sign in. Your data is saved locally.') + ' Press Ctrl+C to stop.', flush=True)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    if args.open:
        threading.Timer(0.5, lambda: webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
    server.serve_forever()


if __name__ == '__main__':
    main()
