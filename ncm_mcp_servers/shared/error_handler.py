"""Error handler module for NCM MCP Servers.

Translates ncm.py responses and exceptions into structured MCP responses.
All output is sanitized to ensure API credentials never appear in responses.
"""

import os
from typing import Any, Dict, List, Optional

from requests.exceptions import ConnectionError, Timeout, RequestException


# HTTP status code to human-readable message mapping
HTTP_ERROR_MESSAGES = {
    400: "Bad request",
    401: "Unauthorized - invalid or expired API credentials",
    403: "Forbidden - insufficient permissions",
    404: "Resource not found",
    500: "Server error - please retry",
}

# Environment variable names that hold credential values to sanitize
_CREDENTIAL_ENV_VARS = (
    "X_CP_API_ID",
    "X_CP_API_KEY",
    "X_ECM_API_ID",
    "X_ECM_API_KEY",
    "NCM_API_TOKEN",
)


def _get_credential_values():
    # type: () -> List[str]
    """Returns a list of non-empty credential values from environment."""
    values = []
    for var in _CREDENTIAL_ENV_VARS:
        val = os.environ.get(var)
        if val:
            values.append(val)
    return values


def _sanitize(text, credential_values=None):
    # type: (str, Optional[List[str]]) -> str
    """Strip any credential values from the given text."""
    if not isinstance(text, str):
        return text
    if credential_values is None:
        credential_values = _get_credential_values()
    for cred in credential_values:
        if cred and cred in text:
            text = text.replace(cred, "***")
    return text


def _sanitize_dict(data, credential_values=None):
    # type: (Any, Optional[List[str]]) -> Any
    """Recursively sanitize all string values in a dict or list."""
    if credential_values is None:
        credential_values = _get_credential_values()
    if not credential_values:
        return data
    if isinstance(data, str):
        return _sanitize(data, credential_values)
    if isinstance(data, dict):
        return {k: _sanitize_dict(v, credential_values) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_dict(item, credential_values) for item in data]
    return data


def _parse_ncm_error(result):
    # type: (str) -> Optional[Dict[str, Any]]
    """Parse ncm.py error string format into structured error dict.

    The ncm.py library returns error strings in the format:
        "ERROR: {status_code}: {details}"

    Returns a dict with code, message, details if the string matches,
    or None if it does not.
    """
    if not isinstance(result, str) or not result.startswith("ERROR:"):
        return None
    parts = result.split(":", 2)
    if len(parts) < 2:
        return None
    try:
        code = int(parts[1].strip())
    except (ValueError, IndexError):
        return None
    details = parts[2].strip() if len(parts) > 2 else ""
    message = HTTP_ERROR_MESSAGES.get(code, "Unknown error")
    return {"code": code, "message": message, "details": details}


def handle_ncm_response(result, operation):
    # type: (Any, str) -> dict
    """Process ncm.py return values into structured responses.

    - If *result* is an error string ("ERROR: {code}: {details}"),
      parse it into a structured error response.
    - If *result* is a list or dict, wrap it in a success response.
    - All output is sanitized to strip credential values.

    Returns:
        dict with ``success``, ``data``/``error``, and ``operation`` keys.
    """
    credential_values = _get_credential_values()

    # Check for ncm.py error string
    parsed = _parse_ncm_error(result)
    if parsed is not None:
        parsed["details"] = _sanitize(parsed["details"], credential_values)
        return {
            "success": False,
            "error": parsed,
            "operation": operation,
        }

    # Successful result — sanitize and wrap
    sanitized_data = _sanitize_dict(result, credential_values)
    return {
        "success": True,
        "data": sanitized_data,
        "operation": operation,
    }


def handle_exception(exc, operation):
    # type: (Exception, str) -> dict
    """Handle exceptions raised during NCM API calls.

    - ConnectionError / Timeout / RequestException -> connectivity error.
    - Any other Exception -> generic error without exposing internals.
    """
    credential_values = _get_credential_values()

    if isinstance(exc, (ConnectionError, Timeout)):
        return {
            "success": False,
            "error": {
                "code": 0,
                "message": "Connectivity error - unable to reach NCM API",
                "details": _sanitize(str(exc), credential_values),
            },
            "operation": operation,
        }

    if isinstance(exc, RequestException):
        return {
            "success": False,
            "error": {
                "code": 0,
                "message": "Connectivity error - unable to reach NCM API",
                "details": _sanitize(str(exc), credential_values),
            },
            "operation": operation,
        }

    # Broad Exception — do not expose internals
    return {
        "success": False,
        "error": {
            "code": 0,
            "message": "An unexpected error occurred",
            "details": "",
        },
        "operation": operation,
    }


def validate_required_params(**params):
    # type: (...) -> Optional[dict]
    """Check for missing required parameters.

    Pass each required parameter as a keyword argument. If any value is
    None, a structured error listing the missing parameter names is
    returned. Returns None when all parameters are present.

    Example::

        err = validate_required_params(router_id=router_id, name=name)
        if err is not None:
            return err
    """
    missing = [name for name, value in params.items() if value is None]
    if not missing:
        return None
    return {
        "success": False,
        "error": {
            "code": 400,
            "message": "Missing required parameters",
            "details": "Missing: {}".format(", ".join(sorted(missing))),
        },
        "operation": "validate_params",
    }
