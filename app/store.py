import json
import os
import sqlite3
from .seed import seed
from .service import Conflict, expire


class SQLiteStore:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS board (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO board VALUES (1, ?)', (json.dumps(seed()),))

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def transact(self, operation, now):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state = json.loads(db.execute('SELECT payload FROM board WHERE id=1').fetchone()[0])
            if expire(state, now):
                state['version'] += 1
            result = operation(state)
            db.execute('UPDATE board SET payload=? WHERE id=1', (json.dumps(state),))
            return result

    def reset(self, now):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = json.loads(db.execute('SELECT payload FROM board WHERE id=1').fetchone()[0])
            new = seed(now)
            new['version'] = old['version'] + 1
            db.execute('UPDATE board SET payload=? WHERE id=1', (json.dumps(new),))


class DynamoStore:
    """A small group's aggregate fits in one item; CAS prevents double reservation.

    Deliberately scoped to a small hackathon group, not an unbounded city board.
    No scans, cross-item transactions, or silent last-write-wins updates.
    """
    def __init__(self, table_name):
        import boto3
        self.table = boto3.resource('dynamodb').Table(table_name)

    def transact(self, operation, now):
        response = self.table.get_item(Key={'id': 'courtyard'}, ConsistentRead=True)
        stored = response.get('Item')
        state = json.loads(stored['payload']) if stored else seed(now)
        revision = int(stored['revision']) if stored else 0
        before = json.dumps(state)
        if expire(state, now):
            state['version'] += 1
        result = operation(state)
        payload = json.dumps(state)
        if payload != before or not stored:
            if len(payload.encode()) > 330000:
                raise Conflict('Demo storage is full. Export and reset the demo before adding more posts.')
            args = {'Item': {'id': 'courtyard', 'payload': payload, 'revision': revision + 1}}
            if stored:
                args.update(ConditionExpression='revision = :old', ExpressionAttributeValues={':old': revision})
            else:
                args['ConditionExpression'] = 'attribute_not_exists(id)'
            try:
                self.table.put_item(**args)
            except self.table.meta.client.exceptions.ConditionalCheckFailedException as exc:
                raise Conflict('Someone changed this circle at the same time. Refresh and try again.') from exc
        return result


def get_store():
    table = os.environ.get('ERRANDLOOP_TABLE')
    if table:
        return DynamoStore(table)
    return SQLiteStore(os.environ.get('ERRANDLOOP_DB', 'errandloop.sqlite3'))
