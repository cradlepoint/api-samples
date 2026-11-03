"""MCP tools for NCM Wi-Fi password retrieval.

Provides:
- get_unmasked_wifi_passwords: Retrieve unmasked Wi-Fi passwords for routers
"""

from typing import List, Optional, Union

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register Wi-Fi password tools."""

    @mcp.tool()
    def get_unmasked_wifi_passwords(
        router: Union[str, List[str]] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve unmasked Wi-Fi passwords for one or more routers.

        Requires router: a single router id, or a list of router ids.
        Optional filters: sort, limit.
        """
        try:
            err = validate_required_params(router=router)
            if err is not None:
                return err
            kwargs = {}
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_unmasked_wifi_passwords(router=router, **kwargs)
            return handle_ncm_response(result, "get_unmasked_wifi_passwords")
        except Exception as e:
            return handle_exception(e, "get_unmasked_wifi_passwords")
