"""
Live, READ-ONLY smoke test against the real NCM API. Skipped unless
NCM_LIVE_TESTS=1. Calls the same GET methods on the original library and on
ncm2 and checks they return identical data. Nothing is written.

    NCM_LIVE_TESTS=1 python3 -m unittest test_live            # from ncm2/tests
    NCM_LIVE_ROUTER=<router id>                                # optional

Credentials come from the environment or the repo's .env (loaded through
scripts/utils/env_check.py). v3 checks are skipped without NCM_API_TOKEN.
"""
import os
import sys
import unittest

from _support import ncm, reference_module, REPO_DIR

LIVE = os.environ.get('NCM_LIVE_TESTS') == '1'

if LIVE:
    sys.path.insert(0, os.path.join(REPO_DIR, 'scripts'))
    import utils.env_check  # noqa: F401,E402  (loads .env into os.environ)

REF = reference_module() if LIVE else None


def v2_keys():
    return {'X-CP-API-ID': os.environ.get('X_CP_API_ID'),
            'X-CP-API-KEY': os.environ.get('X_CP_API_KEY'),
            'X-ECM-API-ID': os.environ.get('X_ECM_API_ID'),
            'X-ECM-API-KEY': os.environ.get('X_ECM_API_KEY')}


@unittest.skipUnless(LIVE, 'set NCM_LIVE_TESTS=1 to run live read-only checks')
class LiveV2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.old = REF.NcmClientv2(api_keys=v2_keys(), log_events=False)
        cls.new = ncm.NcmClientv2(api_keys=v2_keys(), log_events=False)
        cls.router_id = os.environ.get('NCM_LIVE_ROUTER') or \
            cls.new.get_routers(limit=1, fields='id')[0]['id']

    def same(self, method, *args, **kwargs):
        old = getattr(self.old, method)(*args, **kwargs)
        new = getattr(self.new, method)(*args, **kwargs)
        self.assertEqual(new, old, f'{method} differs between libraries')
        return new

    def test_accounts(self):
        self.assertTrue(self.same('get_accounts', limit=2))

    def test_router_by_id(self):
        router = self.same('get_router_by_id', self.router_id, fields='id,name,state')
        self.assertEqual(str(router['id']), str(self.router_id))

    def test_configuration_manager(self):
        recs = self.same('get_configuration_managers', router=self.router_id,
                         fields='id,router,configuration')
        self.assertEqual(len(recs), 1)
        self.assertEqual(self.same('get_configuration_manager_id', self.router_id), recs[0]['id'])

    def test_net_devices(self):
        self.same('get_net_devices_for_router', self.router_id, fields='id,mode,name')

    def test_groups_and_products(self):
        self.same('get_groups', limit=3, fields='id,name')
        self.same('get_products', limit=3)

    def test_paginated_in_filter(self):
        ids = [r['id'] for r in self.new.get_routers(limit=3, fields='id')]
        self.same('get_routers', id__in=','.join(map(str, ids)), fields='id,name')


@unittest.skipUnless(LIVE and os.environ.get('NCM_API_TOKEN'),
                     'set NCM_LIVE_TESTS=1 and NCM_API_TOKEN for live v3 checks')
class LiveV3(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = os.environ['NCM_API_TOKEN']
        cls.old = REF.NcmClientv3(api_key=token)
        cls.new = ncm.NcmClientv3(api_key=token)

    def same(self, method, *args, **kwargs):
        old = getattr(self.old, method)(*args, **kwargs)
        new = getattr(self.new, method)(*args, **kwargs)
        self.assertEqual(new, old, f'{method} differs between libraries')
        return new

    def test_subscriptions(self):
        self.same('get_subscriptions', limit=2)

    def test_users(self):
        self.same('get_users', limit=2)

    def test_asset_endpoints(self):
        self.same('get_asset_endpoints', limit=2)

    def test_exchange_sites(self):
        self.same('get_exchange_sites', limit=2)

    def test_private_cellular_networks_ncm2_only(self):
        # Not in the original library. Accounts without private cellular get
        # an HTML "Server Error (500)" from the beta route (observed
        # 2026-11-26), which the shared v3 error path can't parse as JSON.
        probe = self.new.session.get(f'{self.new.base_url}/beta/private_cellular_networks',
                                     params={'page[size]': 1})
        if probe.status_code >= 500:
            self.skipTest(f'account has no private cellular service (HTTP {probe.status_code})')
        self.assertNotEqual(probe.status_code, 404, 'route not found')
        result = self.new.get_private_cellular_networks(limit=2)
        self.assertIsInstance(result, list)


@unittest.skipUnless(LIVE, 'set NCM_LIVE_TESTS=1 to run live read-only checks')
class LiveModuleLevel(unittest.TestCase):

    def test_zero_config_import(self):
        ncm.reset_ncm_instance()
        try:
            routers = ncm.get_routers(limit=1, fields='id')
            self.assertEqual(len(routers), 1)
            self.assertEqual(ncm.v2.get_routers(limit=1, fields='id'), routers)
        finally:
            ncm.reset_ncm_instance()


if __name__ == '__main__':
    unittest.main()
