"""Shared module for NCM MCP Servers.

Contains common utilities: NCM client initialization, error handling,
and credential loading used by all three MCP server packages.
"""

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)
from ncm_mcp_servers.shared.credentials import (
    ApiCredentials,
    load_credentials,
)
from ncm_mcp_servers.shared.client import get_ncm_client

__all__ = [
    "handle_exception",
    "handle_ncm_response",
    "validate_required_params",
    "ApiCredentials",
    "load_credentials",
    "get_ncm_client",
]
