"""NCM API v3 client (JSON:API; subscriptions, users, regrades, ...)."""

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


class NcmClientv3(BaseNcmClient):
    """
    This NCM Client class provides functions for interacting with =
    the Cradlepoint NCM API. Full documentation of the Cradlepoint API can be
    found at: https://developer.cradlepoint.com
    """

    def __init__(self,
                 api_key=None,
                 log_events=False,
                 logger=None,
                 retries=5,
                 retry_backoff_factor=2,
                 retry_on=None,
                 base_url=None):
        """
        Constructor. Sets up and opens request session.
        :param api_key: API Bearer token (without the "Bearer" text).
          Optional, but must be set before calling functions.
        :type api_key: str
        :param log_events: if True, HTTP status info will be printed. False by default
        :type log_events: bool
        :param retries: number of retries on failure. Optional.
        :param retry_backoff_factor: backoff time multiplier for retries.
          Optional.
        :param retry_on: types of errors on which automatic retry will occur.
          Optional.
        :param base_url: # base url for calls. Configurable for testing.
          Optional.
        """
        self.v3 = self # For backwards compatibility
        base_url = base_url or os.environ.get("CP_BASE_URL_V3", "https://api.cradlepointecm.com/api/v3")
        # v3 widens the retryable status set to {408, 429, 502, 503, 504} with
        # total=5 and backoff_factor=2 (the constructor defaults), so rate-limit
        # (429) and bad-gateway (502) responses are retried with exponential
        # backoff. This is applied only to the v3 adapter; the v2 client still
        # passes retry_on=None and inherits the base default set unchanged
        # (Req 15.1, 15.2). An explicit retry_on from the caller is honored.
        if retry_on is None:
            retry_on = list(V3_RETRY_ON)
        super().__init__(log_events, logger, retries, retry_backoff_factor, retry_on, base_url)
        # Remember the backoff/attempt budget so the in-path 409 disambiguation
        # (which the urllib3 adapter cannot express) mirrors the adapter's
        # bounds (Req 15.2, 15.3).
        self._retry_total = retries
        self._retry_backoff_factor = retry_backoff_factor
        if api_key:
            token = {'Authorization': f'Bearer {api_key}'}
            self.session.headers.update(token)
        # Content negotiation for JSON:API on every v3 request (Req 3.2). The
        # Authorization header above carries the Bearer token when supplied
        # (Req 3.1).
        self.session.headers.update({
            'Content-Type': V3_MEDIA_TYPE,
            'Accept': V3_MEDIA_TYPE
        })

    @staticmethod
    def _atomic_headers():
        """
        Per-request header override selecting the JSON:API atomic-operations
        extension media type for both Content-Type and Accept, in place of the
        default ``application/vnd.api+json`` (Req 3.4). Used by regrade-family
        endpoints. Returns a fresh dict on each call so callers cannot mutate
        shared state.
        """
        return {
            'Content-Type': V3_ATOMIC_MEDIA_TYPE,
            'Accept': V3_ATOMIC_MEDIA_TYPE
        }

    @staticmethod
    def _response_has_errors_array(response):
        """
        Returns True if the response body is a JSON:API document carrying an
        ``errors`` array (i.e. a genuine validation error). Any body that is not
        valid JSON, or that lacks a list-valued ``errors`` member, returns
        False. Used to disambiguate the overloaded ``409 Conflict`` status on
        v3 (Req 15.2): a rate-limit 409 has no ``errors`` array, a validation
        409 does.
        """
        try:
            body = response.json()
        except (ValueError, json.JSONDecodeError):
            return False
        return isinstance(body, dict) and isinstance(body.get('errors'), list)

    def _v3_request(self, verb, url, **kwargs):
        """
        Issues a v3 HTTP request and applies the one piece of retry logic the
        urllib3 adapter cannot express: ``409 Conflict`` disambiguation
        (Req 15.2).

        The adapter already retries {408, 429, 502, 503, 504} with exponential
        backoff. ``409`` is overloaded on v3 -- it means either a rate-limit
        ("Conflict with internal rules... invalid app-key.") or a genuine
        JSON:API validation error -- and the two are distinguished only by the
        response body:

        - ``409`` WITHOUT an ``errors`` array -> transient/rate-limit; retry
          manually with the same exponential backoff, bounded by the same
          max-attempts budget as the adapter (``self._retry_total``).
        - ``409`` WITH an ``errors`` array -> non-retryable validation error;
          return immediately so the caller routes it through ``_return_handler``.

        After exhausting the 409 retry budget, the last response is returned so
        the caller hands it to ``_return_handler`` (Req 15.3). All other
        statuses (including adapter-retried transients that have already been
        exhausted) are returned to the caller unchanged; non-forcelist statuses
        go straight to the handler (Req 15.4).

        :param verb: session method name, e.g. ``'get'``, ``'post'``.
        :param url: fully-qualified request URL.
        :return: the final ``requests.Response``.
        """
        session_method = getattr(self.session, verb)
        # total=5 retries means up to 6 attempts; mirror that budget for 409.
        max_attempts = (self._retry_total or 0) + 1
        backoff_factor = self._retry_backoff_factor or 0
        response = None
        for attempt in range(max_attempts):
            response = session_method(url, **kwargs)
            if response.status_code != int(HTTPStatus.CONFLICT):  # not 409
                return response
            if self._response_has_errors_array(response):
                # Genuine JSON:API validation error: non-retryable.
                return response
            # Rate-limit-style 409 with no errors array: retry with backoff,
            # bounded by the same attempt budget as the adapter.
            if attempt >= max_attempts - 1:
                break
            # urllib3 backoff formula: backoff_factor * (2 ** attempt).
            sleep_for = backoff_factor * (2 ** attempt)
            if sleep_for > 0:
                self.log('info',
                         f'HTTP 409 (no errors array) - retrying in '
                         f'{sleep_for}s (attempt {attempt + 1}/{max_attempts})')
                time.sleep(sleep_for)
        return response

    def __get_json(self, get_url, call_type, params=None):
        """
        Returns full paginated results
        """
        results = []

        if params is not None and "limit" in params:
            limit = params['limit']
            if limit == 0:
                limit = 1000000
            if params['limit'] > 50 or params['limit'] == 0:
                params['page[size]'] = 50
            else:
                params['page[size]'] = params['limit']
        else:
            limit = 50

        url = get_url
        if params is not None:
            from urllib.parse import urlencode
            query_string = urlencode(params)
            url = f'{url}?{query_string}'

        while url and (len(results) < limit):
            # Route through _v3_request so the overloaded 409 status is
            # disambiguated (retry on rate-limit 409, surface validation 409)
            # before pagination inspects the result (Req 15.2).
            ncm = self._v3_request('get', url)
            if not (200 <= ncm.status_code < 300):
                # Stop pagination on any non-2xx page and route the failing
                # response through the shared handler, rather than returning the
                # partially accumulated data as a successful result (Req 4.5).
                return self._return_handler(ncm.status_code, ncm.json(), call_type)
            body = ncm.json()
            data = body.get('data', [])
            if isinstance(data, list):
                for d in data:
                    results.append(d)
            else:
                results.append(data)
            # Follow links.next verbatim as returned by the server; stop when it
            # is null or absent (Req 4.1, 4.3, 4.4).
            url = (body.get('links') or {}).get('next')

        # Never return more than an explicit limit's worth of records (Req 4.2).
        if len(results) > limit:
            results = results[:limit]

        if params is not None and "filter[fields]" in params.keys():
            data = []
            fields = params['filter[fields]'].split(",")
            for result in results:
                items = {}
                for k, v in result['attributes'].items():
                    if k in fields:
                        items[k] = v
                data.append(items)
            return data

        return results


    def __parse_kwargs(self, kwargs, allowed_params):
        """
        Checks for invalid parameters and missing API Keys, and handles "filter" fields
        """
        if 'search' in kwargs:
            return self.__parse_search_kwargs(kwargs, allowed_params)

        bad_params = {k: v for (k, v) in kwargs.items() if
                      k not in allowed_params if ("search" not in k and "filter" not in k and "sort" not in k)}
        if len(bad_params) > 0:
            raise ValueError("Invalid parameters: {}".format(bad_params))

        self.__check_token()

        params = {}

        for key, val in kwargs.items():
            if "search" in key or "filter" in key or "sort" in key or "limit" in key:
                params[key] = val

            elif "__" in key:
                split_key = key.split("__", 1)
                params[f'filter[{split_key[0]}][{split_key[1]}]'] = val
            else:
                params[f'filter[{key}]'] = val

        return params

    def __parse_search_kwargs(self, kwargs, allowed_params):
        """
        Checks for invalid parameters and missing API Keys, and handles "search" fields
        """

        bad_params = {k: v for (k, v) in kwargs.items() if
                      k not in allowed_params if ("search" not in k and "filter" not in k and "sort" not in k)}
        if len(bad_params) > 0:
            raise ValueError("Invalid parameters: {}".format(bad_params))

        self.__check_token()

        params = {}

        for key, val in kwargs.items():
            if "filter" in key or "sort" in key or "limit" in key:
                params[key] = val
            elif "fields" in key:
                params[f'filter[{key}]'] = val
            else:
                if "search" not in key:
                    params[f'search[{key}]'] = val

        return params

    def __parse_put_kwargs(self, kwargs, allowed_params):
        """
        Checks for invalid parameters and missing API Keys, and handles "filter" fields
        """

        bad_params = {k: v for (k, v) in kwargs.items() if
                      k not in allowed_params if ("search" not in k and "filter" not in k and "sort" not in k)}
        if len(bad_params) > 0:
            raise ValueError("Invalid parameters: {}".format(bad_params))

        self.__check_token()

        return kwargs

    def __check_token(self):
        """
        Guards against a missing v3 Bearer token before any request is
        dispatched. Raises the same exception type and message as the
        ``__parse_*`` helpers so every v3 method signals a missing credential
        uniformly (Req 2.5, 3.3, 6.5, 7.8, 13.4).
        """
        if 'Authorization' not in self.session.headers:
            raise KeyError(
                "API key missing. "
                "Please set API key before making API calls.")

    def __normalize_mac(self, mac):
        """
        Normalizes a MAC address to bare uppercase hexadecimal by stripping
        the common separators (``:``, ``-``, ``.``) and upper-casing, i.e.
        ``mac.upper().replace(':','').replace('-','').replace('.','')``.

        The normalized value must match ``^[0-9A-Fa-f]{12}`` (exactly 12 hex
        digits). If it does not, a ``ValueError`` is raised identifying the
        offending MAC and nothing is sent (Req 8.3, 8.6).

        :param mac: A MAC address, with or without separators.
        :type mac: str
        :return: The bare uppercase hexadecimal MAC (12 characters).
        :rtype: str
        """
        normalized = str(mac).upper().replace(':', '').replace('-', '').replace('.', '')
        if not re.match(r'^[0-9A-Fa-f]{12}$', normalized):
            raise ValueError(
                "Invalid MAC address: {}. A MAC address must resolve to "
                "exactly 12 hexadecimal characters after separator removal."
                .format(mac))
        return normalized

    def __validate_regrade_batch(self, subscription_id, macs, action):
        """
        Validates a regrade/unlicense batch before any HTTP dispatch and
        returns the list of unique, normalized MAC addresses.

        Enforces (all before sending — Req 8.6, 8.7):
        - a non-empty/non-blank ``subscription_id``,
        - an ``action`` in ``{UPGRADE, DOWNGRADE, UNLICENSE}``,
        - each supplied MAC normalizes to bare uppercase hex (raises via
          ``__normalize_mac`` otherwise),
        - a batch of 1 to 100 MAC addresses (count of provided MACs).

        Duplicate normalized MACs are removed while preserving first-seen
        order, so callers building a payload get one entry per unique MAC.

        :param subscription_id: Subscription/asset identifier.
        :param macs: A single MAC (str) or a list of MACs.
        :param action: One of ``UPGRADE``, ``DOWNGRADE``, ``UNLICENSE``.
        :return: The list of unique normalized MAC addresses.
        :rtype: list
        """
        if subscription_id is None or str(subscription_id).strip() == '':
            raise ValueError(
                "A non-empty subscription identifier is required.")

        allowed_actions = {"UPGRADE", "DOWNGRADE", "UNLICENSE"}
        if action not in allowed_actions:
            raise ValueError(
                "Invalid action: {}. Action must be one of {}."
                .format(action, sorted(allowed_actions)))

        mac_list = [macs] if isinstance(macs, str) else list(macs)

        if not 1 <= len(mac_list) <= 100:
            raise ValueError(
                "Invalid batch size: {} MAC address(es). A regrade batch "
                "must contain between 1 and 100 MAC addresses."
                .format(len(mac_list)))

        # Normalize (raises on invalid) and dedupe preserving order.
        unique_macs = []
        seen = set()
        for mac in mac_list:
            normalized = self.__normalize_mac(mac)
            if normalized not in seen:
                seen.add(normalized)
                unique_macs.append(normalized)

        return unique_macs

    def set_api_key(self, api_key):
        """
        Sets NCM API Keys for session.
        :param api_key: API Bearer token (without the "Bearer" prefix).
        :type api_key: str
        """
        if api_key:
            token = {'Authorization': f'Bearer {api_key}'}
            self.session.headers.update(token)
        return

    def get_users(self, **kwargs):
        """
        Returns users with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of users with details.
        """
        call_type = 'Users'
        # No trailing slash: /api/v3/users/ is a 404 (verified 2026-11-19).
        get_url = f'{self.base_url}/users'

        allowed_params = ['email',
                          'email__not',
                          'first_name',
                          'first_name__ne',
                          'id',
                          'is_active__ne',
                          'last_login',
                          'last_login__lt',
                          'last_login__lte',
                          'last_login__gt',
                          'last_login__gte',
                          'last_login__ne',
                          'last_name',
                          'last_name__ne',
                          'pending_email',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def create_user(self, email, first_name, last_name, **kwargs):
        """
        Creates a user.
        :param email: Email address
        :type email: str
        :param first_name: First name
        :type first_name: str
        :param last_name: Last name
        :type last_name: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: User creation result.
        """
        call_type = 'User'
        self.__check_token()
        post_url = f'{self.base_url}/users'

        allowed_params = ['is_active',
                          'last_login',
                          'pending_email']
        params = self.__parse_kwargs(kwargs, allowed_params)
        params['email'] = email
        params['first_name'] = first_name
        params['last_name'] = last_name

        """GET TENANT ID"""
        t = self.get_subscriptions(limit=1)

        data = {
            "data": {
                "type": "users",
                "attributes": params,
                "relationships": {
                    "tenant": {
                        "data": [t[0]['relationships']['tenants']['data']]
                    }
                }
            }
        }

        ncm = self._v3_request('post', post_url, data=json.dumps(data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def update_user(self, email, **kwargs):
        """
        Updates a user's date.
        :param email: Email address
        :type email: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: User update result.
        """
        call_type = 'Users'
        self.__check_token()

        users = self.get_users(email=email)
        if not users:
            raise ValueError(
                f"User not found: no user matches email '{email}'. "
                "No user was updated.")
        user = users[0]
        user.pop('links', None)

        patch_url = f'{self.base_url}/users/{user["id"]}'

        allowed_params = ['first_name',
                          'last_name',
                          'is_active',
                          'user_id',
                          'last_login',
                          'pending_email']
        params = self.__parse_kwargs(kwargs, allowed_params)

        for k, v in params.items():
            user['attributes'][k] = v

        user = {"data": user}

        ncm = self._v3_request('patch', patch_url, data=json.dumps(user))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def delete_user(self, email, **kwargs):
        """
        Updates a user's date.
        :param email: Email address
        :type email: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: None unless error.
        """
        call_type = 'Users'
        self.__check_token()

        users = self.get_users(email=email)
        if not users:
            raise ValueError(
                f"User not found: no user matches email '{email}'. "
                "No user was deleted.")
        user = users[0]
        user.pop('links', None)

        delete_url = f'{self.base_url}/users/{user["id"]}'

        ncm = self._v3_request('delete', delete_url)
        result = self._return_handler(ncm.status_code, ncm.text, call_type)
        return result

    def get_asset_endpoints(self, **kwargs):
        """
        Returns assets with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of asset endpoints (routers) with details.
        """
        call_type = 'Asset Endpoints'
        get_url = f'{self.base_url}/asset_endpoints/'

        allowed_params = ['id',
                          'hardware_series',
                          'hardware_series_key',
                          'mac_address',
                          'serial_number',
                          'fields',
                          'limit',
                          'sort']

        # Default the result-limit to 500 when the caller supplies none
        # (Req 9.2). __get_json interprets this as a cap and applies a
        # page[size] of 50 per page, so a default of 500 means "up to 500
        # records, 50 per page".
        if 'limit' not in kwargs:
            kwargs['limit'] = 500

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_subscriptions(self, **kwargs):
        """
        Returns subscriptions with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of subscriptions with details.
        """
        call_type = 'Subscriptions'
        get_url = f'{self.base_url}/subscriptions/'

        allowed_params = ['end_time',
                          'end_time__lt',
                          'end_time__lte',
                          'end_time__gt',
                          'end_time__gte',
                          'end_time__ne',
                          'id',
                          'name',
                          'quantity',
                          'start_time',
                          'start_time__lt',
                          'start_time__lte',
                          'start_time__gt',
                          'start_time__gte',
                          'start_time__ne',
                          'tenant',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)
    
    def regrade(self, subscription_id, mac, action="UPGRADE"):
        """ 
        Applies a subscription to an asset.
        :param subscription_id: ID of the subscription to apply. See https://developer.cradlepoint.com/ for list of subscriptions.
        :param mac: MAC address of the asset to apply the subscription to. Can also be a list.
        :param action: Action to take. Default is "UPGRADE". Can also be "DOWNGRADE".
        """

        call_type = 'Subscription'
        self.__check_token()

        # Validate subscription id, action, MAC format, and batch bounds, and
        # dedupe the normalized MACs — all before building or sending anything
        # (Req 8.3, 8.4, 8.6, 8.7).
        unique_macs = self.__validate_regrade_batch(subscription_id, mac, action)

        post_url = f'{self.base_url}/asset_endpoints/regrades'

        payload = {
            "atomic:operations": []
        }
        for normalized in unique_macs:
            data = {
                "op": "add",
                "data": {
                    "type": "regrades",
                    "attributes": {
                        "action": action,
                        "subscription_type": subscription_id,
                        "mac_address": normalized
                    }
                }
            }
            payload["atomic:operations"].append(data)

        headers = self._atomic_headers()

        ncm = self._v3_request('post', post_url, json=payload, headers=headers)
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        return result

    def unlicense_devices(self, mac_addresses):
        """
        Unlicenses a device by MAC address using the NCM API v3.
        :param mac_addresses: MAC address of the device to unlicense (can be a single MAC address or a list of MAC addresses)
        :return: Result of the unlicense operation
        """
        call_type = 'Unlicense Device'
        self.__check_token()

        # Use the same normalization + batch validation as regrade; the action
        # is fixed to UNLICENSE for this method. A subscription id is not
        # required by unlicense, so pass a sentinel to satisfy the shared
        # non-empty check while validating MACs and batch bounds identically
        # (Req 8.3, 8.6, 8.7).
        unique_macs = self.__validate_regrade_batch(
            "UNLICENSE", mac_addresses, "UNLICENSE")

        post_url = f'{self.base_url}/asset_endpoints/regrades'

        # Create one atomic operation per unique normalized MAC address
        operations = []
        for normalized in unique_macs:
            operations.append({
                "op": "add",
                "data": {
                    "type": "regrades",
                    "attributes": {
                        "mac_address": normalized,
                        "action": "UNLICENSE"
                    }
                }
            })

        payload = {
            "atomic:operations": operations
        }

        headers = self._atomic_headers()

        response = self._v3_request('post', post_url, json=payload, headers=headers)
        
        result = self._return_handler(response.status_code, response.json(), call_type)
        return result
        
    def get_regrades(self, **kwargs):
        """
        Returns regrade jobs with details.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of regrades with details.
        """
        call_type = 'Subscription'
        get_url = f'{self.base_url}/asset_endpoints/regrades'

        allowed_params = ["id", 
                    "action_id", 
                    "mac_address", 
                    "created_at", 
                    "action", 
                    "subcription_type", 
                    "status", 
                    "error_code"]

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_regrade(self, regrade_id):
        """
        Returns a single regrade job by its identifier.
        :param regrade_id: ID of the regrade job to retrieve.
        :return: The regrade job with details.
        """
        call_type = 'Subscription'
        get_url = f'{self.base_url}/asset_endpoints/regrades/{regrade_id}'

        return self.__get_json(get_url, call_type)

    def get_tenants(self, tenant_id=None, **kwargs):
        """
        Returns tenant information from the NCM API v3 tenants endpoint.

        When called without ``tenant_id`` this issues a GET to
        ``/tenants`` and returns the aggregated, paginated list of tenant
        ``data`` objects. When called with ``tenant_id`` it issues a GET to
        ``/tenants/{id}`` and returns that tenant's ``data`` object; if no
        tenant matches the identifier it returns a not-found indicator (an
        empty list) rather than fabricating a tenant object.

        Supported query parameters are the documented list filters ``name`` and
        ``type`` plus ``sort`` and ``limit``. Any other parameter raises a
        ``ValueError`` before a request is dispatched. A missing v3 Bearer token
        raises before dispatch via the shared token guard.

        :param tenant_id: ID of a specific tenant to retrieve. Optional.
        :type tenant_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of tenants, or a single tenant's data when
          ``tenant_id`` is provided (an empty list when no tenant matches).
        """
        call_type = 'Tenants'

        allowed_params = ['name', 'type', 'sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if tenant_id:
            get_url = f'{self.base_url}/tenants/{tenant_id}'
            # __get_json returns a list of accumulated ``data`` objects on
            # success, or an error string routed through _return_handler on a
            # non-2xx page. Treat a bare 'ERROR' string or an empty result as
            # "no matching tenant" rather than fabricating an object (Req 5.6).
            response = self.__get_json(get_url, call_type, params=params)
            if isinstance(response, str):
                if response.startswith('ERROR'):
                    return []
                return response
            if not response:
                return []
            return response

        get_url = f'{self.base_url}/tenants'
        return self.__get_json(get_url, call_type, params=params)

    def get_public_sim_mgmt_assets(self, **kwargs):
        """
        Returns information about SIM asset resources in your NetCloud Manager account.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: SIM asset resources.
        """
        call_type = 'Public SIM Management Assets'
        get_url = f'{self.base_url}/public_sim_mgmt_assets/'

        allowed_params = ['assigned_imei',
                          'carrier',
                          'detected_imei',
                          'device_status',
                          'iccid',
                          'is_licensed',
                          'type',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_public_sim_mgmt_rate_plans(self, **kwargs):
        """
        Returns information about rate plan resources associated with the SIM assets in your NetCloud Manager account.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: Rate plans for SIM assets.
        """
        call_type = 'Public SIM Management Rate Plans'
        get_url = f'{self.base_url}/public_sim_mgmt_rate_plans/'

        allowed_params = ['carrier',
                          'name',
                          'status',
                          'fields',
                          'limit',
                          'sort']

        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_exchange_sites(self, site_id: str = None, exchange_network_id: str = None, name: str = None, **kwargs) -> list:
        """
        Returns information about exchange sites.
        
        :param site_id: ID of a specific exchange site to retrieve. Optional.
        :type site_id: str
        :param exchange_network_id: ID of the exchange network to filter sites by. Optional.
        :type exchange_network_id: str
        :param name: Name of the site to filter by. Optional.
        :type name: str
        :param kwargs: Optional parameters such as limit, sort, fields.
            - limit: Maximum number of sites to return.
            - sort: Field to sort the results by. Can be prefixed with '-' for descending order.
            Valid sort fields: name, updated_at
            - fields: List of fields to include in the response.
            Valid fields: name, created_at, updated_at, editable, lan_as_dns, 
                            local_domain, primary_dns, secondary_dns, tags
        :return: A list of exchange sites, a single site if site_id is provided, or an error message if no sites are found.
        :raises TypeError: If the type of any parameter is incorrect.
        :raises ValueError: If an invalid parameter or value is provided.
        """
        call_type = 'Exchange Sites'
        self.__check_token()
        get_url = f'{self.base_url}/beta/exchange_sites'

        allowed_params = {
            'limit': int,
            'sort': str,
            'fields': list
        }

        valid_sort_fields = ['name', 'updated_at']
        valid_fields = ['name', 'created_at', 'updated_at', 'editable', 'lan_as_dns', 
                        'local_domain', 'primary_dns', 'secondary_dns', 'tags']

        params = {}

        if exchange_network_id:
            if not isinstance(exchange_network_id, str):
                raise TypeError("exchange_network_id must be a string")
            params['filter[exchange_network]'] = exchange_network_id

        if name:
            if not isinstance(name, str):
                raise TypeError("name must be a string")
            params['filter[name]'] = name

        # Type checking and validation for parameters
        for key, value in kwargs.items():
            if key in allowed_params:
                if not isinstance(value, allowed_params[key]):
                    raise TypeError(f"{key} must be of type {allowed_params[key].__name__}")
                
                if key == 'sort':
                    sort_field = value.lstrip('-')
                    if sort_field not in valid_sort_fields:
                        raise ValueError(f"Invalid sort field: {sort_field}")
                
                elif key == 'fields':
                    for field in value:
                        if field not in valid_fields:
                            raise ValueError(f"Invalid field: {field}")
                    params[key] = ','.join(value)
                else:
                    params[key] = value
            
            elif key not in ['search', 'filter']:
                raise ValueError(f"Invalid parameter: {key}")

        if site_id:
            if not isinstance(site_id, str):
                raise TypeError("site_id must be a string")
            # get_url is the collection path '/beta/exchange_sites' (no trailing
            # slash), so append '/{site_id}' to yield the item path
            # '/beta/exchange_sites/{site_id}' (no trailing slash).
            get_url += f'/{site_id}'
            response = self.__get_json(get_url, call_type)

            # __get_json returns a list of accumulated ``data`` objects on
            # success, or an error string (starting with 'ERROR') routed through
            # _return_handler on a non-2xx page. Guard for the string case
            # without calling str-only methods on a list (a pre-existing
            # fragility flagged in task 11.1): a bare string starting with
            # 'ERROR', or an empty result, both mean "no such site".
            if isinstance(response, str):
                if response.startswith('ERROR'):
                    return []
                return response
            if not response:
                return []
            return response

        params.update(self.__parse_kwargs(kwargs, allowed_params.keys()))
        
        response = self.__get_json(get_url, call_type, params=params)

        if not response:
            if name:
                return [f"No site found with name: {name}"]
            if exchange_network_id:
                return [f"No sites found for exchange_network_id: {exchange_network_id}"]
            
        return response
    
    def create_exchange_site(self, name: str, exchange_network_id: str, router_id: str, **kwargs) -> dict:
        """
        Creates an exchange site.

        :param name: Name of the exchange site.
        :type name: str
        :param exchange_network_id: ID of the exchange network.
        :type exchange_network_id: str
        :param router_id: ID of the endpoint.
        :type router_id: str
        :param kwargs: Optional parameters such as primary_dns, secondary_dns, lan_as_dns, local_domain, tags.
            - primary_dns: Primary DNS of the exchange site.
            - secondary_dns: Secondary DNS of the exchange site.
            - lan_as_dns: Whether LAN is used as DNS. Defaults to False.
            - local_domain: Local domain of the exchange site.
            - tags: List of tags for the exchange site.
        :return: The created exchange site data if successful, error message otherwise.
        :raises TypeError: If the type of any parameter is incorrect.
        :raises ValueError: If required parameters are missing or if an invalid parameter or value is provided.
        """
        call_type = 'Create Exchange Site'
        self.__check_token()

        # Type checking for required parameters
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        if not isinstance(exchange_network_id, str):
            raise TypeError("exchange_network_id must be a string")
        if not isinstance(router_id, str):
            raise TypeError("router_id must be a string")

        post_url = f'{self.base_url}/beta/exchange_sites'

        allowed_params = {
            'primary_dns': str,
            'secondary_dns': str,
            'lan_as_dns': bool,
            'local_domain': str,
            'tags': list
        }

        attributes = {
            'name': name,
            'lan_as_dns': False  # Default value
        }

        # Process optional parameters
        for key, value in kwargs.items():
            if key in allowed_params:
                if not isinstance(value, allowed_params[key]):
                    raise TypeError(f"{key} must be of type {allowed_params[key].__name__}")
                if key == 'tags':
                    if not all(isinstance(tag, str) for tag in value):
                        raise TypeError("All tags must be strings")
                attributes[key] = value
            else:
                raise ValueError(f"Invalid parameter: {key}")

        # Check if lan_as_dns is True and primary_dns is provided
        if attributes.get('lan_as_dns', False) and 'primary_dns' not in attributes:
            raise ValueError("primary_dns is required when lan_as_dns is True")

        data = {
            "data": {
                "type": "exchange_user_managed_sites",
                "attributes": attributes,
                "relationships": {
                    "exchange_network": {
                        "data": {
                            "id": exchange_network_id,
                            "type": "exchange_networks"
                        }
                    },
                    "endpoints": {
                        "data": [
                            {
                                "id": router_id,
                                "type": "endpoints"
                            }
                        ]
                    }
                }
            }
        }

        ncm = self._v3_request('post', post_url, data=json.dumps(data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        if ncm.status_code == 201:
            return ncm.json()['data']
        else:
            return result
        
    def update_exchange_site(self, site_id: str = None, name: str = None, **kwargs) -> dict:
        """
        Updates an exchange site.

        :param site_id: ID of the exchange site to update. Optional if name is provided.
        :type site_id: str, optional
        :param name: Name of the exchange site to update or the new name if site_id is provided.
        :type name: str, optional
        :param kwargs: Optional parameters to update. Can include:
            - primary_dns: New primary DNS for the exchange site.
            - secondary_dns: New secondary DNS for the exchange site.
            - lan_as_dns: Whether LAN should be used as DNS.
            - local_domain: New local domain for the exchange site.
            - tags: New list of tags for the exchange site.
        :return: The updated exchange site data if successful, error message otherwise.
        :raises TypeError: If the type of any parameter is incorrect.
        :raises ValueError: If neither site_id nor name is provided, or if an invalid parameter is provided.
        :raises LookupError: If no site is found when searching by id or name.
        """
        call_type = 'Update Exchange Site'
        self.__check_token()

        if (site_id is None or site_id == '') and (name is None or name == ''):
            raise ValueError("Either site_id or name must be provided and cannot be blank")

        allowed_params = {
            'primary_dns': str,
            'secondary_dns': str,
            'lan_as_dns': bool,
            'local_domain': str,
            'tags': list
        }

        # Get current site data 
        if site_id:
            if not isinstance(site_id, str):
                raise TypeError("site_id must be a string")
            current_site = self.get_exchange_sites(site_id=site_id)
            if not current_site:
                raise LookupError(f"No site found with id: {site_id}")
            current_site = current_site[0]
            update_name = name is not None
        elif name:
            if not isinstance(name, str):
                raise TypeError("name must be a string")
            current_site = self.get_exchange_sites(name=name)
            if not current_site:
                raise LookupError(f"No site found with name: {name}")
            current_site = current_site[0]
            site_id = current_site['id']
            update_name = False

        put_url = f'{self.base_url}/beta/exchange_sites/{site_id}'

        attributes = current_site['attributes']
        exchange_network_id = current_site['relationships']['exchange_network']['data']['id']
        router_id = current_site['relationships']['endpoints']['data'][0]['id']

        # Update name if site_id was provided and name is different
        if update_name and name != attributes['name']:
            attributes['name'] = name

        # Update attributes with new values
        for key, expected_type in allowed_params.items():
            if key in kwargs:
                value = kwargs[key]
                if key == 'tags':
                    if not isinstance(value, list):
                        raise TypeError("tags must be a list")
                    if not all(isinstance(tag, str) for tag in value):
                        raise TypeError("All tags must be strings")
                elif not isinstance(value, expected_type):
                    raise TypeError(f"{key} must be of type {expected_type.__name__}")
                attributes[key] = value

        # Check if lan_as_dns is True and primary_dns is provided
        if attributes.get('lan_as_dns', False) and 'primary_dns' not in attributes:
            raise ValueError("primary_dns is required when lan_as_dns is True")

        data = {
            "data": {
                "type": "exchange_user_managed_sites",
                "id": site_id,
                "attributes": attributes,
                "relationships": {
                    "exchange_network": {
                        "data": {
                            "type": "exchange_networks",
                            "id": exchange_network_id
                        }
                    },
                    "endpoints": {
                        "data": [{
                            "type": "routers",
                            "id": router_id
                        }]
                    }
                }
            }
        }

        ncm = self._v3_request('put', put_url, data=json.dumps(data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        if ncm.status_code == 200:
            return ncm.json()['data']
        else:
            return result
    
    def delete_exchange_site(self, site_id: str = None, site_name: str = None) -> dict:
        """
        Deletes an exchange site and its associated resources.

        :param site_id: ID of the exchange site to delete. Optional if site_name is provided.
        :type site_id: str, optional
        :param site_name: Name of the exchange site to delete. Optional if site_id is provided.
        :type site_name: str, optional
        :return: The response from the DELETE request.
        :raises TypeError: If the type of any parameter is incorrect.
        :raises ValueError: If neither site_id nor site_name is provided.
        """
        call_type = 'Delete Exchange Site'
        self.__check_token()

        if not site_id and not site_name:
            raise ValueError("Either site_id or site_name must be provided")

        if site_name and not isinstance(site_name, str):
            raise TypeError("site_name must be a string")
        if site_id and not isinstance(site_id, str):
            raise TypeError("site_id must be a string")

        # Delete associated resources
        if site_id:
            resource_deletion_results = self.delete_exchange_resource(site_id=site_id)
        else:
            resource_deletion_results = self.delete_exchange_resource(site_name=site_name)

        # Delete the exchange site
        if site_id:
            delete_url = f'{self.base_url}/beta/exchange_sites/{site_id}'
        else:
            site_id = self.get_exchange_sites(name=site_name)[0]["id"]
            delete_url = f'{self.base_url}/beta/exchange_sites/{site_id}'

        ncm = self._v3_request('delete', delete_url)
        
        if ncm.status_code == 204:
            site_deletion_result = "deleted"
        else:
            site_deletion_result = "error"

        return {
            "site_deletion_result": site_deletion_result,
            "resource_deletion_results": resource_deletion_results
        }
    
    def get_exchange_resources(self, site_id: str = None, exchange_network_id: str = None, resource_id: str = None, site_name: str = None, **kwargs) -> list:
        """
        Returns information about exchange resources.
        
        :param site_id: ID of the exchange site to filter resources by. Optional.
        :type site_id: str
        :param exchange_network_id: ID of the exchange network to filter resources by. Optional.
        :type exchange_network_id: str
        :param resource_id: ID of a specific exchange resource to retrieve. Optional.
        :type resource_id: str
        :param site_name: Name of the exchange site to filter resources by. Optional.
        :type site_name: str
        :param kwargs: Optional parameters such as name, limit, sort, fields, resource_type.
            - name: Name of the resource to filter by.
            - limit: Maximum number of resources to return.
            - sort: Field to sort the results by. Can be prefixed with '-' for descending order.
            - fields: List of fields to include in the response.
            - resource_type: Type of resource to filter by (exchange_fqdn_resources, exchange_wildcard_fqdn_resources, or exchange_ipsubnet_resources).
        :return: A list of exchange resources or a single resource if resource_id is provided.
        :raises TypeError: If the type of any parameter is incorrect.
        :raises ValueError: If an invalid parameter or value is provided.
        :raises LookupError: If no site is found when searching by site_name.
        """
        call_type = 'Exchange Resources'
        self.__check_token()

        if resource_id:
            if not isinstance(resource_id, str):
                raise TypeError("resource_id must be a string")
            get_url = f"{self.base_url}/beta/exchange_resources/{resource_id}"
        else:
            get_url = f"{self.base_url}/beta/exchange_resources"

        params = {}
        if site_name:
            if not isinstance(site_name, str):
                raise TypeError("site_name must be a string")
            sites = self.get_exchange_sites(name=site_name)
            if not sites:
                raise LookupError(f"No site found with name: {site_name}")
            site_id = sites[0]['id']

        if site_id:
            if not isinstance(site_id, str):
                raise TypeError("site_id must be a string")
            params['filter[exchange_site]'] = site_id
        elif exchange_network_id:
            if not isinstance(exchange_network_id, str):
                raise TypeError("exchange_network_id must be a string")
            params['filter[exchange_network]'] = exchange_network_id

        allowed_params = {
            'name': str,
            'limit': int,
            'sort': str,
            'fields': list,
            'resource_type': str
        }

        valid_sort_fields = ['name', 'created_at', 'updated_at', 'protocols', 'tags', 'domain', 'ip', 'static_prime_ip', 'port_ranges']
        valid_fields = ['name', 'created_at', 'updated_at', 'protocols', 'tags', 'domain', 'ip', 'static_prime_ip', 'port_ranges']
        valid_types = ['exchange_fqdn_resources', 'exchange_wildcard_fqdn_resources', 'exchange_ipsubnet_resources']

        for key, value in kwargs.items():
            if key in allowed_params:
                if not isinstance(value, allowed_params[key]):
                    raise TypeError(f"{key} must be of type {allowed_params[key].__name__}")
                
                if key == 'sort':
                    if value.lstrip('-') not in valid_sort_fields:
                        raise ValueError(f"Invalid sort field: {value}")
                
                elif key == 'fields':
                    for field in value:
                        if field not in valid_fields:
                            raise ValueError(f"Invalid field: {field}")
                    params[key] = ','.join(value)
                
                elif key == 'resource_type':
                    if value not in valid_types:
                        raise ValueError(f"Invalid resource type: {value}. Valid types are: {', '.join(valid_types)}")
                    params['filter[type]'] = value
                
                else:
                    params[key] = value
            
            elif key not in ['search', 'filter']:
                raise ValueError(f"Invalid parameter: {key}")
            else:
                params[key] = value

        response = self._v3_request('get', get_url, params=params)

        if response.status_code == 200:
            data = response.json()['data']
            return data if isinstance(data, list) else [data]
        else:
            return f"ERROR: {response.status_code}: {response.text}"
        
    def create_exchange_resource(self, resource_name: str, resource_type: str, site_id: str = None, site_name: str = None, **kwargs) -> dict:
        """
        Creates an exchange resource.

        :param resource_name: Name for the new resource.
        :type resource_name: str
        :param resource_type: Type of resource to create. Must be one of:
            'exchange_fqdn_resources', 'exchange_wildcard_fqdn_resources', or 'exchange_ipsubnet_resources'.
        :type resource_type: str
        :param site_id: NCX Site ID to add the resource to. Optional if site_name is provided.
        :type site_id: str
        :param site_name: Name of the NCX Site to add the resource to. Optional if site_id is provided.
        :type site_name: str
        :param kwargs: Optional parameters for the resource. Can include:
            - protocols: List of protocols (e.g., ['TCP'], ['UDP'], ['TCP', 'UDP'], or ['ICMP']).
            - tags: List of tags for the resource.
            - domain: Domain name for FQDN or wildcard FQDN resources. Required for these types.
              For wildcard FQDN, must start with '*.'.
            - ip: IP address for IP subnet resources. Required for this type.
            - static_prime_ip: Static prime IP for the resource.
            - port_ranges: List of port ranges. Each range can be an int, a string (e.g., '80' or '8000-8080').
              Will be converted to a list of dicts with 'lower_limit' and 'upper_limit'.
              Not allowed when protocol is ICMP or None.
        :return: The created exchange resource data if successful, error message otherwise.
        :raises TypeError: If the type of any parameter is incorrect.
        :raises ValueError: If required parameters are missing, if an invalid resource type is provided,
                            if an invalid parameter or value is provided, or if port ranges are provided
                            with ICMP protocol or no protocol.
        :raises LookupError: If no site is found when searching by site_name.
        """
        call_type = 'Create Exchange Site Resource'
        self.__check_token()

        # Type checking for required parameters
        if not isinstance(resource_name, str):
            raise TypeError("resource_name must be a string")
        if not isinstance(resource_type, str):
            raise TypeError("resource_type must be a string")

        # Validate and get site_id
        if site_id is None and site_name is None:
            raise ValueError("Either site_id or site_name must be provided")
        
        if site_name:
            if not isinstance(site_name, str):
                raise TypeError("site_name must be a string")
            sites = self.get_exchange_sites(name=site_name)
            if not sites:
                raise LookupError(f"No site found with name: {site_name}")
            site_id = sites[0]['id']
        elif not isinstance(site_id, str):
            raise TypeError("site_id must be a string")

        valid_resource_types = ['exchange_fqdn_resources', 'exchange_wildcard_fqdn_resources', 'exchange_ipsubnet_resources', 'exchange_http_resources', 'exchange_https_resources']
        if resource_type not in valid_resource_types:
            raise ValueError(f"Invalid resource_type. Must be one of: {', '.join(valid_resource_types)}")

        post_url = f'{self.base_url}/beta/exchange_resources'

        allowed_params = {
            'protocols': (list, type(None)),
            'tags': list,
            'domain': str,
            'ip': str,
            'static_prime_ip': str,
            'port_ranges': (list, type(None))
        }

        attributes = {'name': resource_name}

        # Validate required parameters based on resource_type
        if resource_type == 'exchange_ipsubnet_resources':
            if 'ip' not in kwargs:
                raise ValueError("'ip' is required for IP subnet resources")
            attributes['ip'] = kwargs['ip']
        elif resource_type in ['exchange_fqdn_resources', 'exchange_wildcard_fqdn_resources']:
            if 'domain' not in kwargs:
                raise ValueError("'domain' is required for FQDN and wildcard FQDN resources")
            domain = kwargs['domain']
            if resource_type == 'exchange_wildcard_fqdn_resources' and not domain.startswith('*.'):
                raise ValueError("Domain for wildcard FQDN resources must start with '*.'")
            attributes['domain'] = domain

        # Process optional parameters
        for key, value in kwargs.items():
            if key in allowed_params and key not in attributes:
                if not isinstance(value, allowed_params[key]):
                    raise TypeError(f"{key} must be of type {allowed_params[key].__name__}")
                if key == 'tags':
                    if not all(isinstance(tag, str) for tag in value):
                        raise TypeError("All tags must be strings")
                if key == 'protocols':
                    valid_protocols = [['TCP'], ['UDP'], ['TCP', 'UDP'], ['ICMP'], None]
                    if value not in valid_protocols:
                        raise ValueError(f"Invalid protocols. Must be one of: {valid_protocols}")
                    attributes[key] = value
                if key == 'port_ranges':
                    # Check if protocols are set and not ICMP or None
                    if 'protocols' not in attributes or attributes['protocols'] in [['ICMP'], None]:
                        raise ValueError("Port ranges cannot be specified when protocol is ICMP or None")
                    
                    parsed_ranges = []
                    for range_str in value:
                        if isinstance(range_str, int):
                            parsed_ranges.append({'lower_limit': range_str, 'upper_limit': range_str})
                        elif isinstance(range_str, str):
                            if '-' in range_str:
                                lower, upper = map(int, range_str.split('-'))
                                if lower > upper:
                                    raise ValueError(f"Invalid port range: {range_str}. Lower limit must be less than or equal to upper limit.")
                                parsed_ranges.append({'lower_limit': lower, 'upper_limit': upper})
                            else:
                                port = int(range_str)
                                parsed_ranges.append({'lower_limit': port, 'upper_limit': port})
                        else:
                            raise ValueError(f"Invalid port range format: {range_str}")
                    attributes[key] = parsed_ranges
                else:
                    attributes[key] = value

        data = {
            "data": {
                "type": resource_type,
                "attributes": attributes,
                "relationships": {
                    "exchange_site": {
                        "data": {
                            "id": site_id,
                            "type": "exchange_sites"
                        }
                    }
                }
            }
        }

        ncm = self._v3_request('post', post_url, data=json.dumps(data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        if ncm.status_code == 201:
            return ncm.json()['data']
        else:
            return result
    
    def update_exchange_resource(self, resource_id: str, **kwargs) -> dict: #site_id: str = None, site_name: str = None,
        """
        Updates an exchange resource.

        :param resource_id: ID of the exchange resource to update.
        :type resource_id: str
        :param site_id: NCX Site ID of the resource. Optional if site_name is provided.
        :type site_id: str
        :param site_name: Name of the NCX Site of the resource. Optional if site_id is provided.
        :type site_name: str
        :param kwargs: Optional parameters to update. Can include:
            - name: New name for the resource.
            - protocols: List of protocols (e.g., ['TCP'], ['UDP'], ['TCP', 'UDP'], or ['ICMP']).
            - tags: List of tags for the resource.
            - domain: Domain name for FQDN or wildcard FQDN resources.
            - ip: IP address for IP subnet resources.
            - static_prime_ip: Static prime IP for the resource.
            - port_ranges: List of port ranges. Each range can be an int, a string (e.g., '80' or '8000-8080').
              Will be converted to a list of dicts with 'lower_limit' and 'upper_limit'.
              Not allowed when protocol is ICMP or None.
        :return: The updated exchange resource data if successful, error message otherwise.
        :raises TypeError: If the type of any parameter is incorrect.
        :raises ValueError: If an invalid parameter or value is provided,
                            or if port ranges are provided with ICMP protocol or no protocol.
        :raises LookupError: If no site is found when searching by site_name.
        """
        call_type = 'Update Exchange Resource'
        self.__check_token()

        if not isinstance(resource_id, str):
            raise TypeError("resource_id must be a string")

        # Raise an error if resource_type is provided
        if 'resource_type' in kwargs:
            raise ValueError("resource_type cannot be updated after resource creation")

        # Get current resource data
        current_resource = self.get_exchange_resources(resource_id=resource_id)[0]
        resource_type = current_resource['type']
        site_id = current_resource['relationships']['exchange_site']['data']['id']

        put_url = f'{self.base_url}/beta/exchange_resources/{resource_id}'

        allowed_params = {
            'name': str,
            'protocols': (list, type(None)),
            'tags': list,
            'domain': str,
            'ip': str,
            'static_prime_ip': str,
            'port_ranges': (list, type(None))
        }

        attributes = current_resource['attributes']

        # Process optional parameters
        for key, value in kwargs.items():
            if key in allowed_params:
                if not isinstance(value, allowed_params[key]):
                    raise TypeError(f"{key} must be of type {allowed_params[key].__name__}")
                if key == 'tags':
                    if not all(isinstance(tag, str) for tag in value):
                        raise TypeError("All tags must be strings")
                if key == 'protocols':
                    valid_protocols = [['TCP'], ['UDP'], ['TCP', 'UDP'], ['ICMP'], None]
                    if value not in valid_protocols:
                        raise ValueError(f"Invalid protocols. Must be one of: {valid_protocols}")
                    # if protocols is set to ICMP or None, port_ranges must be None
                    if value in [['ICMP'], None]:
                        attributes['port_ranges'] = None
                if key == 'port_ranges':
                    # Check if protocols are set and not ICMP or None
                    if 'protocols' not in attributes or attributes['protocols'] in [['ICMP'], None]:
                        raise ValueError("Port ranges cannot be specified when protocol is ICMP or None")
                    
                    parsed_ranges = []
                    for range_str in value:
                        if isinstance(range_str, int):
                            parsed_ranges.append({'lower_limit': range_str, 'upper_limit': range_str})
                        elif isinstance(range_str, str):
                            if '-' in range_str:
                                lower, upper = map(int, range_str.split('-'))
                                if lower > upper:
                                    raise ValueError(f"Invalid port range: {range_str}. Lower limit must be less than or equal to upper limit.")
                                parsed_ranges.append({'lower_limit': lower, 'upper_limit': upper})
                            else:
                                port = int(range_str)
                                parsed_ranges.append({'lower_limit': port, 'upper_limit': port})
                        else:
                            raise ValueError(f"Invalid port range format: {range_str}")
                    value = parsed_ranges
                attributes[key] = value

        data = {
            "data": {
                "type": resource_type,
                "id": resource_id,
                "attributes": attributes,
                "relationships": {
                    "exchange_site": {
                        "data": {
                            "type": "exchange_sites",
                            "id": site_id
                        }
                    }
                }
            }
        }

        ncm = self._v3_request('put', put_url, data=json.dumps(data))
        result = self._return_handler(ncm.status_code, ncm.json(), call_type)
        if ncm.status_code == 200:
            return ncm.json()['data']
        else:
            return result
        
    def delete_exchange_resource(self, resource_id: str = None, site_name: str = None, site_id: str = None) -> list:
        """
        Deletes exchange resources.

        :param resource_id: ID of the exchange resource to delete. Optional if site_name or site_id is provided.
        :type resource_id: str, optional
        :param site_name: Name of the exchange site to filter resources by. Optional if resource_id or site_id is provided.
        :type site_name: str, optional
        :param site_id: ID of the exchange site to filter resources by. Optional if resource_id or site_name is provided.
        :type site_id: str, optional
        :return: The response from the DELETE request.
        :raises TypeError: If the type of any parameter is incorrect.
        :raises ValueError: If none of resource_id, site_name, or site_id is provided.
        :raises LookupError: If no site is found when searching by site_name.
        """
        call_type = 'Delete Exchange Resource'
        self.__check_token()

        if not resource_id and not site_name and not site_id:
            raise ValueError("Either resource_id, site_name, or site_id must be provided")

        resource_ids = []

        if resource_id:
            if not isinstance(resource_id, str):
                raise TypeError("resource_id must be a string")
            resource_ids.append(resource_id)
        else:
            if site_name:
                if not isinstance(site_name, str):
                    raise TypeError("site_name must be a string")
                sites = self.get_exchange_sites(name=site_name)
                if not sites:
                    raise LookupError(f"No site found with name: {site_name}")
                site_id = sites[0]['id']
            elif site_id and not isinstance(site_id, str):
                raise TypeError("site_id must be a string")

            resources = self.get_exchange_resources(site_id=site_id)
            resource_ids = [resource['id'] for resource in resources]

        results = []
        for rid in resource_ids:
            delete_url = f'{self.base_url}/beta/exchange_resources/{rid}'
            ncm = self._v3_request('delete', delete_url)
            if ncm.status_code == 204:
                results.append({'resource_id': rid, 'status': 'deleted'})
            else:
                results.append({'resource_id': rid, 'status': 'error'})

        return results

    def get_account_authorizations(self, **kwargs):
        """
        Get account authorizations
        
        Args:
            **kwargs: Optional parameters for filtering, sorting, and pagination
                     Supported parameters include:
                     - fields: Comma-separated list of fields to return
                     - user: Filter by user
                     - sort: Field to sort by
                     - limit: Number of records to return
                     - search: Search term to filter results
        
        Returns:
            List of account authorization objects
        """
        get_url = f'{self.base_url}/beta/account_authorizations'
        call_type = 'Account Authorizations'
        allowed_params = ['fields', 'user', 'sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)
        
        return self.__get_json(get_url, call_type, params=params)

    def put_account_authorizations(self, authorization_id: str, account_authorization: dict):
        """
        Update an account authorization role
        
        Args:
            authorization_id: ID of the authorization to update
            account_authorization: Account authorization object
        
        Returns:
            Server response
        """
        call_type = 'Account Authorization'
        if not authorization_id:
            raise ValueError("authorization_id is required to update an account authorization")
        self.__check_token()
        put_url = f'{self.base_url}/beta/account_authorizations/{authorization_id}'
        ncm = self._v3_request('put', put_url, json=account_authorization)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def get_tenant_authorizations(self, authorization_id=None, **kwargs):
        """
        Returns tenant authorization records from the NCM API v3
        tenant_authorizations endpoint.

        When called without ``authorization_id`` this issues a GET to
        ``/beta/tenant_authorizations`` and returns the aggregated, paginated
        list of tenant authorization ``data`` objects. When called with
        ``authorization_id`` it issues a GET to
        ``/beta/tenant_authorizations/{id}`` and returns that authorization's
        ``data`` object.

        A ``search`` parameter is supported and forwarded as a JSON:API search
        query parameter (via the shared ``__parse_search_kwargs`` handling),
        alongside ``sort`` and ``limit``. Any other parameter raises a
        ``ValueError`` before a request is dispatched. A missing v3 Bearer token
        raises before dispatch via the shared token guard. When the list
        endpoint matches zero records an empty list is returned rather than an
        error.

        :param authorization_id: ID of a specific tenant authorization to
          retrieve. Optional.
        :type authorization_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of tenant authorizations, or a single authorization's
          data when ``authorization_id`` is provided.
        """
        call_type = 'Tenant Authorizations'

        allowed_params = ['search', 'sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if authorization_id:
            get_url = f'{self.base_url}/beta/tenant_authorizations/{authorization_id}'
        else:
            get_url = f'{self.base_url}/beta/tenant_authorizations'

        return self.__get_json(get_url, call_type, params=params)

    def update_tenant_authorization(self, authorization_id: str,
                                    role=None, tenant_authorization: dict = None):
        """
        Update a tenant authorization record.

        Issues a PUT to ``/beta/tenant_authorizations/{id}`` with a JSON:API
        request body whose ``data.type`` is ``tenant_authorizations`` and
        returns the updated authorization ``data`` object on success.

        The body may be supplied one of two ways (mirroring
        ``put_account_authorizations``):

        * pass a typed ``role`` string, in which case a minimal JSON:API body is
          constructed as ``{"data": {"type": "tenant_authorizations",
          "id": authorization_id, "attributes": {"role": role}}}``; or
        * pass a caller-supplied generic ``dict`` as ``tenant_authorization``,
          which is sent verbatim (passthrough) so callers can shape the full
          JSON:API document themselves.

        :param authorization_id: ID of the authorization to update. Required;
          a missing or blank value raises before any request is dispatched.
        :type authorization_id: str
        :param role: Optional role to assign, used to build a minimal body.
        :type role: str
        :param tenant_authorization: Optional caller-supplied JSON:API body sent
          verbatim.
        :type tenant_authorization: dict
        :return: The updated tenant authorization data on success.
        """
        call_type = 'Tenant Authorization'
        if not authorization_id or not str(authorization_id).strip():
            raise ValueError(
                "authorization_id is required to update a tenant authorization")

        self.__check_token()

        if tenant_authorization is not None:
            body = tenant_authorization
        else:
            body = {
                "data": {
                    "type": "tenant_authorizations",
                    "id": authorization_id,
                    "attributes": {
                        "role": role
                    }
                }
            }

        put_url = f'{self.base_url}/beta/tenant_authorizations/{authorization_id}'
        ncm = self._v3_request('put', put_url, json=body)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def get_unmasked_wifi_passwords(self, router=None, **kwargs):
        """
        Returns unmasked Wi-Fi passwords for one or more routers from the NCM
        API v3 unmasked_wifi_passwords endpoint.

        Issues a GET to ``/unmasked_wifi_passwords`` (non-beta, no trailing
        slash) with the required ``router`` query parameter and returns the
        aggregated, paginated list of password ``data`` objects. When the
        endpoint matches zero records an empty list is returned rather than an
        error.

        The ``router`` argument is REQUIRED: a single router id, or a list of
        router ids which are comma-joined into the single ``router`` query
        parameter. If ``router`` is absent or blank a ``ValueError`` is raised
        before any request is dispatched. Only ``sort`` and ``limit`` are
        otherwise supported; any other parameter raises a ``ValueError`` before
        a request is dispatched. A missing v3 Bearer token raises before
        dispatch via the shared token guard.

        :param router: A single router id or a list of router ids to retrieve
          unmasked Wi-Fi passwords for. Required.
        :type router: str or list
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of unmasked Wi-Fi password data objects (an empty list
          when no record matches).
        """
        call_type = 'Unmasked WiFi Passwords'

        # ``router`` is required and enforced before any dispatch (Req 7.2).
        if router is None or (isinstance(router, str) and not router.strip()) \
                or (isinstance(router, (list, tuple)) and len(router) == 0):
            raise ValueError(
                "router is required to retrieve unmasked Wi-Fi passwords")

        get_url = f'{self.base_url}/unmasked_wifi_passwords'

        # Validate remaining kwargs and guard the token via the shared helper
        # (Req 7.4, 7.5). ``router`` is a plain query parameter here (not a
        # JSON:API ``filter[...]``), so it is added directly rather than routed
        # through __parse_kwargs.
        allowed_params = ['sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if isinstance(router, (list, tuple)):
            params['router'] = ",".join(str(r) for r in router)
        else:
            params['router'] = str(router)

        return self.__get_json(get_url, call_type, params=params)

    def get_migrations(self, migration_id=None, **kwargs):
        """
        Returns organization migration jobs from the NCM API v3
        organizations migrations endpoint.

        When called without ``migration_id`` this issues a GET to
        ``/organizations/migrations`` (non-beta, no trailing slash) and returns
        the aggregated, paginated list of migration ``data`` objects. When
        called with ``migration_id`` it issues a GET to
        ``/organizations/migrations/{id}`` and returns that migration's ``data``
        object. When the list endpoint matches zero records an empty list is
        returned rather than an error.

        Supported query parameters are the documented list filters ``source``,
        ``status``, ``target`` and ``type`` plus ``sort`` and ``limit``. Any
        other parameter raises a ``ValueError`` before a request is dispatched.
        A missing v3 Bearer token raises before dispatch via the shared token
        guard.

        :param migration_id: ID of a specific migration to retrieve. Optional.
        :type migration_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of migrations, or a single migration's data when
          ``migration_id`` is provided.
        """
        call_type = 'Migrations'

        allowed_params = ['source', 'status', 'target', 'type', 'sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if migration_id:
            get_url = f'{self.base_url}/organizations/migrations/{migration_id}'
        else:
            get_url = f'{self.base_url}/organizations/migrations'

        return self.__get_json(get_url, call_type, params=params)

    def create_migration(self, migration_type: str, attributes: dict = None,
                         relationships: dict = None, **kwargs):
        """
        Creates an organization migration job.

        Issues a POST to ``/organizations/migrations`` with a polymorphic
        JSON:API body whose ``data.type`` equals ``migration_type`` and returns
        the created migration ``data`` object on success. Writes route through
        ``_v3_request`` + ``_return_handler``; a missing v3 Bearer token raises
        before dispatch via the shared token guard.

        ``migration_type`` must be one of ``create_organizations``,
        ``elevate_organizations`` or ``merge_organizations``; any other value
        raises a ``ValueError`` identifying the invalid type and the accepted
        values before any request is dispatched.

        Required inputs are enforced per Swagger before dispatch:

        * ``create_organizations`` and ``elevate_organizations`` require the
          attributes ``organization_name``, ``idle_timeout``,
          ``enhanced_login_security_enabled`` and ``mfa_required``, plus the
          ``organization_administrator`` relationship (``elevate_organizations``
          additionally requires the ``account`` relationship).
        * ``merge_organizations`` requires the ``source_tenant`` relationship
          and has no required attributes.

        :param migration_type: Polymorphic migration type; one of
          ``create_organizations``, ``elevate_organizations``,
          ``merge_organizations``.
        :type migration_type: str
        :param attributes: JSON:API ``data.attributes`` for the migration.
        :type attributes: dict
        :param relationships: JSON:API ``data.relationships`` for the migration.
        :type relationships: dict
        :return: The created migration data on success.
        """
        call_type = 'Migration'

        accepted_types = {
            'create_organizations',
            'elevate_organizations',
            'merge_organizations',
        }
        if migration_type not in accepted_types:
            raise ValueError(
                "Invalid migration_type: {}. Accepted values are: {}".format(
                    migration_type, ", ".join(sorted(accepted_types))))

        attributes = attributes or {}
        relationships = relationships or {}

        # Enforce required attributes and relationships per Swagger before any
        # request is dispatched (Req 8.7).
        if migration_type in ('create_organizations', 'elevate_organizations'):
            required_attrs = [
                'organization_name',
                'idle_timeout',
                'enhanced_login_security_enabled',
                'mfa_required',
            ]
            missing_attrs = [a for a in required_attrs if a not in attributes]
            if missing_attrs:
                raise ValueError(
                    "Missing required attribute(s) for {}: {}".format(
                        migration_type, ", ".join(missing_attrs)))

            required_rels = ['organization_administrator']
            if migration_type == 'elevate_organizations':
                required_rels.append('account')
            missing_rels = [r for r in required_rels if r not in relationships]
            if missing_rels:
                raise ValueError(
                    "Missing required relationship(s) for {}: {}".format(
                        migration_type, ", ".join(missing_rels)))
        else:
            # merge_organizations requires only the source_tenant relationship.
            if 'source_tenant' not in relationships:
                raise ValueError(
                    "Missing required relationship(s) for {}: {}".format(
                        migration_type, "source_tenant"))

        self.__check_token()

        data = {"type": migration_type}
        if attributes:
            data["attributes"] = attributes
        if relationships:
            data["relationships"] = relationships
        body = {"data": data}

        post_url = f'{self.base_url}/organizations/migrations'
        ncm = self._v3_request('post', post_url, json=body)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def get_modem_software_versions(self, group=None, **kwargs):
        """
        Returns available modem software versions from the NCM API v3
        modem_software_versions endpoint.

        Issues a GET to ``/modem_software_versions`` (non-beta, no trailing
        slash) with the required ``filter[group]`` query parameter and returns
        the aggregated, paginated list of software version ``data`` objects.
        When the endpoint matches zero records an empty list is returned rather
        than an error.

        The ``group`` argument is REQUIRED: if it is absent or blank a
        ``ValueError`` is raised before any request is dispatched (Req 9.2).
        Only ``sort`` and ``limit`` are otherwise supported; any other parameter
        raises a ``ValueError`` before a request is dispatched (Req 9.10). A
        missing v3 Bearer token raises before dispatch via the shared token
        guard (Req 9.10).

        :param group: The group identifier used as the required ``filter[group]``
          query parameter. Required.
        :type group: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of modem software version data objects (an empty list
          when no record matches).
        """
        call_type = 'Modem Software Versions'

        # ``group`` (filter[group]) is required and enforced before any dispatch
        # (Req 9.2).
        if group is None or (isinstance(group, str) and not group.strip()):
            raise ValueError(
                "group is required to retrieve modem software versions "
                "(filter[group])")

        get_url = f'{self.base_url}/modem_software_versions'

        # Validate remaining kwargs and guard the token via the shared helper
        # (Req 9.10). The required ``group`` maps to the JSON:API
        # ``filter[group]`` query parameter.
        allowed_params = ['sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)
        params['filter[group]'] = str(group)

        return self.__get_json(get_url, call_type, params=params)

    def get_modem_upgrades(self, modem_upgrade_id=None, group=None,
                           upgrade_type=None, **kwargs):
        """
        Returns modem upgrade jobs from the NCM API v3 modem_upgrades endpoint.

        When called without ``modem_upgrade_id`` this issues a GET to
        ``/modem_upgrades`` (non-beta, no trailing slash). The list form
        requires BOTH the ``filter[group]`` and ``filter[type]`` query
        parameters (supplied via ``group`` and ``upgrade_type``); if either is
        absent or blank a ``ValueError`` is raised before any request is
        dispatched (Req 9.4). The optional ``modem_upgrade_parent`` filter is
        included when supplied (Req 9.5). When called with ``modem_upgrade_id``
        it issues a GET to ``/modem_upgrades/{id}`` and returns that upgrade's
        ``data`` object. When the list endpoint matches zero records an empty
        list is returned rather than an error (Req 9.9).

        Only ``sort`` and ``limit`` are otherwise supported; any other parameter
        raises a ``ValueError`` before a request is dispatched (Req 9.10). A
        missing v3 Bearer token raises before dispatch via the shared token
        guard.

        :param modem_upgrade_id: ID of a specific modem upgrade to retrieve.
          Optional.
        :type modem_upgrade_id: str
        :param group: The group identifier used as the required ``filter[group]``
          query parameter for the list form. Required for the list form.
        :type group: str
        :param upgrade_type: The upgrade type used as the required
          ``filter[type]`` query parameter for the list form. Required for the
          list form.
        :type upgrade_type: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list (``modem_upgrade_parent``, ``sort``,
          ``limit``).
        :return: A list of modem upgrades, or a single modem upgrade's data when
          ``modem_upgrade_id`` is provided (an empty list when no record
          matches the list filters).
        """
        call_type = 'Modem Upgrades'

        allowed_params = ['modem_upgrade_parent', 'sort', 'limit']

        if modem_upgrade_id:
            # Item read: no required filters, validate kwargs + guard token.
            params = self.__parse_kwargs(kwargs, allowed_params)
            get_url = f'{self.base_url}/modem_upgrades/{modem_upgrade_id}'
            return self.__get_json(get_url, call_type, params=params)

        # List form: both filter[group] and filter[type] are required and
        # enforced before any dispatch (Req 9.4).
        missing = []
        if group is None or (isinstance(group, str) and not group.strip()):
            missing.append('filter[group]')
        if upgrade_type is None or \
                (isinstance(upgrade_type, str) and not upgrade_type.strip()):
            missing.append('filter[type]')
        if missing:
            raise ValueError(
                "The following required filter(s) are missing for the modem "
                "upgrades list: {}".format(", ".join(missing)))

        get_url = f'{self.base_url}/modem_upgrades'

        # Validate remaining kwargs and guard the token via the shared helper
        # (Req 9.10). The required group/type map to their JSON:API
        # ``filter[...]`` query parameters; ``modem_upgrade_parent`` is passed
        # through as an optional filter when supplied.
        params = self.__parse_kwargs(kwargs, allowed_params)
        params['filter[group]'] = str(group)
        params['filter[type]'] = str(upgrade_type)

        return self.__get_json(get_url, call_type, params=params)

    @staticmethod
    def _json_media_headers():
        """
        Per-request header override selecting the plain ``application/json``
        media type for both Content-Type and Accept, in place of the session
        default ``application/vnd.api+json`` (Req 9.6, 9.7 -- see the modem
        upgrades Swagger_Spec, which documents ``application/json`` for these
        write operations rather than the JSON:API media type).

        Used by ``create_modem_upgrade`` and ``update_modem_upgrade``. Returns a
        fresh dict on each call so callers cannot mutate shared state -- this
        mirrors the ``_atomic_headers``/``_multipart_headers`` static helpers.
        """
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def create_modem_upgrade(self, carrier, modem_type_name, operation,
                             group_id, **kwargs):
        """
        Creates a modem upgrade job via the NCM API v3 modem_upgrades endpoint.

        Issues a POST to ``/modem_upgrades`` (non-beta, no trailing slash) with a
        request body whose ``data.type`` is ``modem_upgrades`` and a required
        ``group`` relationship pointing at ``group_id``, and returns the created
        modem upgrade ``data`` object on success (Req 9.6).

        The required attributes ``carrier``, ``modem_type_name`` and
        ``operation`` are enforced before any request is dispatched: if any is
        absent or blank a ``ValueError`` naming the missing attribute is raised
        and no request is sent (Req 9.8). Any additional keyword arguments are
        merged into the request body's ``attributes`` so callers can supply the
        optional fields documented by the Swagger_Spec (e.g. ``overwrite``,
        ``connection_states``).

        Unlike the JSON:API endpoints, this operation departs from the session
        default ``application/vnd.api+json`` media type: the per-request
        ``Content-Type``/``Accept`` are overridden to ``application/json`` (see
        ``_json_media_headers``) per the modem upgrades Swagger_Spec (Req 9.6).
        The request routes through the shared ``_v3_request`` (409
        disambiguation and transient retry) and ``_return_handler`` (status
        mapping). A missing v3 Bearer token raises before dispatch via the
        shared token guard.

        :param carrier: Targeted carrier (e.g. ``"att"``). Required.
        :type carrier: str
        :param modem_type_name: Module name (e.g. ``"LP4"``). Required.
        :type modem_type_name: str
        :param operation: Operation type (e.g. ``preview``/``upgrade``/
          ``cancel``). Required.
        :type operation: str
        :param group_id: Identifier of the group targeted by the upgrade, used
          for the required ``group`` relationship.
        :param kwargs: Additional optional attributes merged into the request
          body's ``attributes``.
        :return: The created modem upgrade data on success.
        """
        call_type = 'Create Modem Upgrade'

        # Enforce the required attributes before any dispatch (Req 9.8). A value
        # is missing if it is None or a blank/whitespace-only string.
        required = {
            'carrier': carrier,
            'modem_type_name': modem_type_name,
            'operation': operation,
        }
        missing = [
            name for name, value in required.items()
            if value is None or (isinstance(value, str) and not value.strip())
        ]
        if missing:
            raise ValueError(
                "The following required attribute(s) are missing for the modem "
                "upgrade: {}".format(", ".join(missing)))

        self.__check_token()

        post_url = f'{self.base_url}/modem_upgrades'

        # Required attributes plus any optional attributes the caller supplied.
        attributes = {
            'carrier': carrier,
            'modem_type_name': modem_type_name,
            'operation': operation,
        }
        attributes.update(kwargs)

        data = {
            'data': {
                'type': 'modem_upgrades',
                'attributes': attributes,
                'relationships': {
                    'group': {
                        'data': {
                            'type': 'groups',
                            'id': group_id
                        }
                    }
                }
            }
        }

        # ``application/json`` media-type override per the Swagger_Spec (Req 9.6).
        ncm = self._v3_request(
            'post', post_url, json=data,
            headers=self._json_media_headers())
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def update_modem_upgrade(self, modem_upgrade_id, **kwargs):
        """
        Updates a modem upgrade job via the NCM API v3 modem_upgrades endpoint.

        Issues a PUT to ``/modem_upgrades/{id}`` with a request body whose
        ``data.type`` is ``modem_upgrades`` and returns the updated modem
        upgrade ``data`` object on success (Req 9.7). A non-blank
        ``modem_upgrade_id`` is required: if it is absent or blank a
        ``ValueError`` is raised and no request is dispatched.

        Any keyword arguments are merged into the request body's ``attributes``
        so callers control which fields are updated. As with
        ``create_modem_upgrade`` the per-request ``Content-Type``/``Accept`` are
        overridden to ``application/json`` (see ``_json_media_headers``) per the
        modem upgrades Swagger_Spec, in place of the session default JSON:API
        media type. The request routes through the shared ``_v3_request`` and
        ``_return_handler``; a missing v3 Bearer token raises before dispatch via
        the shared token guard.

        :param modem_upgrade_id: Identifier of the modem upgrade to update.
          Required (non-blank).
        :type modem_upgrade_id: str
        :param kwargs: Attributes merged into the request body's ``attributes``.
        :return: The updated modem upgrade data on success.
        """
        call_type = 'Update Modem Upgrade'

        if modem_upgrade_id is None or \
                (isinstance(modem_upgrade_id, str)
                 and not modem_upgrade_id.strip()):
            raise ValueError(
                "modem_upgrade_id is required to update a modem upgrade")

        self.__check_token()

        put_url = f'{self.base_url}/modem_upgrades/{modem_upgrade_id}'

        data = {
            'data': {
                'type': 'modem_upgrades',
                'id': str(modem_upgrade_id),
                'attributes': dict(kwargs)
            }
        }

        # ``application/json`` media-type override per the Swagger_Spec (Req 9.7).
        ncm = self._v3_request(
            'put', put_url, json=data,
            headers=self._json_media_headers())
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def get_esim_profiles(self, profile_id=None, **kwargs):
        """
        Returns eSIM profiles from the NCM API v3 esim_profiles endpoint.

        When called without ``profile_id`` this issues a GET to
        ``/beta/esim_profiles`` (no trailing slash) and returns the aggregated,
        paginated list of eSIM profile ``data`` objects (Req 10.1). When called
        with ``profile_id`` it issues a GET to ``/beta/esim_profiles/{id}`` and
        returns that profile's ``data`` object (Req 10.2). When the list
        endpoint matches zero records an empty list is returned rather than an
        error (Req 10.9).

        Supported query parameters are the documented filters ``active``,
        ``carrier``, ``classification``, ``eid``, ``iccid``, ``net_device``,
        ``nickname`` and ``profile_name`` plus a ``search`` parameter (Req 10.3),
        alongside ``sort`` and ``limit``. Any other parameter raises a
        ``ValueError`` before a request is dispatched (Req 10.10). A missing v3
        Bearer token raises before dispatch via the shared token guard
        (Req 10.11).

        :param profile_id: ID of a specific eSIM profile to retrieve. Optional.
        :type profile_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of eSIM profiles, or a single profile's data when
          ``profile_id`` is provided.
        """
        call_type = 'eSIM Profiles'

        allowed_params = ['active', 'carrier', 'classification', 'eid', 'iccid',
                          'net_device', 'nickname', 'profile_name', 'search',
                          'sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if profile_id:
            get_url = f'{self.base_url}/beta/esim_profiles/{profile_id}'
        else:
            get_url = f'{self.base_url}/beta/esim_profiles'

        return self.__get_json(get_url, call_type, params=params)

    def get_esim_profiles_manage(self, manage_id=None, **kwargs):
        """
        Returns managed eSIM profiles from the NCM API v3
        esim_profiles/manage endpoint.

        When called without ``manage_id`` this issues a GET to
        ``/beta/esim_profiles/manage`` (no trailing slash) and returns the
        aggregated, paginated list of managed eSIM profile ``data`` objects;
        when called with ``manage_id`` it issues a GET to
        ``/beta/esim_profiles/manage/{id}`` and returns that item's ``data``
        object (Req 10.4). Note that ``manage`` is a FIXED sub-path segment of
        the esim_profiles resource, not an identifier. When the list endpoint
        matches zero records an empty list is returned rather than an error
        (Req 10.9).

        Only ``sort`` and ``limit`` are otherwise supported; any other parameter
        raises a ``ValueError`` before a request is dispatched (Req 10.10). A
        missing v3 Bearer token raises before dispatch via the shared token
        guard (Req 10.11).

        :param manage_id: ID of a specific managed eSIM profile item to
          retrieve. Optional.
        :type manage_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of managed eSIM profiles, or a single item's data when
          ``manage_id`` is provided.
        """
        call_type = 'eSIM Profiles Manage'

        allowed_params = ['sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        # ``manage`` is a fixed sub-path segment; the item id (when supplied) is
        # appended after it: ``/beta/esim_profiles/manage/{id}``.
        if manage_id:
            get_url = f'{self.base_url}/beta/esim_profiles/manage/{manage_id}'
        else:
            get_url = f'{self.base_url}/beta/esim_profiles/manage'

        return self.__get_json(get_url, call_type, params=params)

    def create_esim_profiles_manage(self, body=None, **kwargs):
        """
        Creates a managed eSIM profile via the NCM API v3
        esim_profiles/manage endpoint.

        Issues a POST to ``/beta/esim_profiles/manage`` (no trailing slash) with
        a caller-supplied JSON:API request body sent verbatim (passthrough), and
        returns the created ``data`` object on success (Req 10.5). Because the
        Swagger body for this operation is generic, the caller shapes the full
        JSON:API document themselves -- mirroring the ``put_account_authorizations``
        style -- rather than the method inventing attributes.

        The request routes through the shared ``_v3_request`` (409 disambiguation
        and transient retry) and ``_return_handler`` (status mapping). A missing
        v3 Bearer token raises before dispatch via the shared token guard
        (Req 10.11).

        :param body: The JSON:API request body to send verbatim. Required.
        :type body: dict
        :return: The created managed eSIM profile data on success.
        """
        call_type = 'Create eSIM Profiles Manage'

        if body is None:
            raise ValueError(
                "body is required to create a managed eSIM profile")

        self.__check_token()

        post_url = f'{self.base_url}/beta/esim_profiles/manage'
        ncm = self._v3_request('post', post_url, json=body)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    @staticmethod
    def _multipart_headers():
        """
        Per-request header override for the ``multipart/form-data`` esim
        activation POST (Req 10.7 -- see design "Media Types").

        The v3 session sets a default ``Content-Type: application/vnd.api+json``
        for every request. A multipart upload must instead let ``requests``
        compute the ``Content-Type: multipart/form-data; boundary=...`` header
        itself from the ``files=``/``data=`` form fields -- it cannot do that if
        a fixed ``Content-Type`` is already present. Setting the per-request
        ``Content-Type`` to ``None`` tells ``requests`` to drop the session
        default so it can build the multipart body and boundary (analogous to
        the ``_atomic_headers`` override for regrades). ``Accept`` continues to
        request the JSON:API response media type. A fresh dict is returned on
        each call so callers cannot mutate shared state.
        """
        return {
            'Content-Type': None,
            'Accept': V3_MEDIA_TYPE
        }

    def get_esim_profile_activations(self, activation_id=None, **kwargs):
        """
        Returns eSIM profile activations from the NCM API v3
        esim_profile_activations endpoint.

        When called without ``activation_id`` this issues a GET to
        ``/beta/esim_profile_activations`` (no trailing slash) and returns the
        aggregated, paginated list of activation ``data`` objects; when called
        with ``activation_id`` it issues a GET to
        ``/beta/esim_profile_activations/{id}`` and returns that activation's
        ``data`` object (Req 10.6). When the list endpoint matches zero records
        an empty list is returned rather than an error (Req 10.9).

        Only ``sort`` and ``limit`` are otherwise supported; any other parameter
        raises a ``ValueError`` before a request is dispatched (Req 10.10). A
        missing v3 Bearer token raises before dispatch via the shared token
        guard (Req 10.11).

        :param activation_id: ID of a specific eSIM profile activation to
          retrieve. Optional.
        :type activation_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of eSIM profile activations, or a single activation's
          data when ``activation_id`` is provided.
        """
        call_type = 'eSIM Profile Activations'

        allowed_params = ['sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if activation_id:
            get_url = f'{self.base_url}/beta/esim_profile_activations/{activation_id}'
        else:
            get_url = f'{self.base_url}/beta/esim_profile_activations'

        return self.__get_json(get_url, call_type, params=params)

    def create_esim_profile_activation(self, operation: str, payload, **kwargs):
        """
        Creates an eSIM profile activation via the NCM API v3
        esim_profile_activations endpoint using a multipart upload.

        Issues a POST to ``/beta/esim_profile_activations`` (no trailing slash)
        with a ``multipart/form-data`` body carrying the two Swagger-documented
        form fields ``operation`` (a string) and ``payload`` (the activation
        payload, typically binary), and returns the created ``data`` object on
        success (Req 10.7).

        Unlike the JSON:API endpoints, this operation departs from the session
        default ``application/vnd.api+json`` media type: the form fields are
        passed to ``requests`` via ``data=``/``files=`` and the per-request
        ``Content-Type`` is overridden (see ``_multipart_headers``) so
        ``requests`` builds the ``multipart/form-data`` body and computes the
        MIME boundary itself, rather than a fixed JSON:API ``Content-Type``. The
        request routes through the shared ``_v3_request`` (409 disambiguation
        and transient retry) and ``_return_handler`` (status mapping). A missing
        v3 Bearer token raises before dispatch via the shared token guard
        (Req 10.11).

        :param operation: The activation operation form field. Required.
        :type operation: str
        :param payload: The activation payload form field (binary or file-like).
          Required.
        :return: The created eSIM profile activation data on success.
        """
        call_type = 'Create eSIM Profile Activation'

        self.__check_token()

        post_url = f'{self.base_url}/beta/esim_profile_activations'

        # Send ``operation`` and ``payload`` as multipart/form-data form fields.
        # ``payload`` is routed through ``files=`` so requests treats it as a
        # file part (binary), while ``operation`` is a plain text field; the
        # header override drops the JSON:API Content-Type so requests sets
        # ``multipart/form-data`` with its own boundary.
        ncm = self._v3_request(
            'post',
            post_url,
            data={'operation': operation},
            files={'payload': payload},
            headers=self._multipart_headers()
        )
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def update_esim_profile_activation(self, activation_id, **kwargs):
        """
        Updates an eSIM profile activation via the NCM API v3
        esim_profile_activations endpoint.

        Issues a PUT to ``/beta/esim_profile_activations/{id}`` with a
        caller-supplied JSON:API request body sent verbatim (generic ``dict``
        passthrough), and returns the updated ``data`` object on success
        (Req 10.8). Because the Swagger body for this operation is generic, the
        caller shapes the full JSON:API document themselves -- mirroring the
        ``put_account_authorizations`` / ``create_esim_profiles_manage`` style --
        rather than the method inventing attributes. The caller supplies the
        body via a ``body`` keyword argument.

        The request routes through the shared ``_v3_request`` (409
        disambiguation and transient retry) and ``_return_handler`` (status
        mapping). A missing v3 Bearer token raises before dispatch via the
        shared token guard (Req 10.11).

        :param activation_id: ID of the eSIM profile activation to update.
          Required.
        :type activation_id: str
        :param kwargs: Must include ``body`` -- the JSON:API request body sent
          verbatim.
        :return: The updated eSIM profile activation data on success.
        """
        call_type = 'Update eSIM Profile Activation'

        if not activation_id or not str(activation_id).strip():
            raise ValueError(
                "activation_id is required to update an eSIM profile activation")

        body = kwargs.get('body')
        if body is None:
            raise ValueError(
                "body is required to update an eSIM profile activation")

        self.__check_token()

        put_url = f'{self.base_url}/beta/esim_profile_activations/{activation_id}'
        ncm = self._v3_request('put', put_url, json=body)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def get_starlink_interfaces(self, interface_id=None, **kwargs):
        """
        Returns Starlink interfaces from the NCM API v3 starlink_interfaces
        endpoint.

        When called without ``interface_id`` this issues a GET to
        ``/starlink_interfaces`` (non-beta, no trailing slash) and returns the
        aggregated, paginated list of interface ``data`` objects (Req 11.1).
        When called with ``interface_id`` it issues a GET to
        ``/starlink_interfaces/{id}`` and returns that interface's ``data``
        object (Req 11.1). When the list endpoint matches zero records an empty
        list is returned rather than an error (Req 11.9).

        Supported query parameters are the documented filters ``carrier``,
        ``gateway_ip``, ``net_device``, ``port``, ``software_version`` and
        ``terminal_identifier`` plus a ``sort`` parameter (Req 11.2), alongside
        ``limit``. Any other parameter raises a ``ValueError`` before a request
        is dispatched (Req 11.10). A missing v3 Bearer token raises before
        dispatch via the shared token guard (Req 11.11).

        :param interface_id: ID of a specific Starlink interface to retrieve.
          Optional.
        :type interface_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of Starlink interfaces, or a single interface's data
          when ``interface_id`` is provided.
        """
        call_type = 'Starlink Interfaces'

        allowed_params = ['carrier', 'gateway_ip', 'net_device', 'port',
                          'software_version', 'terminal_identifier',
                          'sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if interface_id:
            get_url = f'{self.base_url}/starlink_interfaces/{interface_id}'
        else:
            get_url = f'{self.base_url}/starlink_interfaces'

        return self.__get_json(get_url, call_type, params=params)

    def get_starlink_interface_reboots(self, reboot_id=None, **kwargs):
        """
        Returns Starlink interface reboots from the NCM API v3
        starlink_interfaces/reboots endpoint.

        When called without ``reboot_id`` this issues a GET to
        ``/starlink_interfaces/reboots`` (non-beta, no trailing slash) and
        returns the aggregated, paginated list of reboot ``data`` objects; when
        called with ``reboot_id`` it issues a GET to
        ``/starlink_interfaces/reboots/{id}`` and returns that reboot's ``data``
        object (Req 11.3). Note that ``reboots`` is a FIXED sub-path segment of
        the starlink_interfaces resource, not an identifier. When the list
        endpoint matches zero records an empty list is returned rather than an
        error (Req 11.9).

        Only ``sort`` and ``limit`` are otherwise supported; any other parameter
        raises a ``ValueError`` before a request is dispatched (Req 11.10). A
        missing v3 Bearer token raises before dispatch via the shared token
        guard (Req 11.11).

        :param reboot_id: ID of a specific Starlink interface reboot to
          retrieve. Optional.
        :type reboot_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of Starlink interface reboots, or a single reboot's data
          when ``reboot_id`` is provided.
        """
        call_type = 'Starlink Interface Reboots'

        allowed_params = ['sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        # ``reboots`` is a fixed sub-path segment; the item id (when supplied) is
        # appended after it: ``/starlink_interfaces/reboots/{id}``.
        if reboot_id:
            get_url = f'{self.base_url}/starlink_interfaces/reboots/{reboot_id}'
        else:
            get_url = f'{self.base_url}/starlink_interfaces/reboots'

        return self.__get_json(get_url, call_type, params=params)

    def get_starlink_interface_stows(self, stow_id=None, **kwargs):
        """
        Returns Starlink interface stows from the NCM API v3
        starlink_interfaces/stows endpoint.

        When called without ``stow_id`` this issues a GET to
        ``/starlink_interfaces/stows`` (non-beta, no trailing slash) and returns
        the aggregated, paginated list of stow ``data`` objects; when called
        with ``stow_id`` it issues a GET to
        ``/starlink_interfaces/stows/{id}`` and returns that stow's ``data``
        object (Req 11.5). Note that ``stows`` is a FIXED sub-path segment of
        the starlink_interfaces resource, not an identifier. When the list
        endpoint matches zero records an empty list is returned rather than an
        error (Req 11.9).

        Only ``sort`` and ``limit`` are otherwise supported; any other parameter
        raises a ``ValueError`` before a request is dispatched (Req 11.10). A
        missing v3 Bearer token raises before dispatch via the shared token
        guard (Req 11.11).

        :param stow_id: ID of a specific Starlink interface stow to retrieve.
          Optional.
        :type stow_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of Starlink interface stows, or a single stow's data
          when ``stow_id`` is provided.
        """
        call_type = 'Starlink Interface Stows'

        allowed_params = ['sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        # ``stows`` is a fixed sub-path segment; the item id (when supplied) is
        # appended after it: ``/starlink_interfaces/stows/{id}``.
        if stow_id:
            get_url = f'{self.base_url}/starlink_interfaces/stows/{stow_id}'
        else:
            get_url = f'{self.base_url}/starlink_interfaces/stows'

        return self.__get_json(get_url, call_type, params=params)

    def get_starlink_diagnostics(self, diagnostics_id=None, **kwargs):
        """
        Returns Starlink diagnostics from the NCM API v3 starlink_diagnostics
        endpoint.

        When called without ``diagnostics_id`` this issues a GET to
        ``/starlink_diagnostics`` (non-beta, no trailing slash) and returns the
        aggregated, paginated list of diagnostics ``data`` objects; when called
        with ``diagnostics_id`` it issues a GET to
        ``/starlink_diagnostics/{id}`` and returns that diagnostics ``data``
        object (Req 11.8). When the list endpoint matches zero records an empty
        list is returned rather than an error (Req 11.9).

        Only ``sort`` and ``limit`` are otherwise supported; any other parameter
        raises a ``ValueError`` before a request is dispatched (Req 11.10). A
        missing v3 Bearer token raises before dispatch via the shared token
        guard (Req 11.11).

        :param diagnostics_id: ID of a specific Starlink diagnostics record to
          retrieve. Optional.
        :type diagnostics_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of Starlink diagnostics, or a single diagnostics record's
          data when ``diagnostics_id`` is provided.
        """
        call_type = 'Starlink Diagnostics'

        allowed_params = ['sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if diagnostics_id:
            get_url = f'{self.base_url}/starlink_diagnostics/{diagnostics_id}'
        else:
            get_url = f'{self.base_url}/starlink_diagnostics'

        return self.__get_json(get_url, call_type, params=params)

    def create_starlink_interface_reboot(self, interface_id, **kwargs):
        """
        Requests a reboot of a Starlink interface via the NCM API v3
        starlink_interfaces/reboots endpoint.

        Issues a POST to ``/starlink_interfaces/reboots`` (non-beta, no trailing
        slash) with a JSON:API body whose ``data.type`` is
        ``starlink_interface_reboots`` and a required ``starlink_interface``
        relationship pointing at the target interface, and returns the created
        reboot ``data`` object on success (Req 11.4). The write routes through
        ``_v3_request`` + ``_return_handler``; a missing v3 Bearer token raises
        before dispatch via the shared token guard.

        :param interface_id: ID of the Starlink interface to reboot. Required.
        :type interface_id: str
        :return: The created reboot job data on success, error message
          otherwise.
        """
        call_type = 'Starlink Interface Reboot'
        self.__check_token()

        post_url = f'{self.base_url}/starlink_interfaces/reboots'

        body = {
            "data": {
                "type": "starlink_interface_reboots",
                "relationships": {
                    "starlink_interface": {
                        "data": {
                            "type": "starlink_interfaces",
                            "id": interface_id
                        }
                    }
                }
            }
        }

        ncm = self._v3_request('post', post_url, json=body)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def create_starlink_interface_stow(self, interface_id, action, **kwargs):
        """
        Requests a stow or unstow of a Starlink interface via the NCM API v3
        starlink_interfaces/stows endpoint.

        Issues a POST to ``/starlink_interfaces/stows`` (non-beta, no trailing
        slash) with a JSON:API body whose ``data.type`` is
        ``starlink_interface_stows``, an ``attributes.action`` of the requested
        action, and a required ``starlink_interface`` relationship pointing at
        the target interface, and returns the created stow ``data`` object on
        success (Req 11.6). The write routes through ``_v3_request`` +
        ``_return_handler``; a missing v3 Bearer token raises before dispatch
        via the shared token guard.

        ``action`` is REQUIRED and constrained to ``stow`` or ``unstow``: if it
        is absent, blank, or any other value a ``ValueError`` is raised
        identifying the accepted values before any request is dispatched
        (Req 11.7).

        :param interface_id: ID of the Starlink interface to stow/unstow.
          Required.
        :type interface_id: str
        :param action: The stow action to perform; one of ``stow`` or
          ``unstow``. Required.
        :type action: str
        :return: The created stow job data on success, error message otherwise.
        """
        call_type = 'Starlink Interface Stow'

        accepted_actions = {'stow', 'unstow'}
        if action not in accepted_actions:
            raise ValueError(
                "action is required and must be one of: {}".format(
                    ", ".join(sorted(accepted_actions))))

        self.__check_token()

        post_url = f'{self.base_url}/starlink_interfaces/stows'

        body = {
            "data": {
                "type": "starlink_interface_stows",
                "attributes": {
                    "action": action
                },
                "relationships": {
                    "starlink_interface": {
                        "data": {
                            "type": "starlink_interfaces",
                            "id": interface_id
                        }
                    }
                }
            }
        }

        ncm = self._v3_request('post', post_url, json=body)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def get_lan_devices(self, device_id=None, **kwargs):
        """
        Returns LAN devices from the NCM API v3 lan_devices endpoint.

        When called without ``device_id`` this issues a GET to ``/lan_devices``
        (non-beta, no trailing slash) and returns the aggregated, paginated list
        of LAN device ``data`` objects; when called with ``device_id`` it issues
        a GET to ``/lan_devices/{id}`` and returns that device's ``data`` object
        (Req 12.1). When the list endpoint matches zero records an empty list is
        returned rather than an error (Req 12.5).

        The documented filters ``account``, ``device_status``, ``group``,
        ``id``, ``lan_firmware_upgrade_status``, ``lan_product_info``,
        ``mac_address``, ``name``, ``router``, ``serial_number``, ``type`` and
        their ``__ne`` operator forms (``device_status__ne``,
        ``lan_firmware_upgrade_status__ne``, ``name__ne``, ``type__ne``) plus
        ``sort`` are supported and mapped to JSON:API query parameters; the
        ``__ne`` forms route through the shared ``a__b`` -> ``filter[a][b]``
        rule (e.g. ``type__ne=x`` -> ``filter[type][ne]=x``) (Req 12.2, 12.4).
        Any other parameter raises a ``ValueError`` before a request is
        dispatched (Req 12.6). A missing v3 Bearer token raises before dispatch
        via the shared token guard (Req 12.7).

        :param device_id: ID of a specific LAN device to retrieve. Optional.
        :type device_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of LAN devices, or a single device's data when
          ``device_id`` is provided.
        """
        call_type = 'LAN Devices'

        allowed_params = ['account', 'device_status', 'device_status__ne',
                          'group', 'id', 'lan_firmware_upgrade_status',
                          'lan_firmware_upgrade_status__ne', 'lan_product_info',
                          'mac_address', 'name', 'name__ne', 'router',
                          'serial_number', 'type', 'type__ne', 'sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if device_id:
            get_url = f'{self.base_url}/lan_devices/{device_id}'
        else:
            get_url = f'{self.base_url}/lan_devices'

        return self.__get_json(get_url, call_type, params=params)

    def get_lan_product_infos(self, product_info_id=None, **kwargs):
        """
        Returns LAN product infos from the NCM API v3 lan_product_infos
        endpoint.

        When called without ``product_info_id`` this issues a GET to
        ``/lan_product_infos`` (non-beta, no trailing slash) and returns the
        aggregated, paginated list of product info ``data`` objects; when called
        with ``product_info_id`` it issues a GET to
        ``/lan_product_infos/{id}`` and returns that product info's ``data``
        object (Req 12.3). When the list endpoint matches zero records an empty
        list is returned rather than an error (Req 12.5).

        The documented filters ``id``, ``name``, ``product_type`` and its
        ``__ne`` operator form (``product_type__ne``) plus ``sort`` are
        supported and mapped to JSON:API query parameters; the ``__ne`` form
        routes through the shared ``a__b`` -> ``filter[a][b]`` rule (e.g.
        ``product_type__ne=x`` -> ``filter[product_type][ne]=x``) (Req 12.4).
        Any other parameter raises a ``ValueError`` before a request is
        dispatched (Req 12.6). A missing v3 Bearer token raises before dispatch
        via the shared token guard (Req 12.7).

        :param product_info_id: ID of a specific LAN product info to retrieve.
          Optional.
        :type product_info_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of LAN product infos, or a single product info's data
          when ``product_info_id`` is provided.
        """
        call_type = 'LAN Product Infos'

        allowed_params = ['id', 'name', 'product_type', 'product_type__ne',
                          'sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if product_info_id:
            get_url = f'{self.base_url}/lan_product_infos/{product_info_id}'
        else:
            get_url = f'{self.base_url}/lan_product_infos'

        return self.__get_json(get_url, call_type, params=params)

    def get_remote_connect_profiles(self, profile_id=None, **kwargs):
        """
        Returns remote connect profiles from the NCM API v3
        remote_connect_profiles endpoint.

        When called without ``profile_id`` this issues a GET to
        ``/remote_connect_profiles`` (non-beta, no trailing slash) and returns
        the aggregated, paginated list of profile ``data`` objects. When called
        with ``profile_id`` it issues a GET to
        ``/remote_connect_profiles/{id}`` and returns that profile's ``data``
        object. When the list endpoint matches zero records an empty list is
        returned rather than an error (Req 13.2).

        The documented filters ``address``, ``name``, ``router`` and ``type``
        plus ``sort`` are supported and mapped to JSON:API query parameters
        (Req 13.1, 13.2). Any other parameter raises a ``ValueError`` before a
        request is dispatched. A missing v3 Bearer token raises before dispatch
        via the shared token guard (Req 13.12).

        :param profile_id: ID of a specific remote connect profile to retrieve.
          Optional.
        :type profile_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of remote connect profiles, or a single profile's data
          when ``profile_id`` is provided.
        """
        call_type = 'Remote Connect Profiles'

        allowed_params = ['address', 'name', 'router', 'type', 'sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if profile_id:
            get_url = f'{self.base_url}/remote_connect_profiles/{profile_id}'
        else:
            get_url = f'{self.base_url}/remote_connect_profiles'

        return self.__get_json(get_url, call_type, params=params)

    def create_remote_connect_profile(self, profile_type: str,
                                      attributes: dict = None,
                                      relationships: dict = None, **kwargs):
        """
        Creates a remote connect profile.

        Issues a POST to ``/remote_connect_profiles`` with a polymorphic
        JSON:API body whose ``data.type`` equals ``profile_type`` and returns
        the created profile ``data`` object on success. Writes route through
        ``_v3_request`` + ``_return_handler``; a missing v3 Bearer token raises
        before dispatch via the shared token guard (Req 13.3, 13.12).

        ``profile_type`` must be one of the six documented profile types
        (``remote_connect_ssh_profile``, ``remote_connect_http_profile``,
        ``remote_connect_https_profile``, ``remote_connect_rdp_profile``,
        ``remote_connect_vnc_profile``, ``remote_connect_serial_profile``); any
        other value raises a ``ValueError`` identifying the invalid type and the
        accepted values before any request is dispatched.

        Required inputs are enforced per Swagger before dispatch (Req 13.10):
        every type requires the attributes ``name``, ``port`` and ``address``;
        ``remote_connect_ssh_profile`` additionally requires ``username``. A
        ``router`` relationship is required for every type. When any required
        attribute or the ``router`` relationship is missing a ``ValueError`` is
        raised and no request is transmitted.

        :param profile_type: Polymorphic remote connect profile type; one of the
          six documented types.
        :type profile_type: str
        :param attributes: JSON:API ``data.attributes`` for the profile.
        :type attributes: dict
        :param relationships: JSON:API ``data.relationships`` for the profile
          (must include the required ``router`` relationship).
        :type relationships: dict
        :return: The created remote connect profile data on success.
        """
        call_type = 'Remote Connect Profile'

        accepted_types = {
            'remote_connect_ssh_profile',
            'remote_connect_http_profile',
            'remote_connect_https_profile',
            'remote_connect_rdp_profile',
            'remote_connect_vnc_profile',
            'remote_connect_serial_profile',
        }
        if profile_type not in accepted_types:
            raise ValueError(
                "Invalid profile_type: {}. Accepted values are: {}".format(
                    profile_type, ", ".join(sorted(accepted_types))))

        attributes = attributes or {}
        relationships = relationships or {}

        # Enforce required attributes per Swagger before any request is
        # dispatched (Req 13.10). All types require name/port/address; SSH also
        # requires username.
        required_attrs = ['name', 'port', 'address']
        if profile_type == 'remote_connect_ssh_profile':
            required_attrs.append('username')
        missing_attrs = [a for a in required_attrs if a not in attributes]
        if missing_attrs:
            raise ValueError(
                "Missing required attribute(s) for {}: {}".format(
                    profile_type, ", ".join(missing_attrs)))

        # A router relationship is required for every profile type (Req 13.10).
        if 'router' not in relationships:
            raise ValueError(
                "Missing required relationship(s) for {}: {}".format(
                    profile_type, "router"))

        self.__check_token()

        data = {"type": profile_type, "attributes": attributes,
                "relationships": relationships}
        body = {"data": data}

        post_url = f'{self.base_url}/remote_connect_profiles'
        ncm = self._v3_request('post', post_url, json=body)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def update_remote_connect_profile(self, profile_id: str, **kwargs):
        """
        Updates a remote connect profile.

        Issues a PUT to ``/remote_connect_profiles/{id}`` and returns the
        updated profile ``data`` object on success. Writes route through
        ``_v3_request`` + ``_return_handler``; a missing v3 Bearer token raises
        before dispatch via the shared token guard (Req 13.4, 13.12).

        ``profile_id`` is required: a missing or blank value raises before any
        request is dispatched (Req 13.11). Updating a real-but-absent id
        surfaces as an ``HTTPError`` via ``_return_handler`` (404) rather than a
        silent change.

        The JSON:API body is assembled from the caller-supplied keyword
        arguments: ``attributes`` and/or ``relationships`` (both optional
        ``dict``); ``profile_type`` (optional) sets ``data.type``.

        :param profile_id: ID of the remote connect profile to update. Required.
        :type profile_id: str
        :param kwargs: Optional ``profile_type`` (str), ``attributes`` (dict)
          and ``relationships`` (dict) used to build the JSON:API body.
        :return: The updated remote connect profile data on success.
        """
        call_type = 'Remote Connect Profile'
        if not profile_id or not str(profile_id).strip():
            raise ValueError(
                "profile_id is required to update a remote connect profile")

        self.__check_token()

        data = {"id": profile_id}
        if kwargs.get('profile_type') is not None:
            data['type'] = kwargs['profile_type']
        if kwargs.get('attributes') is not None:
            data['attributes'] = kwargs['attributes']
        if kwargs.get('relationships') is not None:
            data['relationships'] = kwargs['relationships']
        body = {"data": data}

        put_url = f'{self.base_url}/remote_connect_profiles/{profile_id}'
        ncm = self._v3_request('put', put_url, json=body)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def delete_remote_connect_profile(self, profile_id: str):
        """
        Deletes a remote connect profile.

        Issues a DELETE to ``/remote_connect_profiles/{id}`` and routes the
        response through ``_return_handler``; a missing v3 Bearer token raises
        before dispatch via the shared token guard (Req 13.5, 13.12).

        ``profile_id`` is required: a missing or blank value raises before any
        request is dispatched (Req 13.11). Deleting a real-but-absent id
        surfaces as an ``HTTPError`` via ``_return_handler`` (404) rather than a
        silent no-op.

        :param profile_id: ID of the remote connect profile to delete. Required.
        :type profile_id: str
        :return: The response routed through ``_return_handler`` on success.
        """
        call_type = 'Remote Connect Profile'
        if not profile_id or not str(profile_id).strip():
            raise ValueError(
                "profile_id is required to delete a remote connect profile")

        self.__check_token()

        delete_url = f'{self.base_url}/remote_connect_profiles/{profile_id}'
        ncm = self._v3_request('delete', delete_url)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def get_lan_manager_options(self, option_id=None, **kwargs):
        """
        Returns LAN manager options from the NCM API v3
        lan_manager_options endpoint.

        When called without ``option_id`` this issues a GET to
        ``/lan_manager_options`` (non-beta, no trailing slash) and returns the
        aggregated, paginated list of option ``data`` objects. When called with
        ``option_id`` it issues a GET to ``/lan_manager_options/{id}`` and
        returns that option's ``data`` object. When the list endpoint matches
        zero records an empty list is returned rather than an error (Req 13.6).

        The documented filters ``enabled`` and ``router`` plus ``sort`` are
        supported and mapped to JSON:API query parameters (Req 13.6, 13.7). Any
        other parameter raises a ``ValueError`` before a request is dispatched.
        A missing v3 Bearer token raises before dispatch via the shared token
        guard (Req 13.12).

        :param option_id: ID of a specific LAN manager option to retrieve.
          Optional.
        :type option_id: str
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of LAN manager options, or a single option's data when
          ``option_id`` is provided.
        """
        call_type = 'LAN Manager Options'

        allowed_params = ['enabled', 'router', 'sort', 'limit']
        params = self.__parse_kwargs(kwargs, allowed_params)

        if option_id:
            get_url = f'{self.base_url}/lan_manager_options/{option_id}'
        else:
            get_url = f'{self.base_url}/lan_manager_options'

        return self.__get_json(get_url, call_type, params=params)

    def create_lan_manager_option(self, enabled: bool, router_id: str,
                                  account_id: str = None, **kwargs):
        """
        Creates a LAN manager option.

        Issues a POST to ``/lan_manager_options`` with a JSON:API body whose
        ``data.type`` equals ``"lan_manager_options"`` and returns the created
        option ``data`` object on success. Writes route through ``_v3_request``
        + ``_return_handler``; a missing v3 Bearer token raises before dispatch
        via the shared token guard (Req 13.8, 13.12).

        Required inputs are enforced per Swagger before dispatch (Req 13.10):
        the ``enabled`` attribute is required and a ``router`` relationship
        (built from ``router_id``) is required. When either is missing a
        ``ValueError`` is raised and no request is transmitted. An optional
        ``account`` relationship is included when ``account_id`` is supplied.

        :param enabled: Value for the required ``attributes.enabled`` flag.
        :type enabled: bool
        :param router_id: ID of the router for the required ``router``
          relationship.
        :type router_id: str
        :param account_id: Optional ID for an ``account`` relationship.
        :type account_id: str
        :return: The created LAN manager option data on success.
        """
        call_type = 'LAN Manager Option'

        # Enforce required attribute/relationship inputs before any request is
        # dispatched (Req 13.10).
        if enabled is None:
            raise ValueError(
                "Missing required attribute for lan_manager_options: enabled")
        if not router_id or not str(router_id).strip():
            raise ValueError(
                "Missing required relationship for lan_manager_options: router")

        self.__check_token()

        relationships = {
            "router": {"data": {"type": "routers", "id": router_id}}
        }
        if account_id is not None:
            relationships["account"] = {
                "data": {"type": "accounts", "id": account_id}
            }

        data = {"type": "lan_manager_options",
                "attributes": {"enabled": enabled},
                "relationships": relationships}
        body = {"data": data}

        post_url = f'{self.base_url}/lan_manager_options'
        ncm = self._v3_request('post', post_url, json=body)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def update_lan_manager_option(self, option_id: str, **kwargs):
        """
        Updates a LAN manager option.

        Issues a PUT to ``/lan_manager_options/{id}`` and returns the updated
        option ``data`` object on success. Writes route through ``_v3_request``
        + ``_return_handler``; a missing v3 Bearer token raises before dispatch
        via the shared token guard (Req 13.9, 13.12).

        ``option_id`` is required: a missing or blank value raises before any
        request is dispatched (Req 13.11). Updating a real-but-absent id
        surfaces as an ``HTTPError`` via ``_return_handler`` (404) rather than a
        silent change.

        The JSON:API body is assembled from the caller-supplied keyword
        arguments: ``attributes`` and/or ``relationships`` (both optional
        ``dict``). ``data.type`` is set to ``"lan_manager_options"``.

        :param option_id: ID of the LAN manager option to update. Required.
        :type option_id: str
        :param kwargs: Optional ``attributes`` (dict) and ``relationships``
          (dict) used to build the JSON:API body.
        :return: The updated LAN manager option data on success.
        """
        call_type = 'LAN Manager Option'
        if not option_id or not str(option_id).strip():
            raise ValueError(
                "option_id is required to update a LAN manager option")

        self.__check_token()

        data = {"type": "lan_manager_options", "id": option_id}
        if kwargs.get('attributes') is not None:
            data['attributes'] = kwargs['attributes']
        if kwargs.get('relationships') is not None:
            data['relationships'] = kwargs['relationships']
        body = {"data": data}

        put_url = f'{self.base_url}/lan_manager_options/{option_id}'
        ncm = self._v3_request('put', put_url, json=body)
        return self._return_handler(ncm.status_code, ncm.json(), call_type)

    def update_user_role(self, email: str, new_role: str) -> dict:
        """
        Updates the role of a user in NCM.
        
        Args:
            email (str): Email address of the user
            new_role (str): New role to assign to the user
            
        Returns:
            dict: Response from the API containing the updated authorization
        """
        try:
            # Find user
            users = self.get_users(email=email)
            if not users:
                raise ValueError(f"User not found: {email}")
            
            user_id = users[0]['id']

            # Get account authorizations
            auths = self.get_account_authorizations(user=user_id)
            if not auths:
                raise ValueError(f"No account authorization found for: {email}")

            account_auth_data = auths[0]
            account_auth_id = account_auth_data['id']

            # Update authorization
            account_auth = {
                "data": {
                    **account_auth_data,
                    "attributes": {
                        **account_auth_data["attributes"],
                        "role": new_role
                    }
                }
            }
            call_type = 'Update User Role'
            response = self.put_account_authorizations(account_auth_id, account_auth)
            return response
            
        except Exception as e:
            self.log('error', f"Error updating role for {email}: {str(e)}")
            raise
        
    # def get_group_modem_upgrade_jobs(self, **kwargs):
    #     """
    #     Returns users with details.
    #     :param kwargs: A set of zero or more allowed parameters
    #       in the allowed_params list.
    #     :return: A list of users with details.
    #     """
    #     call_type = 'Group Modem Upgrades'
    #     get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs'

    #     allowed_params = ['id',
    #                       'group_id',
    #                       'module_id',
    #                       'carrier_id',
    #                       'overwrite',
    #                       'active_only',
    #                       'upgrade_only',
    #                       'batch_size',
    #                       'created_at',
    #                       'created_at__lt',
    #                       'created_at__lte',
    #                       'created_at__gt',
    #                       'created_at__gte',
    #                       'created_at__ne',
    #                       'updated_at',
    #                       'updated_at__lt',
    #                       'updated_at__lte',
    #                       'updated_at__gt',
    #                       'updated_at__gte',
    #                       'updated_at__ne',
    #                       'available_version',
    #                       'modem_count',
    #                       'success_count',
    #                       'failed_count',
    #                       'statuscarrier_name',
    #                       'module_name',
    #                       'type',
    #                       'fields',
    #                       'limit',
    #                       'sort']

    #     if "search" not in kwargs.keys():
    #         params = self.__parse_kwargs(kwargs, allowed_params)
    #     else:
    #         if kwargs['search']:
    #             params = self.__parse_search_kwargs(kwargs, allowed_params)
    #         else:
    #             params = self.__parse_kwargs(kwargs, allowed_params)
    #     return self.__get_json(get_url, call_type, params=params)

    # def get_group_modem_upgrade_job(self, job_id, **kwargs):
    #     """
    #     Returns users with details.
    #     :param job_id: The ID of the job
    #     :param kwargs: A set of zero or more allowed parameters
    #       in the allowed_params list.
    #     :return: A list of users with details.
    #     """
    #     call_type = 'Group Modem Upgrades'
    #     get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs/{job_id}'

    #     allowed_params = ['id',
    #                       'group_id',
    #                       'module_id',
    #                       'carrier_id',
    #                       'overwrite',
    #                       'active_only',
    #                       'upgrade_only',
    #                       'batch_size',
    #                       'created_at',
    #                       'updated_at',
    #                       'available_version',
    #                       'modem_count',
    #                       'success_count',
    #                       'failed_count',
    #                       'statuscarrier_name',
    #                       'module_name',
    #                       'type',
    #                       'fields',
    #                       'limit',
    #                       'sort']

    #     if "search" not in kwargs.keys():
    #         params = self.__parse_kwargs(kwargs, allowed_params)
    #     else:
    #         if kwargs['search']:
    #             params = self.__parse_search_kwargs(kwargs, allowed_params)
    #         else:
    #             params = self.__parse_kwargs(kwargs, allowed_params)
    #     return self.__get_json(get_url, call_type, params=params)

    # def get_group_modem_upgrade_summary(self, **kwargs):
    #     """
    #     Returns users with details.
    #     :param kwargs: A set of zero or more allowed parameters
    #       in the allowed_params list.
    #     :return: A list of users with details.
    #     """
    #     call_type = 'Group Modem Upgrades'
    #     get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs'

    #     allowed_params = ['group_id',
    #                       'module_id',
    #                       'module_name',
    #                       'upgradable_modems',
    #                       'up_to_date_modems',
    #                       'summary_data',
    #                       'type',
    #                       'fields',
    #                       'limit',
    #                       'sort']

    #     if "search" not in kwargs.keys():
    #         params = self.__parse_kwargs(kwargs, allowed_params)
    #     else:
    #         if kwargs['search']:
    #             params = self.__parse_search_kwargs(kwargs, allowed_params)
    #         else:
    #             params = self.__parse_kwargs(kwargs, allowed_params)
    #     return self.__get_json(get_url, call_type, params=params)

    # def get_group_modem_upgrade_device_summary(self, **kwargs):
    #     """
    #     Returns users with details.
    #     :param kwargs: A set of zero or more allowed parameters
    #       in the allowed_params list.
    #     :return: A list of users with details.
    #     """
    #     call_type = 'Group Modem Upgrades'
    #     get_url = f'{self.base_url}/beta/group_modem_upgrade_jobs'

    #     allowed_params = ['group_id',
    #                       'module_id',
    #                       'carrier_id',
    #                       'overwrite',
    #                       'active_only',
    #                       'upgrade_only',
    #                       'router_name',
    #                       'net_device_name',
    #                       'current_version',
    #                       'type',
    #                       'fields',
    #                       'limit',
    #                       'sort']

    #     if "search" not in kwargs.keys():
    #         params = self.__parse_kwargs(kwargs, allowed_params)
    #     else:
    #         if kwargs['search']:
    #             params = self.__parse_search_kwargs(kwargs, allowed_params)
    #         else:
    #             params = self.__parse_kwargs(kwargs, allowed_params)
    #     return self.__get_json(get_url, call_type, params=params)

    # def create_modem_upgrade(self, group_id: int, carrier: str, modem_type_name: str, operation: str, overwrite: bool = False, connection_states: list = None, **kwargs) -> dict:
    #     """
    #     Creates a new modem upgrade job.

    #     :param group_id: ID of the group to target for the modem upgrade.
    #     :type group_id: int
    #     :param carrier: Targeted carrier (e.g., "att").
    #     :type carrier: str
    #     :param modem_type_name: Module name associated with module_id (e.g., "LP4").
    #     :type modem_type_name: str
    #     :param operation: Operation type [preview|upgrade|cancel].
    #     :type operation: str
    #     :param overwrite: Overwrite modem firmware if on the same version already. Defaults to False.
    #     :type overwrite: bool
    #     :param connection_states: The targeted net devices connection state. Optional.
    #     :type connection_states: list, optional
    #     :param kwargs: Additional optional parameters to include in the request.
    #     :return: The created modem upgrade job data if successful, error message otherwise.
    #     :raises TypeError: If the type of any parameter is incorrect.
    #     :raises ValueError: If required parameters are missing or if an invalid parameter or value is provided.
    #     """
    #     call_type = 'Create Modem Upgrade'

    #     # Type checking for required parameters
    #     if not isinstance(group_id, int):
    #         raise TypeError("group_id must be an integer")
    #     if not isinstance(carrier, str):
    #         raise TypeError("carrier must be a string")
    #     if not isinstance(modem_type_name, str):
    #         raise TypeError("modem_type_name must be a string")
    #     if not isinstance(operation, str):
    #         raise TypeError("operation must be a string")
    #     if not isinstance(overwrite, bool):
    #         raise TypeError("overwrite must be a boolean")

    #     # Validate operation value
    #     valid_operations = ["preview", "upgrade", "cancel"]
    #     if operation not in valid_operations:
    #         raise ValueError(f"operation must be one of: {valid_operations}")

    #     # Validate carrier and modem_type_name are not empty
    #     if not carrier.strip():
    #         raise ValueError("carrier cannot be empty")
    #     if not modem_type_name.strip():
    #         raise ValueError("modem_type_name cannot be empty")

    #     post_url = f'{self.base_url}/beta/modem_upgrades'

    #     # Build attributes dictionary with required fields
    #     attributes = {
    #         'carrier': carrier,
    #         'modem_type_name': modem_type_name,
    #         'operation': operation,
    #         'overwrite': overwrite
    #     }

    #     # Add connection_states if provided
    #     if connection_states is not None:
    #         if not isinstance(connection_states, list):
    #             raise TypeError("connection_states must be a list")
    #         if not all(isinstance(state, str) for state in connection_states):
    #             raise TypeError("All connection_states must be strings")
    #         attributes['connection_states'] = connection_states

    #     # Add any additional parameters from kwargs directly to attributes
    #     for key, value in kwargs.items():
    #         attributes[key] = value

    #     data = {
    #         "data": {
    #             "type": "modem_upgrades",
    #             "attributes": attributes,
    #             "relationships": {
    #                 "group": {
    #                     "data": {
    #                         "type": "groups",
    #                         "id": group_id
    #                     }
    #                 }
    #             }
    #         }
    #     }

    #     ncm = self.session.post(post_url, data=json.dumps(data))
    #     result = self._return_handler(ncm.status_code, ncm.json(), call_type)
    #     if ncm.status_code == 201:
    #         return ncm.json()['data']
    #     else:
    #         return result

    # --- Private Cellular (ported from the original ncm2 rewrite) -------------
    # Endpoints live under /api/v3/beta/ with no trailing slash.

    def _pc_body(self, ncm):
        """JSON body of a response, or None when it is empty (e.g. 204)."""
        return ncm.json() if ncm.text else None

    def get_private_cellular_networks(self, **kwargs):
        """
        Returns private cellular networks.
        :param kwargs: A set of zero or more allowed parameters
          in the allowed_params list.
        :return: A list of private cellular networks.
        """
        call_type = 'Private Cellular Networks'
        get_url = f'{self.base_url}/beta/private_cellular_networks'
        allowed_params = ['core_ip', 'created_at', 'created_at__lt',
                          'created_at__lte', 'created_at__gt', 'created_at__gte',
                          'created_at__ne', 'ha_enabled', 'id',
                          'mobility_gateways', 'mobility_gateway_virtual_ip',
                          'name', 'state', 'status', 'tac', 'type',
                          'updated_at', 'updated_at__lt', 'updated_at__lte',
                          'updated_at__gt', 'updated_at__gte', 'updated_at__ne',
                          'fields', 'limit', 'sort']
        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def create_private_cellular_network(self, name, core_ip, ha_enabled=False,
                                        mobility_gateway_virtual_ip=None,
                                        mobility_gateways=None):
        """
        Creates a private cellular network.
        :param mobility_gateways: Core IDs, as a list or comma-separated string.
        """
        call_type = 'Private Cellular Network'
        self.__check_token()
        post_url = f'{self.base_url}/beta/private_cellular_networks'
        data = {"data": {"type": "private_cellular_networks", "attributes": {
            "name": name, "core_ip": core_ip, "ha_enabled": ha_enabled,
            "mobility_gateway_virtual_ip": mobility_gateway_virtual_ip}}}
        if mobility_gateways:
            gateways = (mobility_gateways.split(",")
                        if isinstance(mobility_gateways, str)
                        else mobility_gateways)
            data["data"]["relationships"] = {"mobility_gateways": {
                "data": [{"type": "private_cellular_cores", "id": g}
                         for g in gateways]}}
        ncm = self._v3_request('post', post_url, data=json.dumps(data))
        return self._return_handler(ncm.status_code, self._pc_body(ncm), call_type)

    def delete_private_cellular_network(self, network_id):
        """Deletes a private cellular network."""
        call_type = 'Private Cellular Network'
        if not network_id or not str(network_id).strip():
            raise ValueError("network_id is required")
        self.__check_token()
        delete_url = f'{self.base_url}/beta/private_cellular_networks/{network_id}'
        ncm = self._v3_request('delete', delete_url)
        return self._return_handler(ncm.status_code, self._pc_body(ncm), call_type)

    def get_private_cellular_cores(self, **kwargs):
        """Returns private cellular cores (mobility gateways)."""
        call_type = 'Private Cellular Cores'
        get_url = f'{self.base_url}/beta/private_cellular_cores'
        allowed_params = ['created_at', 'id', 'management_ip', 'network',
                          'router', 'status', 'type', 'updated_at', 'url',
                          'fields', 'limit', 'sort']
        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_private_cellular_radios(self, **kwargs):
        """Returns private cellular radios."""
        call_type = 'Private Cellular Radios'
        get_url = f'{self.base_url}/beta/private_cellular_radios'
        allowed_params = ['admin_state', 'antenna_azimuth', 'antenna_beamwidth',
                          'antenna_downtilt', 'antenna_gain', 'bandwidth',
                          'category', 'cpi_id', 'cpi_name', 'created_at',
                          'description', 'fccid', 'height', 'height_type', 'id',
                          'indoor_deployment', 'latitude', 'location',
                          'longitude', 'mac', 'name', 'network',
                          'serial_number', 'tdd_mode', 'tx_power', 'type',
                          'updated_at', 'fields', 'limit', 'sort']
        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def get_private_cellular_radio_groups(self, **kwargs):
        """Returns private cellular radio groups."""
        call_type = 'Private Cellular Radio Groups'
        get_url = f'{self.base_url}/beta/private_cellular_radio_groups'
        allowed_params = ['created_at', 'created_at__lt', 'created_at__lte',
                          'created_at__gt', 'created_at__gte', 'created_at__ne',
                          'description', 'id', 'name', 'network', 'type',
                          'updated_at', 'updated_at__lt', 'updated_at__lte',
                          'updated_at__gt', 'updated_at__gte', 'updated_at__ne',
                          'fields', 'limit', 'sort']
        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def create_private_cellular_radio_group(self, name, description, network=None):
        """Creates a private cellular radio group."""
        call_type = 'Private Cellular Radio Group'
        self.__check_token()
        post_url = f'{self.base_url}/beta/private_cellular_radio_groups'
        data = {"data": {"type": "private_cellular_radio_groups",
                         "attributes": {"name": name, "description": description}}}
        if network:
            data["data"]["relationships"] = {"network": {"data": {
                "type": "private_cellular_networks", "id": network}}}
        ncm = self._v3_request('post', post_url, data=json.dumps(data))
        return self._return_handler(ncm.status_code, self._pc_body(ncm), call_type)

    def get_private_cellular_sims(self, **kwargs):
        """Returns private cellular SIMs."""
        call_type = 'Private Cellular SIMs'
        get_url = f'{self.base_url}/beta/private_cellular_sims'
        allowed_params = ['created_at', 'created_at__lt', 'created_at__lte',
                          'created_at__gt', 'created_at__gte', 'created_at__ne',
                          'iccid', 'id', 'imsi', 'last_contact_at',
                          'last_contact_at__lt', 'last_contact_at__lte',
                          'last_contact_at__gt', 'last_contact_at__gte',
                          'last_contact_at__ne', 'name', 'network', 'state',
                          'state_updated_at', 'state_updated_at__lt',
                          'state_updated_at__lte', 'state_updated_at__gt',
                          'state_updated_at__gte', 'state_updated_at__ne',
                          'type', 'fields', 'limit', 'sort']
        params = self.__parse_kwargs(kwargs, allowed_params)
        return self.__get_json(get_url, call_type, params=params)

    def delete_exchange_resources_for_site(self, site_id):
        """Deletes every exchange resource on a site (ncm2 convenience name)."""
        return self.delete_exchange_resource(site_id=site_id)
