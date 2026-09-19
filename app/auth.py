"""AWS Cedar engine, via the separately maintained cedarpy Python binding."""
from pathlib import Path
import cedarpy

POLICIES = cedarpy.PolicySet.from_str(Path(__file__).with_name('policies.cedar').read_text())


def ref(kind, uid):
    return {'__entity': {'type': kind, 'id': uid}}


def authorize(member, action, kind, rid, attrs, group='courtyard'):
    result = cedarpy.is_authorized(
        {'principal': {'type': 'Member', 'id': member},
         'action': {'type': 'Action', 'id': action},
         'resource': {'type': kind, 'id': rid}, 'context': {}}, POLICIES,
        [{'uid': {'type': 'Member', 'id': member}, 'attrs': {'group': group}, 'parents': []},
         {'uid': {'type': kind, 'id': rid}, 'attrs': attrs, 'parents': []}])
    if not result.allowed:
        raise PermissionError('Only the relevant participant can perform this action.')
    return True
