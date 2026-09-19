"""Atomic, isolated group storage. Account hashes never leave the service layer."""
import json
import os
import secrets
import sqlite3
from .service import Conflict


class LocalGroups:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS groups (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS config (id TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO config VALUES (?, ?)', ('session-key', secrets.token_hex(32)))
            self.key = db.execute('SELECT value FROM config WHERE id=?', ('session-key',)).fetchone()[0]

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def transact(self, group, operation, initial=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT payload FROM groups WHERE id=?', (group,)).fetchone()
            if initial is not None and row:
                raise Conflict('Group code collision. Please try again.')
            if not row and initial is None:
                raise ValueError('Group not found. Check your group code.')
            state = json.loads(row[0]) if row else initial
            result = operation(state)
            payload = json.dumps(state)
            if len(payload.encode()) > 330000:
                raise Conflict('This group has reached its storage limit. Export its activity and create a new group.')
            db.execute('INSERT INTO groups VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (group, payload))
            return result


class CloudGroups:
    def __init__(self, table):
        import boto3
        self.table = boto3.resource('dynamodb').Table(table)

    def transact(self, group, operation, initial=None):
        key = {'id': 'group:' + group}
        stored = self.table.get_item(Key=key, ConsistentRead=True).get('Item')
        if initial is not None and stored:
            raise Conflict('Group code collision. Please try again.')
        if not stored and initial is None:
            raise ValueError('Group not found. Check your group code.')
        state = json.loads(stored['payload']) if stored else initial
        before = json.dumps(state)
        result = operation(state)
        payload = json.dumps(state)
        if len(payload.encode()) > 330000:
            raise Conflict('This group has reached its storage limit. Export its activity and create a new group.')
        if stored and payload == before:
            return result
        revision = int(stored['revision']) if stored else 0
        args = {'Item': {**key, 'payload': payload, 'revision': revision + 1},
                'ConditionExpression': 'revision = :old' if stored else 'attribute_not_exists(id)'}
        if stored:
            args['ExpressionAttributeValues'] = {':old': revision}
        try:
            self.table.put_item(**args)
        except self.table.meta.client.exceptions.ConditionalCheckFailedException as exc:
            raise Conflict('The group changed at the same time. Please try again.') from exc
        return result
