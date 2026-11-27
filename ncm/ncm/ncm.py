"""
Combined v2/v3 client, the module-level singleton, and module-level
method delegation (``ncm.get_routers()``). Kept as the ``ncm.ncm``
submodule so ``from ncm import ncm`` and ``from ncm.ncm import NcmClient``
keep working.
"""

from requests import Session
from requests.adapters import HTTPAdapter
import requests
from http import HTTPStatus
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
import sys
import os
import json
import time
import uuid
import re
from typing import Union, Optional, Dict, Any, Tuple

from ._base import (BaseNcmClient, ConfigSafeSession, strip_masked_secrets,
                    V3_MEDIA_TYPE, V3_ATOMIC_MEDIA_TYPE, V3_RETRY_ON)
from ._v2 import NcmClientv2
from ._v3 import NcmClientv3


class NcmClientv2v3:
    """
    Unified NCM client that provides access to both v2 and v3 APIs.
    Uses composition instead of inheritance for better maintainability.
    """

    def __init__(self, 
              api_keys=None,
              api_key=None,
              log_events=True,
              logger=None,
              retries=5,
              retry_backoff_factor=2,
              retry_on=None,
              base_url=None,
              base_url_v3=None):
        """
        :param api_keys: Dictionary of API credentials (apiv2).
            Optional, but must be set before calling functions.
        :type api_keys: dict
        :param api_key: API key for apiv3.
            Optional, but must be set before calling functions.
        :type api_key: str
        """
        api_keys = api_keys or {}
        apiv3_key = api_keys.pop('token', None) or api_key
        
        # Initialize clients using composition
        self._v2_client = None
        self._v3_client = None
        
        if api_keys:
            self._v2_client = NcmClientv2(api_keys=api_keys, 
                                        log_events=log_events,
                                        logger=logger,
                                        retries=retries, 
                                        retry_backoff_factor=retry_backoff_factor, 
                                        retry_on=retry_on, 
                                        base_url=base_url)
        
        if apiv3_key:
            base_url = base_url_v3 if api_keys else base_url
            self._v3_client = NcmClientv3(api_key=apiv3_key, 
                                        log_events=log_events, 
                                        logger=logger,
                                        retries=retries, 
                                        retry_backoff_factor=retry_backoff_factor, 
                                        retry_on=retry_on, 
                                        base_url=base_url)
        
        # For backwards compatibility
        self.v2 = self._v2_client
        self.v3 = self._v3_client
        
    def __getattr__(self, name: str) -> Any:
        """
        Delegate method calls to the appropriate client.
        Prioritizes v2 for router-related methods (since router IDs are v2-specific),
        otherwise prioritizes v3 over v2 for method resolution.
        
        :param name: Name of the attribute to get
        :type name: str
        :return: The requested attribute
        :raises AttributeError: If the attribute doesn't exist in either client
        """
        # Router-related methods should use v2 since router IDs are v2-specific
        router_methods = [
            'get_router_appdata', 'get_router_appdata_value',
            'get_router_by_id', 'get_router_by_name', 'get_routers',
            'get_router_alerts', 'get_router_logs', 'get_router_state_samples',
            'get_router_stream_usage_samples', 'get_routers_for_account',
            'get_routers_for_group', 'rename_router_by_id', 'rename_router_by_name',
            'assign_router_to_group', 'remove_router_from_group', 'assign_router_to_account',
            'delete_router_by_id', 'delete_router_by_name', 'reboot_device',
            'set_lan_ip_address', 'set_custom1', 'set_custom2', 'set_admin_password',
            'set_router_name', 'set_router_description', 'set_router_asset_id',
            'set_ethernet_wan_ip', 'add_custom_apn', 'set_ncm_api_keys_by_router',
            'set_router_fields', 'copy_router_configuration', 'resume_updates_for_router',
            'get_net_devices_for_router', 'get_net_devices_for_router_by_mode',
            'get_historical_locations', 'get_historical_locations_for_date',
            'create_location', 'delete_location_for_router', 'create_speed_test_mdm'
        ]
        
        # For router-related methods, try v2 first
        if name in router_methods:
            if self._v2_client and hasattr(self._v2_client, name):
                return getattr(self._v2_client, name)
            if self._v3_client and hasattr(self._v3_client, name):
                return getattr(self._v3_client, name)
        else:
            # For other methods, try v3 first, then v2
            if self._v3_client and hasattr(self._v3_client, name):
                return getattr(self._v3_client, name)
            if self._v2_client and hasattr(self._v2_client, name):
                return getattr(self._v2_client, name)
        
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __dir__(self) -> list:
        """
        Return a list of available attributes and methods.
        Combines methods from both v2 and v3 clients.
        
        :return: List of available attribute names
        :rtype: list
        """
        attrs = set(super().__dir__())
        if self._v2_client:
            attrs.update(dir(self._v2_client))
        if self._v3_client:
            attrs.update(dir(self._v3_client))
        return sorted(attrs)
    
    def get_available_methods(self) -> list:
        """
        Get a list of all available methods from both clients.
        Useful for introspection and debugging.
        
        :return: List of available method names
        :rtype: list
        """
        methods = set()
        if self._v2_client:
            v2_methods = [method for method in dir(self._v2_client) 
                         if not method.startswith('_') and callable(getattr(self._v2_client, method))]
            methods.update(v2_methods)
        if self._v3_client:
            v3_methods = [method for method in dir(self._v3_client) 
                         if not method.startswith('_') and callable(getattr(self._v3_client, method))]
            methods.update(v3_methods)
        return sorted(methods)
    
    def has_v2_client(self) -> bool:
        """
        Check if v2 client is available.
        
        :return: True if v2 client is available
        :rtype: bool
        """
        return self._v2_client is not None
    
    def has_v3_client(self) -> bool:
        """
        Check if v3 client is available.
        
        :return: True if v3 client is available
        :rtype: bool
        """
        return self._v3_client is not None


class NcmClient:
    """
    This NCM Client class provides functions for interacting with =
    the Cradlepoint NCM API. Full documentation of the Cradlepoint API can be
    found at: https://developer.cradlepoint.com
    """

    def __new__(cls, api_keys=None, api_key=None, **kwargs):
        api_keys = {**(api_keys or {})}
        apiv3_key = api_keys.pop('token', None) or api_key
        v2 = bool(api_keys)
        v3 = bool(apiv3_key)
        if v2 and v3:
            return NcmClientv2v3(api_keys=api_keys, api_key=apiv3_key, **kwargs)
        if v2 or not (v2 or v3):
            return NcmClientv2(api_keys=api_keys, **kwargs)
        else:
            return NcmClientv3(api_key=apiv3_key, **kwargs)


# Singleton instance for easy module-level access
_ncm_instance = None


def _load_api_keys_from_env() -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """
    Load API keys from environment variables if available.
    
    :return: Tuple of (v2_api_keys_dict, v3_api_key_string)
    :rtype: tuple
    """
    # Load v2 API keys from environment
    v2_keys = {}
    env_v2_keys = {
        'X-CP-API-ID': os.environ.get('X_CP_API_ID'),
        'X-CP-API-KEY': os.environ.get('X_CP_API_KEY'),
        'X-ECM-API-ID': os.environ.get('X_ECM_API_ID'),
        'X-ECM-API-KEY': os.environ.get('X_ECM_API_KEY')
    }
    
    # Only include keys that are actually set
    for key, value in env_v2_keys.items():
        if value:
            v2_keys[key] = value
    
    # Load v3 API key from environment
    v3_key = os.environ.get('NCM_API_TOKEN') or os.environ.get('TOKEN')
    
    # Return None for empty dictionaries/keys
    v2_result = v2_keys if v2_keys else None
    v3_result = v3_key if v3_key else None
    
    return v2_result, v3_result


def get_ncm_instance() -> Union['NcmClientv2', 'NcmClientv3', 'NcmClientv2v3']:
    """
    Get the singleton NCM instance.
    Automatically initializes from environment variables if no instance exists.
    
    Environment variables:
        - X_CP_API_ID: CP API ID for v2 API
        - X_CP_API_KEY: CP API Key for v2 API  
        - X_ECM_API_ID: ECM API ID for v2 API
        - X_ECM_API_KEY: ECM API Key for v2 API
        - NCM_API_TOKEN or TOKEN: Bearer token for v3 API
    
    :param api_keys: Dictionary of API credentials (apiv2). Optional.
    :type api_keys: dict
    :param api_key: API key for apiv3. Optional.
    :type api_key: str
    :param kwargs: Additional arguments passed to NcmClient
    :return: NCM client instance
    :rtype: NcmClientv2, NcmClientv3, or NcmClientv2v3
    """
    global _ncm_instance
    if _ncm_instance is None:
        # Try to auto-initialize from environment variables
        env_v2_keys, env_v3_key = _load_api_keys_from_env()
        if env_v2_keys or env_v3_key:
            _ncm_instance = NcmClient(api_keys=env_v2_keys, api_key=env_v3_key, log_events=False)
        else:
            raise RuntimeError("No NCM instance has been created yet. Call ncm.set_api_keys() first or set environment variables (X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY, NCM_API_TOKEN).")
    return _ncm_instance


def set_api_keys(api_keys: Optional[Dict[str, str]] = None, 
                api_key: Optional[str] = None, 
                **kwargs: Any) -> Union['NcmClientv2', 'NcmClientv3', 'NcmClientv2v3']:
    """
    Set API keys for the singleton NCM instance.
    This is a convenience function that creates or updates the singleton instance.
    This function is backward compatible and doesn't interfere with existing 
    instance.set_api_keys() methods.
    Automatically loads API keys from environment variables if not provided.
    
    Environment variables:
        - X_CP_API_ID: CP API ID for v2 API
        - X_CP_API_KEY: CP API Key for v2 API  
        - X_ECM_API_ID: ECM API ID for v2 API
        - X_ECM_API_KEY: ECM API Key for v2 API
        - NCM_API_TOKEN or TOKEN: Bearer token for v3 API
    
    :param api_keys: Dictionary of API credentials (apiv2). Optional.
    :type api_keys: dict
    :param api_key: API key for apiv3. Optional.
    :type api_key: str
    :param kwargs: Additional arguments passed to NcmClient
    :return: NCM client instance
    :rtype: NcmClientv2, NcmClientv3, or NcmClientv2v3
    """
    global _ncm_instance
    
    # Load from environment if not provided
    if not api_keys and not api_key:
        env_v2_keys, env_v3_key = _load_api_keys_from_env()
        api_keys = env_v2_keys
        api_key = env_v3_key
    
    # Create a new instance with the provided keys
    # This uses the existing NcmClient logic which handles key validation
    _ncm_instance = NcmClient(api_keys=api_keys, api_key=api_key, **kwargs)
    return _ncm_instance


def set_ncm_instance(instance: Union['NcmClientv2', 'NcmClientv3', 'NcmClientv2v3']) -> None:
    """
    Set the singleton NCM instance (useful for testing or custom configuration).
    
    :param instance: NCM client instance to use as singleton
    :type instance: NcmClientv2, NcmClientv3, or NcmClientv2v3
    """
    global _ncm_instance
    _ncm_instance = instance


def reset_ncm_instance() -> None:
    """
    Reset the singleton NCM instance to None.
    """
    global _ncm_instance
    _ncm_instance = None


# Module-level function factory for direct method access
def _create_module_method(method_name: str) -> Any:
    """
    Create a module-level function that delegates to the singleton instance.
    
    :param method_name: Name of the method to create module-level access for
    :type method_name: str
    :return: Function that delegates to the singleton instance method
    :rtype: function
    """
    def module_method(*args: Any, **kwargs: Any) -> Any:
        instance = get_ncm_instance()
        if not hasattr(instance, method_name):
            raise AttributeError(f"NCM client has no method '{method_name}'")
        return getattr(instance, method_name)(*args, **kwargs)
    
    module_method.__name__ = method_name
    module_method.__doc__ = f"Module-level access to {method_name} method"
    return module_method


# Module-level method delegation functions
def _delegate_to_instance(method_name: str, *args: Any, **kwargs: Any) -> Any:
    """
    Delegate method calls to the singleton instance.
    
    :param method_name: Name of the method to call
    :type method_name: str
    :param args: Positional arguments for the method
    :param kwargs: Keyword arguments for the method
    :return: Result of the method call
    :raises AttributeError: If the method doesn't exist on the instance
    """
    instance = get_ncm_instance()
    if not hasattr(instance, method_name):
        # Provide a more helpful error message
        if method_name == 'get_exchange_resources':
            raise AttributeError(f"NCM client has no method '{method_name}'. This method requires a v3 API client. Please ensure you have a v3 API token configured.")
        else:
            raise AttributeError(f"NCM client has no method '{method_name}'")
    return getattr(instance, method_name)(*args, **kwargs)


def _setup_all_module_methods():
    """
    Automatically create module-level functions for all methods in NCM client classes.
    This makes all methods available as module-level functions (e.g., ncm.get_routers()).
    """
    # Collect all public methods from the client classes
    all_methods = set()
    
    # Get methods from NcmClientv2
    for name in dir(NcmClientv2):
        if not name.startswith('_') and callable(getattr(NcmClientv2, name)):
            all_methods.add(name)
    
    # Get methods from NcmClientv3
    for name in dir(NcmClientv3):
        if not name.startswith('_') and callable(getattr(NcmClientv3, name)):
            all_methods.add(name)
    
    # Get methods from NcmClientv2v3
    for name in dir(NcmClientv2v3):
        if not name.startswith('_') and callable(getattr(NcmClientv2v3, name)):
            all_methods.add(name)
    
    # Exclude methods that are already defined or are special methods
    excluded = {
        'set_api_keys', 'get_ncm_instance', 'set_ncm_instance', 'reset_ncm_instance',
        '__class__', '__dict__', '__doc__', '__module__', '__weakref__'
    }
    
    # Create module-level functions for each method
    for method_name in all_methods:
        if method_name in excluded or method_name in globals():
            continue
        
        # Create a wrapper function that delegates to the instance
        # Use default parameter to capture method_name in closure
        def make_wrapper(name=method_name):
            def wrapper(*args, **kwargs):
                return _delegate_to_instance(name, *args, **kwargs)
            wrapper.__name__ = name
            wrapper.__doc__ = f"Module-level access to {name} method"
            return wrapper
        
        # Set the function in the module's globals
        globals()[method_name] = make_wrapper()


# Automatically set up all module-level methods
_setup_all_module_methods()


# ---------------------------------------------------------------------------
# ncm2 additions: explicit version access and key helpers.
# These all resolve through the same singleton as ncm.get_routers() etc., so
# they always use the same keys.
# ---------------------------------------------------------------------------

# Short class names (aliases; the original names remain canonical)
NcmV2 = NcmClientv2
NcmV3 = NcmClientv3
BaseClient = BaseNcmClient

_V2_HEADER_NAMES = ('X-CP-API-ID', 'X-CP-API-KEY', 'X-ECM-API-ID', 'X-ECM-API-KEY')


class _VersionProxy:
    """
    ``ncm.v2`` / ``ncm.v3``: explicit access to one API version of the
    singleton client, e.g. ``ncm.v2.get_routers()`` or
    ``ncm.v3.get_subscriptions()``.
    """

    def __init__(self, version):
        self._version = version

    def _client(self):
        client = getattr(get_ncm_instance(), self._version, None)
        if client is None:
            need = ('v2 API keys (X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, '
                    'X_ECM_API_KEY)' if self._version == 'v2'
                    else 'a v3 token (NCM_API_TOKEN)')
            raise RuntimeError(
                f"No {self._version} client is configured. Set {need}, then "
                f"call ncm.set_api_keys().")
        return client

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return getattr(self._client(), name)

    def __dir__(self):
        return dir(self._client())

    def __repr__(self):
        return f'<ncm.{self._version} proxy>'


v2 = _VersionProxy('v2')
v3 = _VersionProxy('v3')


def _current_keys():
    """(v2_keys, v3_token) held by the singleton, else from the environment."""
    inst = _ncm_instance
    if inst is None:
        return _load_api_keys_from_env()
    v2_client = getattr(inst, 'v2', None)
    v3_client = getattr(inst, 'v3', None)
    v2_keys = None
    if v2_client is not None:
        v2_keys = {k: v2_client.session.headers[k] for k in _V2_HEADER_NAMES
                   if k in v2_client.session.headers} or None
    token = None
    if v3_client is not None:
        auth = v3_client.session.headers.get('Authorization', '')
        token = auth[len('Bearer '):] if auth.startswith('Bearer ') else None
    return v2_keys, token


def set_v2_keys(api_keys: Dict[str, str], **kwargs: Any):
    """Set v2 API keys on the singleton, keeping any v3 token already in use."""
    _, token = _current_keys()
    return set_api_keys(api_keys=dict(api_keys), api_key=token, **kwargs)


def set_v3_key(api_key: str, **kwargs: Any):
    """Set the v3 Bearer token on the singleton, keeping any v2 keys in use."""
    v2_keys, _ = _current_keys()
    return set_api_keys(api_keys=v2_keys, api_key=api_key, **kwargs)


def set_keys(v2_keys: Optional[Dict[str, str]] = None,
             v3_key: Optional[str] = None, **kwargs: Any):
    """Set v2 keys and/or the v3 token on the singleton in one call."""
    current_v2, current_v3 = _current_keys()
    return set_api_keys(api_keys=dict(v2_keys) if v2_keys else current_v2,
                        api_key=v3_key or current_v3, **kwargs)


# Backward compatibility: Create a submodule-like structure
class _NcmModule:
    """
    Backward compatibility class that provides the old import structure.
    Allows scripts to use: from ncm import ncm
    """
    
    # Expose all the main classes
    NcmClient = NcmClient
    NcmClientv2 = NcmClientv2
    NcmClientv3 = NcmClientv3
    NcmClientv2v3 = NcmClientv2v3
    BaseNcmClient = BaseNcmClient
    
    # Expose utility functions as static methods to avoid self parameter issues
    @staticmethod
    def get_ncm_instance(api_keys: Optional[Dict[str, str]] = None, 
                        api_key: Optional[str] = None, 
                        **kwargs: Any) -> Union['NcmClientv2', 'NcmClientv3', 'NcmClientv2v3']:
        """Module-level get_ncm_instance function for backward compatibility."""
        return globals()['get_ncm_instance'](api_keys, api_key, **kwargs)
    
    @staticmethod
    def set_ncm_instance(instance: Union['NcmClientv2', 'NcmClientv3', 'NcmClientv2v3']) -> None:
        """Module-level set_ncm_instance function for backward compatibility."""
        return globals()['set_ncm_instance'](instance)
    
    # Expose reset_ncm_instance as a static method to avoid self parameter issues
    @staticmethod
    def reset_ncm_instance() -> None:
        """Module-level reset_ncm_instance function for backward compatibility."""
        return globals()['reset_ncm_instance']()
    
    # Expose set_api_keys as a static method to avoid self parameter issues
    @staticmethod
    def set_api_keys(api_keys: Optional[Dict[str, str]] = None, 
                    api_key: Optional[str] = None, 
                    **kwargs: Any) -> Union['NcmClientv2', 'NcmClientv3', 'NcmClientv2v3']:
        """
        Module-level set_api_keys function for backward compatibility.
        
        :param api_keys: Dictionary of API credentials (apiv2). Optional.
        :type api_keys: dict
        :param api_key: API key for apiv3. Optional.
        :type api_key: str
        :param kwargs: Additional arguments passed to NcmClient
        :return: NCM client instance
        :rtype: NcmClientv2, NcmClientv3, or NcmClientv2v3
        """
        return globals()['set_api_keys'](api_keys, api_key, **kwargs)
    
    # Expose all module-level methods
    def __getattr__(self, name: str) -> Any:
        """
        Delegate to module-level functions.
        
        :param name: Name of the attribute to get
        :type name: str
        :return: The requested attribute
        :raises AttributeError: If the attribute doesn't exist
        """
        if hasattr(sys.modules[__name__], name):
            return getattr(sys.modules[__name__], name)
        raise AttributeError(f"module 'ncm.ncm' has no attribute '{name}'")
    
    def __dir__(self) -> list:
        """
        Return available attributes.
        
        :return: List of available attribute names
        :rtype: list
        """
        return sorted(set(dir(sys.modules[__name__])))


# Create the backward compatibility object
ncm = _NcmModule()
