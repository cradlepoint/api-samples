"""
Shared test helpers: import paths, the reference (original) ncm module, a
recording fake HTTP layer, and argument synthesis for calling every method.
"""
import importlib.util
import inspect
import json
import os
import re
import sys
from contextlib import contextmanager
from unittest import mock

import requests

NCM2_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(NCM2_DIR)

# The parity reference is the last single-file SDK, ncm 0.0.74, read straight
# from git history (no copy kept in the repo). Override with NCM_REFERENCE_SRC=
# <path to a single-file ncm.py>. Parity tests skip if neither is available.
REFERENCE_COMMIT = '208f2840ffe712a09842ba954391541e9b782ad0'  # "Bump version: 0.0.73 -> 0.0.74"
REFERENCE_PATH_IN_COMMIT = 'ncm/ncm/ncm.py'

# Make sure "import ncm" resolves to ncm2/ncm, not the PyPI package in the venv.
if sys.path[0] != NCM2_DIR:
    sys.path.insert(0, NCM2_DIR)
for _name in [m for m in sys.modules if m == 'ncm' or m.startswith('ncm.')]:
    if not sys.modules[_name].__file__ or not sys.modules[_name].__file__.startswith(NCM2_DIR):
        del sys.modules[_name]

import ncm  # noqa: E402

assert ncm.__file__.startswith(NCM2_DIR), f'wrong ncm imported: {ncm.__file__}'

V2_KEYS = {'X-CP-API-ID': 'cp-id', 'X-CP-API-KEY': 'cp-key',
           'X-ECM-API-ID': 'ecm-id', 'X-ECM-API-KEY': 'ecm-key'}
V3_TOKEN = 'test-token'
NCM_ENV_VARS = ('X_CP_API_ID', 'X_CP_API_KEY', 'X_ECM_API_ID', 'X_ECM_API_KEY',
                'NCM_API_TOKEN', 'TOKEN', 'CP_API_TOKEN',
                'CP_BASE_URL', 'CP_BASE_URL_V3')

_reference = None


def _reference_source():
    """Path to the 0.0.74 single-file SDK, or None if it can't be found."""
    override = os.environ.get('NCM_REFERENCE_SRC')
    if override:
        return override if os.path.exists(override) else None
    import subprocess
    import tempfile
    try:
        src = subprocess.run(
            ['git', 'show', f'{REFERENCE_COMMIT}:{REFERENCE_PATH_IN_COMMIT}'],
            cwd=REPO_DIR, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    path = os.path.join(tempfile.gettempdir(), f'ncm_reference_{REFERENCE_COMMIT[:12]}.py')
    with open(path, 'wb') as fh:
        fh.write(src)
    return path


def reference_module():
    """The original single-file ncm 0.0.74, loaded as 'ncm_ref'."""
    global _reference
    if _reference is None:
        source = _reference_source()
        if source is None:
            return None
        spec = importlib.util.spec_from_file_location('ncm_ref', source)
        mod = importlib.util.module_from_spec(spec)
        sys.modules['ncm_ref'] = mod
        spec.loader.exec_module(mod)
        _reference = mod
    return _reference


def clean_env():
    """Patch os.environ so no NCM credentials leak into a test."""
    env = {k: v for k, v in os.environ.items() if k not in NCM_ENV_VARS}
    return mock.patch.dict(os.environ, env, clear=True)


# --- Canned data -----------------------------------------------------------

def config_with_secrets():
    """A device config diff containing NCM's masked "*" secrets."""
    return [
        {
            "system": {"users": {"0": {"password": "*", "username": "admin"}},
                       "ntp": {"servers": {"0": {"key": "*", "server": "time.example"}}}},
            "wlan": {"radio": {"0": {"bss": {"0": {"ssid": "net", "wpapsk": "*"}}}}},
            "certmgmt": {"certs": {"0": {"name": "c", "key": "*", "x509": "*"}}},
            "wan": {"rules2": {"0": {"_id_": "00000000-a81d-3590-93ca-8b1fcfeb8e14",
                                     "priority": 1}}},
        },
        [["lan", "00000001-0d93-319d-8220-4a1fb0372b51"]],
    ]


def canned_item():
    return {
        "id": "1", "name": "item", "email": "user@example.com",
        "resource_url": "https://www.cradlepointecm.com/api/v2/things/1/",
        "product": "https://www.cradlepointecm.com/api/v2/products/1/",
        "router": "https://www.cradlepointecm.com/api/v2/routers/1/",
        "account": "https://www.cradlepointecm.com/api/v2/accounts/1/",
        "group": None, "mode": "wan", "state": "online", "status": "complete",
        "configuration": config_with_secrets(),
        "type": "items", "value": "v",
        "attributes": {"name": "item", "email": "user@example.com", "status": "complete",
                       "role": "admin", "mac_address": "003044123456"},
        "relationships": {"tenants": {"data": {"id": "t1", "type": "tenants"}},
                          "tenant": {"data": {"id": "t1", "type": "tenants"}}},
        "links": {"self": "https://api.cradlepointecm.com/api/v3/items/1"},
    }


def canned_body():
    return {"data": [canned_item()],
            "meta": {"next": None, "limit": 500, "offset": 0, "total_count": 1},
            "links": {"next": None}}


def make_response(status=200, body=None, url='https://example.invalid/'):
    resp = requests.Response()
    resp.status_code = status
    resp._content = b'' if body is None else json.dumps(body).encode()
    resp.headers['Content-Type'] = 'application/json'
    resp.encoding = 'utf-8'
    resp.url = url
    return resp


# --- Recording HTTP layer --------------------------------------------------

class CallBudgetExceeded(RuntimeError):
    pass


class Recorder:
    """
    Replaces ``requests.Session.request`` (below ConfigSafeSession's filter,
    so it sees exactly what would go on the wire) and records every call.
    """

    def __init__(self, responder=None, budget=60):
        self.calls = []
        self.responder = responder or (lambda method, url, kw: make_response(200, canned_body(), url))
        self.budget = budget

    def __call__(self, session, method, url, *args, **kwargs):
        if len(self.calls) >= self.budget:
            raise CallBudgetExceeded('call budget exceeded')
        self.calls.append(normalize_call(method, url, kwargs))
        return self.responder(str(method).upper(), url, kwargs)


def normalize_call(method, url, kwargs):
    body = kwargs.get('json')
    data = kwargs.get('data')
    if body is None and data is not None:
        if isinstance(data, (bytes, bytearray)):
            data = data.decode()
        try:
            body = json.loads(data) if isinstance(data, str) else data
        except ValueError:
            body = data
    headers = kwargs.get('headers') or {}
    return {
        'method': str(method).upper(),
        'url': str(url),
        'params': kwargs.get('params'),
        'body': body,
        'headers': {k: headers[k] for k in sorted(headers)},
    }


@contextmanager
def recording(responder=None, budget=60):
    """
    Record HTTP calls. Also makes ``time.sleep`` instant and ``uuid.uuid4``
    deterministic (restarting each time), so two runs of the same method
    produce identical requests.
    """
    import uuid as _uuid
    rec = Recorder(responder, budget)
    counter = iter(range(1, 1_000_000))

    def fake_request(self, method, url, *args, **kwargs):
        return rec(self, method, url, *args, **kwargs)

    with mock.patch.object(requests.Session, 'request', fake_request), \
            mock.patch('time.sleep', lambda *_a, **_k: None), \
            mock.patch('uuid.uuid4', lambda: _uuid.UUID(int=next(counter))):
        yield rec


# --- Argument synthesis ----------------------------------------------------

def sample_value(name, param):
    n = name.lower()
    ann = param.annotation
    if n in ('config_json', 'config_man_json', 'configman_json', 'config'):
        return {"configuration": config_with_secrets()}
    if 'mac' in n:
        return '00:30:44:12:34:56'
    if n in ('net_device_ids',):
        return [1]
    if 'email' in n:
        return 'user@example.com'
    if n == 'date':
        return '2026-01-01'
    if n in ('latitude', 'longitude'):
        return 1.0
    if n in ('enabled', 'ha_enabled'):
        return False
    if ann is dict or 'payload' in n or 'attributes' in n or 'relationships' in n \
            or n.endswith('authorization'):
        return {}
    if ann is bool:
        return False
    if ann is int or n.endswith('_id') or n == 'id':
        return 1
    return 'x'


def call_args(func):
    """Positional args for every required parameter of ``func``."""
    args = []
    for name, param in inspect.signature(func).parameters.items():
        if name == 'self' or param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if param.default is param.empty:
            args.append(sample_value(name, param))
    return args


_ADDR = re.compile(r' at 0x[0-9a-f]+')
_MODS = re.compile(r'\b(ncm_ref|ncm\._v2|ncm\._v3|ncm\._base|ncm\.ncm)\.')


def scrub(text):
    """Remove memory addresses and module names so reprs compare equal."""
    return _MODS.sub('', _ADDR.sub('', text))


def outcome(func, *args):
    """Result or raised exception of func(*args), as a comparable string."""
    try:
        result = func(*args)
    except CallBudgetExceeded:
        return 'CALL_BUDGET'
    except Exception as exc:  # noqa: BLE001 - compared, not swallowed
        return f'raise {type(exc).__name__}: {scrub(str(exc))}'
    return 'return ' + scrub(repr(result))


def public_methods(cls):
    return sorted(n for n, _ in inspect.getmembers(cls, callable)
                  if not n.startswith('_'))
