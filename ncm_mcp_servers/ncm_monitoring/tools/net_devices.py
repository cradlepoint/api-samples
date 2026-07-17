"""MCP tools for NCM net device monitoring.

Consolidates net device metrics into:
- get_net_devices: Query/list net devices
- get_net_device_health: Get cellular health scores
- get_net_device_metrics: Unified metrics retrieval (signal, usage, wan, modem)
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register net device monitoring tools."""

    @mcp.tool()
    def get_net_devices(
        router: Optional[int] = None,
        mode: Optional[str] = None,
        connection_state: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve net devices with optional filtering by router, mode, or connection state."""
        try:
            kwargs = {}
            if router is not None:
                kwargs["router"] = router
            if mode is not None:
                kwargs["mode"] = mode
            if connection_state is not None:
                kwargs["connection_state"] = connection_state
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_net_devices(**kwargs)
            return handle_ncm_response(result, "get_net_devices")
        except Exception as e:
            return handle_exception(e, "get_net_devices")

    @mcp.tool()
    def get_net_device_health(
        net_device: Optional[int] = None,
    ) -> dict:
        """Retrieve cellular health scores, optionally filtered by net device ID."""
        try:
            kwargs = {}
            if net_device is not None:
                kwargs["net_device"] = net_device
            result = client.get_net_device_health(**kwargs)
            return handle_ncm_response(result, "get_net_device_health")
        except Exception as e:
            return handle_exception(e, "get_net_device_health")

    @mcp.tool()
    def get_net_device_metrics(
        metric_type: str = None,
        net_device: Optional[int] = None,
        created_at__gt: Optional[str] = None,
        created_at__lt: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve net device metrics by type.

        Args:
            metric_type: One of "signal", "usage", "wan", or "modem".
                - signal: Signal strength samples over time.
                - usage: Data usage samples over time.
                - wan: Latest signal/usage metrics for WAN devices.
                - modem: Latest signal/usage metrics for modem devices.
            net_device: Filter by net device ID.
            created_at__gt: Start date (ISO 8601). For signal/usage only.
            created_at__lt: End date (ISO 8601). For signal/usage only.
            limit: Max results to return.
        """
        try:
            err = validate_required_params(metric_type=metric_type)
            if err is not None:
                return err

            kwargs = {}
            if net_device is not None:
                kwargs["net_device"] = net_device
            if limit is not None:
                kwargs["limit"] = limit

            if metric_type == "signal":
                if created_at__gt is not None:
                    kwargs["created_at__gt"] = created_at__gt
                if created_at__lt is not None:
                    kwargs["created_at__lt"] = created_at__lt
                result = client.get_net_device_signal_samples(**kwargs)

            elif metric_type == "usage":
                if created_at__gt is not None:
                    kwargs["created_at__gt"] = created_at__gt
                if created_at__lt is not None:
                    kwargs["created_at__lt"] = created_at__lt
                result = client.get_net_device_usage_samples(**kwargs)

            elif metric_type == "wan":
                result = client.get_net_devices_metrics_for_wan(**kwargs)

            elif metric_type == "modem":
                result = client.get_net_devices_metrics_for_mdm(**kwargs)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid metric_type",
                        "details": "Valid types: signal, usage, wan, modem",
                    },
                    "operation": "get_net_device_metrics",
                }

            return handle_ncm_response(result, "get_net_device_metrics")
        except Exception as e:
            return handle_exception(e, "get_net_device_metrics")
