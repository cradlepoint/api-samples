"""
Module-level API: import styles, the singleton, auto-routing, and the ncm2
additions (ncm.v2 / ncm.v3, set_v2_keys / set_v3_key / set_keys, aliases).
"""
import os
import unittest
from unittest import mock

from _support import ncm, reference_module, clean_env, recording, V2_KEYS, V3_TOKEN

REF = reference_module()
ENV = {'X_CP_API_ID': 'cp-id', 'X_CP_API_KEY': 'cp-key',
       'X_ECM_API_ID': 'ecm-id', 'X_ECM_API_KEY': 'ecm-key'}


class ImportStyles(unittest.TestCase):

    def test_from_ncm_import_ncm(self):
        from ncm import ncm as legacy
        self.assertIs(legacy.NcmClient, ncm.NcmClient)
        self.assertTrue(callable(legacy.get_routers))
        self.assertTrue(callable(legacy.set_api_keys))

    def test_from_ncm_ncm_import_classes(self):
        from ncm.ncm import NcmClient, NcmClientv2, NcmClientv3, NcmClientv2v3  # noqa: F401
        self.assertIs(NcmClientv2, ncm.NcmClientv2)

    def test_new_names(self):
        self.assertIs(ncm.NcmV2, ncm.NcmClientv2)
        self.assertIs(ncm.NcmV3, ncm.NcmClientv3)
        self.assertIs(ncm.NcmClientv2.create_group, ncm.NcmClientv2.create_group_by_parent_id)
        self.assertIs(ncm.NcmClientv2.rename_router, ncm.NcmClientv2.rename_router_by_id)


class Singleton(unittest.TestCase):

    def setUp(self):
        ncm.reset_ncm_instance()
        if REF:
            REF.reset_ncm_instance()

    tearDown = setUp

    def test_no_keys_raises_same_as_before(self):
        with clean_env():
            with self.assertRaises(RuntimeError) as new_err:
                ncm.get_ncm_instance()
            if REF:
                with self.assertRaises(RuntimeError) as old_err:
                    REF.get_ncm_instance()
                self.assertEqual(str(new_err.exception), str(old_err.exception))

    def test_factory_types(self):
        with clean_env():
            self.assertIsInstance(ncm.NcmClient(api_keys=dict(V2_KEYS)), ncm.NcmClientv2)
            self.assertIsInstance(ncm.NcmClient(api_key=V3_TOKEN), ncm.NcmClientv3)
            both = ncm.NcmClient(api_keys={**V2_KEYS, 'token': V3_TOKEN})
            self.assertIsInstance(both, ncm.NcmClientv2v3)

    def test_env_autoload_and_module_routing(self):
        with clean_env(), mock.patch.dict(os.environ, {**ENV, 'NCM_API_TOKEN': V3_TOKEN}):
            with recording() as rec:
                ncm.get_routers(limit=1)
                ncm.get_subscriptions(limit=1)
        self.assertIn('/api/v2/routers/', rec.calls[0]['url'])
        self.assertIn('/api/v3/subscriptions', rec.calls[1]['url'])

    def test_set_api_keys_module_level(self):
        with clean_env():
            inst = ncm.set_api_keys(dict(V2_KEYS))
            self.assertIsInstance(inst, ncm.NcmClientv2)
            self.assertIs(ncm.get_ncm_instance(), inst)


class VersionProxiesAndKeyHelpers(unittest.TestCase):

    def setUp(self):
        ncm.reset_ncm_instance()

    tearDown = setUp

    def test_v2_v3_proxies_use_singleton(self):
        with clean_env():
            ncm.set_api_keys({**V2_KEYS, 'token': V3_TOKEN})
            inst = ncm.get_ncm_instance()
            self.assertIs(ncm.v2.session, inst.v2.session)
            self.assertIs(ncm.v3.session, inst.v3.session)

    def test_missing_version_raises_clearly(self):
        with clean_env():
            ncm.set_api_keys(dict(V2_KEYS))
            with self.assertRaises(RuntimeError) as err:
                ncm.v3.get_subscriptions()
            self.assertIn('NCM_API_TOKEN', str(err.exception))

    def test_set_v3_key_keeps_v2_keys(self):
        with clean_env():
            ncm.set_v2_keys(dict(V2_KEYS))
            ncm.set_v3_key(V3_TOKEN)
            inst = ncm.get_ncm_instance()
            self.assertIsInstance(inst, ncm.NcmClientv2v3)
            self.assertEqual(inst.v2.session.headers['X-CP-API-ID'], 'cp-id')
            self.assertEqual(inst.v3.session.headers['Authorization'], f'Bearer {V3_TOKEN}')

    def test_set_v2_keys_keeps_token(self):
        with clean_env():
            ncm.set_v3_key(V3_TOKEN)
            ncm.set_v2_keys(dict(V2_KEYS))
            self.assertIsInstance(ncm.get_ncm_instance(), ncm.NcmClientv2v3)

    def test_set_keys(self):
        with clean_env():
            ncm.set_keys(v2_keys=dict(V2_KEYS), v3_key=V3_TOKEN)
            self.assertIsInstance(ncm.get_ncm_instance(), ncm.NcmClientv2v3)

    def test_caller_dict_not_mutated(self):
        keys = {**V2_KEYS}
        with clean_env():
            ncm.set_v2_keys(keys)
        self.assertEqual(keys, V2_KEYS)


if __name__ == '__main__':
    unittest.main()
