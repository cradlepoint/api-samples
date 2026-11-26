"""
NCM - Python client library for the Cradlepoint / Ericsson NetCloud Manager API.

Drop-in replacement for the original single-file ``ncm`` package. Every class,
method, signature and module-level function of ncm 0.0.74 is preserved; the
code is split by API version:

    _base.py  shared HTTP plumbing + masked-secret filter for config writes
    _v2.py    NcmClientv2  (alias NcmV2)
    _v3.py    NcmClientv3  (alias NcmV3)
    ncm.py    NcmClientv2v3, NcmClient factory, singleton, module-level methods

All existing usage keeps working:

    import ncm
    routers = ncm.get_routers()                 # module-level, auto-routed

    from ncm import ncm                         # legacy import
    client = ncm.NcmClient(api_keys={...})

    from ncm.ncm import NcmClientv2             # submodule import

New in this version:

    ncm.v2.get_routers()                        # explicit API version
    ncm.v3.get_subscriptions()
    ncm.set_v2_keys({...}); ncm.set_v3_key('token'); ncm.set_keys(...)

Config writes never send NCM's masked "*" secret placeholders; see
``strip_masked_secrets`` in ``_base.py``.
"""

from .ncm import *  # noqa: F401,F403  (same public surface as ncm 0.0.74)
from ._base import strip_masked_secrets, ConfigSafeSession  # noqa: F401

__version__ = '0.1.0'
