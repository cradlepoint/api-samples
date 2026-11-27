"""ncm2-only additions: private cellular methods and short-name aliases."""
import unittest

from _support import ncm, clean_env, recording, make_response, V2_KEYS, V3_TOKEN

V3 = 'https://api.cradlepointecm.com/api/v3'


def v3_client():
    return ncm.NcmClientv3(api_key=V3_TOKEN)


class PrivateCellular(unittest.TestCase):

    def test_get_methods_hit_beta_paths_without_trailing_slash(self):
        paths = {
            'get_private_cellular_networks': 'private_cellular_networks',
            'get_private_cellular_cores': 'private_cellular_cores',
            'get_private_cellular_radios': 'private_cellular_radios',
            'get_private_cellular_radio_groups': 'private_cellular_radio_groups',
            'get_private_cellular_sims': 'private_cellular_sims',
        }
        with clean_env():
            for method, path in paths.items():
                with self.subTest(method=method), recording() as rec:
                    getattr(v3_client(), method)(id='n', limit=5)
                    url = rec.calls[0]['url']
                    self.assertTrue(url.startswith(f'{V3}/beta/{path}?'), url)
                    self.assertIn('filter%5Bid%5D=n', url)
                    self.assertIn('page%5Bsize%5D=5', url)

    def test_invalid_filter_rejected_before_request(self):
        with clean_env(), recording() as rec:
            with self.assertRaises(ValueError):
                v3_client().get_private_cellular_networks(bogus=1)
        self.assertEqual(rec.calls, [])

    def test_missing_token_rejected_before_request(self):
        with clean_env(), recording() as rec:
            with self.assertRaises(KeyError):
                ncm.NcmClientv3().get_private_cellular_sims()
        self.assertEqual(rec.calls, [])

    def test_create_network_body(self):
        with clean_env(), recording(lambda m, u, k: make_response(201, {"data": {"id": "p1"}})) as rec:
            result = v3_client().create_private_cellular_network(
                'net', '10.0.0.1', mobility_gateways='c1,c2')
        call = rec.calls[0]
        self.assertEqual((call['method'], call['url']),
                         ('POST', f'{V3}/beta/private_cellular_networks'))
        self.assertEqual(call['body']['data']['relationships']['mobility_gateways']['data'],
                         [{"type": "private_cellular_cores", "id": "c1"},
                          {"type": "private_cellular_cores", "id": "c2"}])
        self.assertEqual(result, {"data": {"id": "p1"}})

    def test_delete_handles_empty_204(self):
        with clean_env(), recording(lambda m, u, k: make_response(204)) as rec:
            v3_client().delete_private_cellular_network('p1')
        self.assertEqual(rec.calls[0]['url'], f'{V3}/beta/private_cellular_networks/p1')

    def test_delete_requires_id(self):
        with clean_env(), self.assertRaises(ValueError):
            v3_client().delete_private_cellular_network(' ')

    def test_module_level_access(self):
        ncm.reset_ncm_instance()
        try:
            with clean_env(), recording() as rec:
                ncm.set_api_keys({**V2_KEYS, 'token': V3_TOKEN})
                ncm.get_private_cellular_networks(limit=1)
                ncm.v3.get_private_cellular_sims(limit=1)
            self.assertIn('/beta/private_cellular_networks', rec.calls[0]['url'])
            self.assertIn('/beta/private_cellular_sims', rec.calls[1]['url'])
        finally:
            ncm.reset_ncm_instance()


class ExchangeHelper(unittest.TestCase):

    def test_delete_exchange_resources_for_site_delegates(self):
        with clean_env():
            client = v3_client()
            seen = {}
            client.delete_exchange_resource = lambda **kw: seen.update(kw) or ['ok']
            self.assertEqual(client.delete_exchange_resources_for_site('s1'), ['ok'])
        self.assertEqual(seen, {'site_id': 's1'})


if __name__ == '__main__':
    unittest.main()
