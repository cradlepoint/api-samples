"""MCP tools for NCM speed tests.

Provides:
- create_speed_test: Run speed tests on net devices or all modems on a router
- get_speed_test: Check speed test status/results
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register speed test tools."""

    @mcp.tool()
    def create_speed_test(
        net_device_ids: Optional[list] = None,
        router_id: Optional[int] = None,
        account_id: Optional[int] = None,
        host: Optional[str] = None,
        max_test_concurrency: Optional[int] = None,
        port: Optional[int] = None,
        size: Optional[int] = None,
        test_timeout: Optional[int] = None,
        test_type: Optional[str] = None,
        time: Optional[int] = None,
    ) -> dict:
        """Create a speed test for net devices or all modems on a router.

        Provide either net_device_ids (list of specific device IDs) or
        router_id (auto-discovers all connected modems on that router).

        test_type can be 'TCP Download', 'TCP Upload', or 'TCP Latency'.
        """
        try:
            if net_device_ids is None and router_id is None:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Missing required parameters",
                        "details": "Provide either net_device_ids or router_id",
                    },
                    "operation": "create_speed_test",
                }

            kwargs = {}
            if account_id is not None:
                kwargs["account_id"] = account_id
            if host is not None:
                kwargs["host"] = host
            if max_test_concurrency is not None:
                kwargs["max_test_concurrency"] = max_test_concurrency
            if port is not None:
                kwargs["port"] = port
            if size is not None:
                kwargs["size"] = size
            if test_timeout is not None:
                kwargs["test_timeout"] = test_timeout
            if test_type is not None:
                kwargs["test_type"] = test_type
            if time is not None:
                kwargs["time"] = time

            if net_device_ids is not None:
                result = client.create_speed_test(net_device_ids, **kwargs)
            else:
                result = client.create_speed_test_mdm(router_id, **kwargs)

            return handle_ncm_response(result, "create_speed_test")
        except Exception as e:
            return handle_exception(e, "create_speed_test")

    @mcp.tool()
    def get_speed_test(speed_test_id: int = None) -> dict:
        """Get the status and results of a speed test by its ID."""
        try:
            err = validate_required_params(speed_test_id=speed_test_id)
            if err is not None:
                return err
            result = client.get_speed_test(speed_test_id)
            return handle_ncm_response(result, "get_speed_test")
        except Exception as e:
            return handle_exception(e, "get_speed_test")
