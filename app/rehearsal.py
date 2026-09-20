"""Synthetic three-account rehearsal through the real application routes."""
import json
import secrets
import time
import uuid
from .live import dispatch


def prepare(store):
    origin = 'http://rehearsal.local'
    def call(path, data=None, cookie=''):
        response = dispatch(store, store.key, 'POST' if data is not None else 'GET', path,
            {'origin': origin, 'content-type': 'application/json', 'cookie': cookie},
            json.dumps(data) if data is not None else '', origin, secure=False)
        if response['statusCode'] != 200:
            raise RuntimeError('Rehearsal setup failed: ' + response['body'])
        return response
    credentials = []
    group = None
    now = int(time.time())
    for i, name in enumerate(['Asha', 'Ravi', 'Meena']):
        password = secrets.token_urlsafe(15)
        account = {'name': name + ' (test)', 'username': name.lower(), 'password': password}
        if group is None:
            result = call('/api/groups/create', {**account, 'group_name': 'REHEARSAL - simulated pickups',
                'meeting': 'Test reception', 'places': ['Print shop', 'Library', 'Grocery']})
        else:
            result = call('/api/groups/join', {**account, 'group_code': group})
        cookie = result['cookies'][0].split(';')[0]
        board = json.loads(call('/api/board', cookie=cookie)['body'])
        group = board['group']['id']
        places = [p['id'] for p in board['places']]
        for command, fields in [
            ('trip', {'destination': places[i], 'depart': now+3600, 'returns': now+5400, 'capacity': 1}),
            ('request', {'destination': places[(i+1)%3], 'item': ['Test reserved book', 'Test prepaid grocery bag', 'Test print envelope'][i],
                         'ready': now, 'deadline': now+7200, 'units': 1})]:
            board = json.loads(call('/api/board', cookie=cookie)['body'])
            call('/api/actions/'+command, {'version': board['version'], 'operation': uuid.uuid4().hex,
                                          **fields}, cookie)
        credentials.append({'username': account['username'], 'password': password})
    return group, credentials
