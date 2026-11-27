"""
Shared HTTP plumbing for the NCM API clients: the base client, the v3
media-type and retry constants, and the masked-secret filter applied to
every configuration write.
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


# NCM API v3 media types (JSON:API). The default type is applied to the v3
# session in NcmClientv3.__init__; the atomic-operations extension type is used
# as a per-request Content-Type/Accept override for endpoints that require the
# JSON:API atomic operations extension (regrades). Centralized here so every
# call site uses the identical string and the two cannot drift (Req 3.2, 3.4).
V3_MEDIA_TYPE = 'application/vnd.api+json'
V3_ATOMIC_MEDIA_TYPE = (
    'application/vnd.api+json;ext="https://jsonapi.org/ext/atomic"'
)

# Retryable HTTP statuses for the NCM API v3 client only (Req 15.1, 15.2). The
# base client's default forcelist is {408, 503, 504}; v3 widens it to also retry
# rate-limit (429) and bad-gateway (502) responses. NcmClientv3.__init__ passes
# this explicitly when no retry_on is supplied, so the v2 client's forcelist is
# left unchanged. 409 is deliberately absent: it is overloaded on v3 (rate-limit
# vs. JSON:API validation error) and cannot be expressed in the urllib3 Retry
# forcelist without also retrying legitimate validation conflicts, so it is
# disambiguated in the v3 request path instead (see NcmClientv3._v3_get / the
# 409 handling in __get_json).
V3_RETRY_ON = [
    HTTPStatus.REQUEST_TIMEOUT,       # 408
    HTTPStatus.TOO_MANY_REQUESTS,     # 429
    HTTPStatus.BAD_GATEWAY,           # 502
    HTTPStatus.SERVICE_UNAVAILABLE,   # 503
    HTTPStatus.GATEWAY_TIMEOUT,       # 504
]


def __is_json(test_json):
    """
    Checks if a string is a valid json object
    """
    try:
        json.loads(test_json)
    except ValueError:
        return False
    return True


# --- Masked-secret filter -------------------------------------------------
#
# NCM returns every secret in a config (passwords, Wi-Fi PSKs, certificate
# keys, NTP keys, ...) as the literal string "*". Echoing a config you read back
# would send "*" as the new secret: NCM either rejects it
# ("cannot set wlan.radio.1.bss.0.wpapsk to *: too short") or stores it.
# Every config write goes through strip_masked_secrets(), which simply leaves
# those keys out so the target keeps its existing secret.

MASKED_SECRET = '*'

# Endpoints whose request body carries a router/group "configuration" diff.
_CONFIG_URL_RE = re.compile(r'/(configuration_managers|groups)/')


def strip_masked_secrets(obj):
    """
    Return a copy of ``obj`` with every dict entry whose value is exactly
    ``"*"`` (NCM's masked-secret placeholder) removed, at any depth.

    Lists are walked but their elements are kept, so removals-list paths are
    untouched. The input is never mutated.
    """
    if isinstance(obj, dict):
        return {k: strip_masked_secrets(v) for k, v in obj.items()
                if not (isinstance(v, str) and v == MASKED_SECRET)}
    if isinstance(obj, list):
        return [strip_masked_secrets(v) for v in obj]
    return obj


def _strip_config_body(body):
    """
    If ``body`` is a dict carrying a ``configuration`` key, return a copy with
    masked secrets stripped from that value only. Otherwise return ``body``
    unchanged.
    """
    if isinstance(body, dict) and 'configuration' in body:
        cleaned = dict(body)
        cleaned['configuration'] = strip_masked_secrets(body['configuration'])
        return cleaned
    return body


class ConfigSafeSession(Session):
    """
    ``requests.Session`` that strips masked ``"*"`` secrets from the
    ``configuration`` of every PUT/PATCH/POST to ``/configuration_managers/``
    or ``/groups/``.

    Filtering at the session means every SDK method is covered, and so is a
    caller that uses ``client.session.put(...)`` directly. Bodies are only
    rewritten when something was actually removed, so all other requests go
    out byte-for-byte as before.
    """

    def request(self, method, url, *args, **kwargs):
        if (str(method).upper() in ('PUT', 'PATCH', 'POST')
                and _CONFIG_URL_RE.search(str(url))):
            if kwargs.get('json') is not None:
                kwargs['json'] = _strip_config_body(kwargs['json'])
            data = kwargs.get('data')
            if isinstance(data, (str, bytes, bytearray)):
                try:
                    parsed = json.loads(data)
                except ValueError:
                    parsed = None
                cleaned = _strip_config_body(parsed)
                if cleaned != parsed:
                    kwargs['data'] = json.dumps(cleaned)
            elif isinstance(data, dict):
                kwargs['data'] = _strip_config_body(data)
        return super().request(method, url, *args, **kwargs)


class BaseNcmClient:
    def __init__(self,
                 log_events=True,
                 logger=None,
                 retries=5,
                 retry_backoff_factor=2,
                 retry_on=None,
                 base_url=None):
        """
        Constructor. Sets up and opens request session.
        :param retries: number of retries on failure. Optional.
        :param retry_backoff_factor: backoff time multiplier for retries.
          Optional.
        :param retry_on: types of errors on which automatic retry will occur.
          Optional.
        :param base_url: # base url for calls. Configurable for testing.
          Optional.
        """
        if retry_on is None:
            retry_on = [
                HTTPStatus.REQUEST_TIMEOUT,
                HTTPStatus.GATEWAY_TIMEOUT,
                HTTPStatus.SERVICE_UNAVAILABLE
            ]
        self.log_events = log_events
        self.logger = logger
        self.session = ConfigSafeSession()
        self.adapter = HTTPAdapter(
            max_retries=Retry(total=retries,
                              backoff_factor=retry_backoff_factor,
                              status_forcelist=retry_on,
                              redirect=3
                              )
        )
        self.base_url = base_url
        self.session.mount(self.base_url, self.adapter)
    
    def log(self, level, message):
        """
        Logs messages if self.logEvents is True.
        """
        if self.log_events:
            if self.logger:
                log_level = getattr(self.logger, level)
                log_level(message)
            else:
                print(f"{level}: {message}", file=sys.stderr) 

    def _return_handler(self, status_code, returntext, obj_type):
        """
        Handles HTTP response status codes. Raises exceptions for error
        status codes so callers can use try/except for error handling.
        Returns response data for success codes.
        """
        if str(status_code) == '200':
            return f'{obj_type} operation successful.'
        elif str(status_code) == '201':
            self.log('info', '{0} created Successfully'.format(str(obj_type)))
            return returntext
        elif str(status_code) == '202':
            self.log('info', '{0} accepted Successfully'.format(str(obj_type)))
            return returntext
        elif str(status_code) == '204':
            self.log('info', '{0} deleted Successfully'.format(str(obj_type)))
            return returntext
        elif str(status_code) == '400':
            self.log('error', 'Bad Request')
            raise requests.exceptions.HTTPError(
                f'{status_code}: {returntext}',
                response=type('Response', (), {'status_code': status_code, 'text': str(returntext)})()
            )
        elif str(status_code) == '401':
            self.log('error', 'Unauthorized Access')
            raise requests.exceptions.HTTPError(
                f'{status_code}: {returntext}',
                response=type('Response', (), {'status_code': status_code, 'text': str(returntext)})()
            )
        elif str(status_code) == '404':
            self.log('error', 'Resource Not Found\n')
            raise requests.exceptions.HTTPError(
                f'{status_code}: {returntext}',
                response=type('Response', (), {'status_code': status_code, 'text': str(returntext)})()
            )
        elif str(status_code) == '500':
            self.log('error', 'HTTP 500 - Server Error\n')
            raise requests.exceptions.HTTPError(
                f'{status_code}: {returntext}',
                response=type('Response', (), {'status_code': status_code, 'text': str(returntext)})()
            )
        else:
            self.log('info', f'HTTP Status Code: {status_code} - {returntext}\n')
