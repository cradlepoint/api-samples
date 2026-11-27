"""
Backward-compatibility tests against the original single-file ncm
(ncm/ncm/ncm.py, v0.0.74).

1. Surface: every public class, method, signature and module-level name of
   the original exists unchanged in ncm2.
2. Behavior: every public v2/v3 method is called on both libraries against
   the same recording fake HTTP layer. The wire calls and results must be
   identical, except for the two intentional changes:
     - configuration bodies never contain masked "*" secrets, and
     - copy_router_configuration replaces via PUT instead of merging via PATCH.
"""
import inspect
import unittest

from _support import (ncm, reference_module, clean_env, recording, call_args,
                      outcome, public_methods, V2_KEYS, V3_TOKEN)
from ncm._base import strip_masked_secrets, _CONFIG_URL_RE

REF = reference_module()
CLASSES = ['BaseNcmClient', 'NcmClientv2', 'NcmClientv3', 'NcmClientv2v3', 'NcmClient']

# Methods whose wire behavior is intentionally different (covered by their
# own tests in test_secret_filter.py).
INTENTIONAL = {'copy_router_configuration'}

# Methods that gained optional parameters (old calls are unaffected).
EXTENDED_SIGNATURES = {
    'NcmClientv2.copy_router_configuration',   # replace=False
}

# Realistic keyword arguments for methods the generic argument synthesis can't
# get past input validation, so they reach the HTTP layer too.
OVERRIDES = {
    'NcmClientv2': {
        'patch_group': dict(group_id=1, configuration=[{"system": {"users": {"0": {"password": "*"}}},
                                                         "wan": {"x": 1}}, []]),
        'remove_router_from_group': dict(router_id=1),
        'set_encrypted_value_by_group': dict(group_id=1, name='k', key='v'),
        'set_encrypted_value_by_router': dict(router_id=1, name='k', key='v'),
        'set_ncm_api_keys_by_group': dict(group_id=1, x_ecm_api_id='a', x_ecm_api_key='b',
                                          x_cp_api_id='c', x_cp_api_key='d'),
        'set_ncm_api_keys_by_router': dict(router_id=1, x_ecm_api_id='a', x_ecm_api_key='b',
                                           x_cp_api_id='c', x_cp_api_key='d'),
    },
    'NcmClientv3': {
        'create_esim_profiles_manage': dict(body={"data": {"type": "x", "attributes": {}}}),
        'create_exchange_resource': dict(resource_name='r', resource_type='exchange_fqdn_resources',
                                         site_id='s1', domain='example.com'),
        'create_exchange_site': dict(name='s', exchange_network_id='n1', router_id='1'),
        'create_migration': dict(
            migration_type='create_organizations',
            attributes={'organization_name': 'o', 'idle_timeout': 30,
                        'enhanced_login_security_enabled': False, 'mfa_required': False},
            relationships={'organization_administrator': {'data': {'type': 'users', 'id': 'u1'}}}),
        'create_remote_connect_profile': dict(
            profile_type='remote_connect_http_profile',
            attributes={'name': 'p', 'port': 80, 'address': '192.168.0.1'},
            relationships={'router': {'data': {'type': 'routers', 'id': '1'}}}),
        'create_starlink_interface_stow': dict(interface_id='i1', action='stow'),
        'delete_exchange_resource': dict(resource_id='r1'),
        'delete_exchange_site': dict(site_id='s1'),
        'get_modem_software_versions': dict(group='1'),
        'get_modem_upgrades': dict(group='1', upgrade_type='modem_upgrade_parent'),
        'get_unmasked_wifi_passwords': dict(router='1'),
        'update_esim_profile_activation': dict(activation_id='a1', body={"data": {}}),
        'update_exchange_resource': dict(resource_id='r1', name='r2'),
        'update_exchange_site': dict(site_id='s1', name='s2'),
    },
}


def expected_new_call(old_call):
    """What ncm2 should send for a call the original sent."""
    call = dict(old_call)
    body = call['body']
    if (call['method'] in ('PUT', 'PATCH', 'POST') and _CONFIG_URL_RE.search(call['url'])
            and isinstance(body, dict) and 'configuration' in body):
        call['body'] = {**body, 'configuration': strip_masked_secrets(body['configuration'])}
    return call


@unittest.skipIf(REF is None, 'ncm 0.0.74 reference not available (git history or NCM_REFERENCE_SRC)')
class SurfaceParity(unittest.TestCase):

    def test_module_level_names(self):
        old = {n for n in dir(REF) if not n.startswith('_')}
        new = set(dir(ncm))
        self.assertEqual(sorted(old - new), [], 'module names missing from ncm2')

    def test_legacy_ncm_object_names(self):
        from ncm import ncm as legacy
        old = {n for n in dir(REF.ncm) if not n.startswith('_')}
        new = set(dir(legacy))
        self.assertEqual(sorted(old - new), [], 'names missing from "from ncm import ncm"')

    def test_class_methods_and_signatures(self):
        """
        Every old signature is unchanged, or extended only by new optional
        parameters after the old ones (so every existing call binds the same).
        """
        for cls_name in CLASSES:
            old_cls, new_cls = getattr(REF, cls_name), getattr(ncm, cls_name)
            for name in public_methods(old_cls):
                with self.subTest(cls=cls_name, method=name):
                    self.assertTrue(hasattr(new_cls, name), f'{cls_name}.{name} missing')
                    old_params = list(inspect.signature(getattr(old_cls, name)).parameters.values())
                    new_params = list(inspect.signature(getattr(new_cls, name)).parameters.values())
                    self.assertEqual([str(p) for p in new_params[:len(old_params)]],
                                     [str(p) for p in old_params],
                                     'existing parameters changed')
                    for extra in new_params[len(old_params):]:
                        self.assertIsNot(extra.default, inspect.Parameter.empty,
                                         f'new parameter {extra.name!r} must be optional')
                    # Any extension must be one of the documented ones.
                    if len(new_params) > len(old_params):
                        self.assertIn(f'{cls_name}.{name}', EXTENDED_SIGNATURES)

    def test_module_function_signatures(self):
        for name in ('get_ncm_instance', 'set_api_keys', 'set_ncm_instance',
                     'reset_ncm_instance'):
            with self.subTest(func=name):
                self.assertEqual(str(inspect.signature(getattr(REF, name))),
                                 str(inspect.signature(getattr(ncm, name))))

    def test_constants(self):
        for name in ('V3_MEDIA_TYPE', 'V3_ATOMIC_MEDIA_TYPE', 'V3_RETRY_ON'):
            self.assertEqual(getattr(REF, name), getattr(ncm, name))


@unittest.skipIf(REF is None, 'ncm 0.0.74 reference not available (git history or NCM_REFERENCE_SRC)')
class BehaviorParity(unittest.TestCase):
    """Same inputs, same canned responses -> same wire calls and results."""

    @staticmethod
    def _invoke(cls_name, client, name):
        kwargs = OVERRIDES.get(cls_name, {}).get(name)
        method = getattr(client, name)
        if kwargs is not None:
            import copy
            return outcome(lambda: method(**copy.deepcopy(kwargs)))
        return outcome(method, *call_args(method))

    def _compare_class(self, cls_name, make):
        old_cls = getattr(REF, cls_name)
        compared = stripped = 0
        no_http = []
        for name in public_methods(old_cls):
            if name in INTENTIONAL:
                continue
            with self.subTest(cls=cls_name, method=name):
                # Fresh args per run: some methods mutate what they are given.
                with recording() as old_rec:
                    old_out = self._invoke(cls_name, make(REF), name)
                with recording() as new_rec:
                    new_out = self._invoke(cls_name, make(ncm), name)
                expected = [expected_new_call(c) for c in old_rec.calls]
                self.assertEqual(new_rec.calls, expected, 'wire calls differ')
                self.assertEqual(new_out, old_out, 'result differs')
                compared += 1
                stripped += expected != old_rec.calls
                if not old_rec.calls:
                    no_http.append(name)
        # Only methods that never touch the network may skip HTTP; anything
        # else here means the comparison didn't exercise it.
        self.assertEqual(sorted(no_http),
                         sorted({'log', 'set_api_key', 'set_api_keys'} & set(no_http)),
                         f'{cls_name} methods that never reached HTTP: {no_http}')
        return compared, stripped

    def test_v2_methods(self):
        with clean_env():
            compared, stripped = self._compare_class(
                'NcmClientv2', lambda m: m.NcmClientv2(api_keys=dict(V2_KEYS), log_events=False))
        self.assertGreater(compared, 90)
        # The filter must actually have fired on the config writers.
        self.assertGreaterEqual(stripped, 4)

    def test_v3_methods(self):
        with clean_env():
            compared, _ = self._compare_class(
                'NcmClientv3', lambda m: m.NcmClientv3(api_key=V3_TOKEN))
        self.assertGreater(compared, 50)

    def test_combined_client_routing(self):
        """NcmClientv2v3 routes each method to the same API version."""
        with clean_env():
            old = REF.NcmClientv2v3(api_keys=dict(V2_KEYS), api_key=V3_TOKEN, log_events=False)
            new = ncm.NcmClientv2v3(api_keys=dict(V2_KEYS), api_key=V3_TOKEN, log_events=False)
            for name in old.get_available_methods():
                with self.subTest(method=name):
                    old_owner = type(getattr(old, name).__self__).__name__
                    new_owner = type(getattr(new, name).__self__).__name__
                    self.assertEqual(old_owner, new_owner)


if __name__ == '__main__':
    unittest.main()
