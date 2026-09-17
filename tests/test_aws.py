import json
import pytest
from botocore.stub import Stubber
from app.seed import seed
from app.store import DynamoStore
from app.service import Conflict

NOW = 1_000_000


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test-only')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test-only')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'ap-south-1')
    return DynamoStore('ErrandLoopTest')


def test_dynamodb_reads_consistently_and_rejects_racing_write(store):
    with Stubber(store.table.meta.client) as stub:
        stub.add_response('get_item', {'Item': {'id':{'S':'courtyard'},'payload':{'S':json.dumps(seed(NOW))},'revision':{'N':'7'}}},
                          {'TableName':'ErrandLoopTest','Key':{'id':'courtyard'},'ConsistentRead':True})
        stub.add_client_error('put_item','ConditionalCheckFailedException','A concurrent reservation won.')
        with pytest.raises(Conflict, match='same time'):
            store.transact(lambda s:s.update(version=2),NOW)
        stub.assert_no_pending_responses()


def test_dynamodb_unchanged_reads_do_not_write(store):
    with Stubber(store.table.meta.client) as stub:
        stub.add_response('get_item', {'Item': {'id':{'S':'courtyard'},'payload':{'S':json.dumps(seed(NOW))},'revision':{'N':'7'}}},
                          {'TableName':'ErrandLoopTest','Key':{'id':'courtyard'},'ConsistentRead':True})
        assert store.transact(lambda s:s['version'],NOW)==1
        stub.assert_no_pending_responses()


def test_dynamodb_write_has_revision_guard(store):
    changed=seed(NOW);changed['version']=2
    with Stubber(store.table.meta.client) as stub:
        stub.add_response('get_item', {'Item': {'id':{'S':'courtyard'},'payload':{'S':json.dumps(seed(NOW))},'revision':{'N':'7'}}})
        stub.add_response('put_item', {}, {'TableName':'ErrandLoopTest',
             'Item':{'id':'courtyard','payload':json.dumps(changed),'revision':8},
             'ConditionExpression':'revision = :old','ExpressionAttributeValues':{':old':7}})
        store.transact(lambda s:s.update(version=2),NOW)
        stub.assert_no_pending_responses()
