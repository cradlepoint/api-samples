"""
Masked-secret filter and copy_router_configuration.

NCM returns every secret as "*" on GET. Config writes must leave those keys
out entirely so the target keeps (or defaults) its secret instead of being
set to a literal "*".
"""
import json
import unittest

import requests

from _support import (ncm, clean_env, recording, make_response, canned_body,
                      config_with_secrets, V2_KEYS)
from ncm._base import strip_masked_secrets, ConfigSafeSession

BASE = 'https://www.cradlepointecm.com/api/v2'

EXPECTED_STRIPPED = [
    {
        "system": {"users": {"0": {"username": "admin"}},
                   "ntp": {"servers": {"0": {"server": "time.example"}}}},
        "wlan": {"radio": {"0": {"bss": {"0": {"ssid": "net"}}}}},
        "certmgmt": {"certs": {"0": {"name": "c"}}},
        "wan": {"rules2": {"0": {"_id_": "00000000-a81d-3590-93ca-8b1fcfeb8e14",
                                 "priority": 1}}},
    },
    [["lan", "00000001-0d93-319d-8220-4a1fb0372b51"]],
]


class StripMaskedSecrets(unittest.TestCase):

    def test_removes_every_masked_value_at_any_depth(self):
        self.assertEqual(strip_masked_secrets(config_with_secrets()), EXPECTED_STRIPPED)

    def test_does_not_mutate_input(self):
        cfg = config_with_secrets()
        before = json.dumps(cfg, sort_keys=True)
        strip_masked_secrets(cfg)
        self.assertEqual(json.dumps(cfg, sort_keys=True), before)

    def test_keeps_list_elements_and_non_secret_values(self):
        cfg = [{"a": ["*", "x"], "b": "**", "c": "", "d": None, "e": 0}, [["p", 1]]]
        self.assertEqual(strip_masked_secrets(cfg), cfg)

    def test_real_password_is_kept(self):
        cfg = [{"system": {"users": {"0": {"password": "N3w-Secret!"}}}}, []]
        self.assertEqual(strip_masked_secrets(cfg), cfg)


class SessionFilter(unittest.TestCase):
    """The filter sits in the session, so every write path is covered."""

    def _send(self, method, url, **kwargs):
        session = ConfigSafeSession()
        with recording() as rec:
            session.request(method, url, **kwargs)
        return rec.calls[0]['body']

    def test_json_body_to_configuration_managers(self):
        body = self._send('PUT', f'{BASE}/configuration_managers/9/',
                          json={"configuration": config_with_secrets()})
        self.assertEqual(body, {"configuration": EXPECTED_STRIPPED})

    def test_string_body_to_groups(self):
        body = self._send('PATCH', f'{BASE}/groups/9/',
                          data=json.dumps({"configuration": config_with_secrets()}))
        self.assertEqual(body, {"configuration": EXPECTED_STRIPPED})

    def test_only_configuration_key_is_filtered(self):
        body = self._send('PATCH', f'{BASE}/groups/9/',
                          json={"name": "*", "configuration": [{"x": "*"}, []]})
        self.assertEqual(body, {"name": "*", "configuration": [{}, []]})

    def test_other_endpoints_untouched(self):
        payload = {"configuration": [{"x": "*"}, []]}
        self.assertEqual(self._send('PUT', f'{BASE}/routers/9/', json=payload), payload)

    def test_get_untouched(self):
        session = ConfigSafeSession()
        with recording() as rec:
            session.get(f'{BASE}/configuration_managers/9/')
        self.assertEqual(rec.calls[0]['method'], 'GET')

    def test_unchanged_string_body_sent_verbatim(self):
        """No secrets -> the original string goes out byte-for-byte."""
        raw = json.dumps({"configuration": [{"wan": {"x": 1}}, []]}, separators=(',', ':'))
        seen = {}

        def fake(self, method, url, *a, **kw):
            seen['data'] = kw.get('data')
            return make_response(200, {})

        from unittest import mock
        with mock.patch.object(requests.Session, 'request', fake):
            ConfigSafeSession().patch(f'{BASE}/configuration_managers/9/', data=raw)
        self.assertIs(seen['data'], raw)

    def test_patch_configuration_managers_end_to_end(self):
        with clean_env():
            client = ncm.NcmClientv2(api_keys=dict(V2_KEYS), log_events=False)
            with recording() as rec:
                client.patch_configuration_managers(5, {"configuration": config_with_secrets()})
        patch = [c for c in rec.calls if c['method'] == 'PATCH'][0]
        self.assertEqual(patch['body'], {"configuration": EXPECTED_STRIPPED})
        self.assertNotIn('"*"', json.dumps(patch['body']))


def copy_responder(src_config):
    """Source router 111 has ``src_config``; destination 222 has config manager 777."""
    def responder(method, url, kw):
        if method == 'GET' and 'router=111' in url:
            return make_response(200, {"data": [{"configuration": src_config}],
                                       "meta": {"next": None}})
        if method == 'GET' and 'router=222' in url:
            return make_response(200, {"data": [{"id": "777"}], "meta": {"next": None}})
        return make_response(200, {"configuration": src_config})
    return responder


class CopyRouterConfiguration(unittest.TestCase):

    def _copy(self, src_config, client_module=ncm, **kwargs):
        with clean_env():
            client = client_module.NcmClientv2(api_keys=dict(V2_KEYS), log_events=False)
            with recording(copy_responder(src_config)) as rec:
                result = client.copy_router_configuration(111, 222, **kwargs)
        writes = [c for c in rec.calls if c['method'] != 'GET']
        self.assertEqual(len(writes), 1)
        return writes[0], result

    def test_default_merges_with_patch_without_secrets(self):
        write, result = self._copy(config_with_secrets())
        self.assertEqual(write['method'], 'PATCH')
        self.assertEqual(write['url'], f'{BASE}/configuration_managers/777/')
        self.assertEqual(write['body'], {"configuration": EXPECTED_STRIPPED})
        self.assertEqual(result, 'Configuration Manager operation successful.')

    def test_replace_true_uses_put_without_secrets(self):
        write, result = self._copy(config_with_secrets(), replace=True)
        self.assertEqual(write['method'], 'PUT')
        self.assertEqual(write['url'], f'{BASE}/configuration_managers/777/')
        self.assertEqual(write['body'], {"configuration": EXPECTED_STRIPPED})
        self.assertEqual(result, 'Configuration Manager operation successful.')

    def test_replace_false_explicit_is_default(self):
        self.assertEqual(self._copy(config_with_secrets(), replace=False)[0]['method'], 'PATCH')

    def test_default_matches_0_0_74_when_its_body_was_valid(self):
        """Non-breaking: same method, URL and body as before wherever 0.0.74 worked."""
        from _support import reference_module
        ref = reference_module()
        if ref is None:
            self.skipTest('ncm 0.0.74 reference not available')
        # Secrets not first in their objects, and only the two 0.0.74 removed.
        src = [{"system": {"users": {"0": {"_id_": "00000000-a0ab-3e74-bcbd-02af091f1c50",
                                           "password": "*"}}},
                "wlan": {"radio": {"0": {"bss": {"0": {"ssid": "net", "wpapsk": "*"}}}}},
                "wan": {"x": 1}}, [["lan", 0]]]
        old_write, old_result = self._copy(src, client_module=ref)
        new_write, new_result = self._copy(src)
        self.assertEqual(new_write, old_write)
        self.assertEqual(new_result, old_result)

    def test_secret_as_first_key_still_sends_valid_json(self):
        """0.0.74's string replacement produced '{, "username": ...}' here."""
        src = [{"system": {"users": {"0": {"password": "*", "username": "admin"}}}}, []]
        write, _ = self._copy(src)
        self.assertIsInstance(write['body'], dict)   # parsed fine
        self.assertEqual(write['body'],
                         {"configuration": [{"system": {"users": {"0": {"username": "admin"}}}}, []]})

    def test_module_level_passes_replace(self):
        ncm.reset_ncm_instance()
        try:
            with clean_env():
                ncm.set_api_keys(dict(V2_KEYS))
                with recording(copy_responder(config_with_secrets())) as rec:
                    ncm.copy_router_configuration(111, 222, replace=True)
            self.assertEqual([c['method'] for c in rec.calls if c['method'] != 'GET'], ['PUT'])
        finally:
            ncm.reset_ncm_instance()

    def test_missing_destination_raises_like_before(self):
        def responder(method, url, kw):
            if 'router=222' in url:
                return make_response(200, {"data": [], "meta": {"next": None}})
            return make_response(200, canned_body())

        with clean_env():
            client = ncm.NcmClientv2(api_keys=dict(V2_KEYS), log_events=False)
            with recording(responder) as rec:
                with self.assertRaises(IndexError):
                    client.copy_router_configuration(111, 222)
        self.assertFalse([c for c in rec.calls if c['method'] != 'GET'])


if __name__ == '__main__':
    unittest.main()
