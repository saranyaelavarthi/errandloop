"""One cookie jar completes a rehearsal through the same public HTTP actions."""
import http.cookiejar
import json
import pytest
import urllib.error
import socket
import subprocess
import sys
import urllib.request
import urllib.parse
import uuid


def test_one_window_rehearsal():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    process = subprocess.Popen([sys.executable, '-m', 'app.server', '--rehearsal', '--port', str(port)], stdout=subprocess.PIPE, text=True)
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def call(path, data=None, form=False):
        raw = (urllib.parse.urlencode(data) if form else json.dumps(data)).encode() if data is not None else None
        req = urllib.request.Request(base+path, data=raw, headers={'Origin': base, 'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json'})
        with client.open(req, timeout=10) as response:
            return response.read().decode()
    def board():
        return json.loads(call('/api/board'))
    def act(command, **fields):
        return call('/api/actions/'+command, {'version':board()['version'], 'operation':uuid.uuid4().hex, **fields})
    def switch(name):
        call('/rehearsal/switch', {'username':name}, True)
    try:
        assert 'running at' in process.stdout.readline()
        html = call('/')
        assert html.count('class="demo-strip"') == 1
        assert '/rehearsal/switch' in html
        blocked = urllib.request.Request(base+'/rehearsal/switch', data=b'username=ravi', headers={'Origin':'https://other.example'})
        with pytest.raises(urllib.error.HTTPError) as error:
            client.open(blocked)
        assert error.value.code == 403
        state = board()
        candidate = state['matching']['candidates'][0]
        act('propose', id=candidate['id'])
        for name in ['ravi', 'meena']:
            switch(name)
            act('accept', id=board()['loops'][0]['id'])
        for name in ['asha', 'ravi', 'meena']:
            switch(name)
            state = board(); loop = state['loops'][0]
            edge = next(e for e in loop['edges'] if e['giver'] == state['actor'])
            act('collected', id=loop['id'], request=edge['request'])
        for name in ['asha', 'ravi', 'meena']:
            switch(name)
            state = board(); loop = state['loops'][0]
            edge = next(e for e in loop['edges'] if e['receiver'] == state['actor'])
            act('received', id=loop['id'], request=edge['request'])
        assert board()['metrics'] == {'completed':1, 'handovers':3}
    finally:
        process.terminate()
        process.communicate(timeout=10)
