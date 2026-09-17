"""IAM-authenticated AWS demo API; explicit demo actors are not real user identities."""
import base64
import json
import os
from .http_api import handle
from .store import DynamoStore


def handler(event, context):
    if not event.get('requestContext', {}).get('identity', {}).get('userArn'):
        return {'statusCode': 403, 'body': json.dumps({'error': 'An IAM-authenticated request is required.'})}
    headers = {k.lower(): v for k, v in event.get('headers', {}).items()}
    raw = event.get('body') or ''
    try:
        if event.get('isBase64Encoded'):
            raw = base64.b64decode(raw, validate=True).decode()
        if len(raw.encode()) > 16000:
            raise ValueError('Request too large.')
        body = json.loads(raw) if raw else None
        status, result = handle(DynamoStore(os.environ['ERRANDLOOP_TABLE']), event['httpMethod'],
                                event['path'], headers.get('x-demo-member', 'you'), body)
    except (ValueError, UnicodeError):
        status, result = 400, {'error': 'Invalid request body.'}
    return {'statusCode': status, 'headers': {'Content-Type': 'application/json', 'Cache-Control': 'no-store'},
            'body': json.dumps(result)}
