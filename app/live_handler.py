"""Public HTTPS entry point: identities come exclusively from signed sessions."""
import base64
import os
from .groups import CloudGroups
from .live import dispatch
from .hosted_handler import response


def handler(event, context):
    request = event.get('requestContext', {})
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    headers['cookie'] = '; '.join(event.get('cookies') or [])
    raw = event.get('body') or ''
    try:
        if len(raw) > 24000:
            raise ValueError()
        if event.get('isBase64Encoded'):
            raw = base64.b64decode(raw, validate=True).decode()
        return dispatch(CloudGroups(os.environ['ERRANDLOOP_TABLE']),
            os.environ.get('ERRANDLOOP_ACCESS_HASH', ''), request.get('http', {}).get('method', 'GET'),
            event.get('rawPath', '/'), headers, raw, 'https://' + request.get('domainName', ''), secure=True)
    except (ValueError, UnicodeError):
        return response(400, {'error': 'Invalid request body.'})
