import time
from app.groups import LocalGroups
from app.rehearsal import prepare
from app.service import view


def test_rehearsal_uses_real_accounts_and_only_three_way_cycle(tmp_path):
    real = LocalGroups(tmp_path / 'real.sqlite3')
    real.transact('untouched', lambda s: None, initial={'marker':'preserve'})
    demo = LocalGroups(tmp_path / 'rehearsal.sqlite3')
    group, accounts = prepare(demo)
    state = demo.transact(group, lambda s: s)
    assert len(state['accounts']) == len(state['members']) == 3
    assert all('(test)' in m['name'] for m in state['members'])
    assert [a['username'] for a in accounts] == ['asha','ravi','meena']
    result = view(state, int(time.time()))
    assert len(result['matching']['candidates']) == 1
    assert len(result['matching']['candidates'][0]['members']) == 3
    assert result['metrics']['handovers'] == 0
    assert real.transact('untouched', lambda s:s)['marker'] == 'preserve'
