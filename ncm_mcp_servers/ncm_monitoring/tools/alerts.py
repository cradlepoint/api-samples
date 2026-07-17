"""MCP tools for NCM alerts and logs.

Consolidates alert/log queries into:
- get_logs: Unified log retrieval (alerts, recent_alerts, router_logs, activity_logs)
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register alert and log tools."""

    @mcp.tool()
    def get_logs(
        source: str = None,
        router: Optional[int] = None,
        alert_type: Optional[str] = None,
        actor: Optional[str] = None,
        action_type: Optional[str] = None,
        created_at__gt: Optional[str] = None,
        created_at__lt: Optional[str] = None,
        tzoffset_hrs: Optional[int] = 0,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve alerts or logs from various sources.

        Args:
            source: One of "alerts", "recent_alerts", "router_logs",
                or "activity_logs".
                - alerts: Router alerts with date/type filtering.
                - recent_alerts: Alerts from the last 24 hours.
                - router_logs: Device logs for a specific router.
                - activity_logs: NCM platform activity logs.
            router: Filter by router ID (alerts, recent_alerts, router_logs).
            alert_type: Filter by alert type (alerts only).
            actor: Filter by actor ID (activity_logs only).
            action_type: Filter by action type (activity_logs only).
            created_at__gt: Start date filter (ISO 8601).
            created_at__lt: End date filter (ISO 8601).
            tzoffset_hrs: Timezone offset in hours (recent_alerts only).
            limit: Max results to return.
        """
        try:
            err = validate_required_params(source=source)
            if err is not None:
                return err

            if source == "alerts":
                kwargs = {}
                if router is not None:
                    kwargs["router"] = router
                if alert_type is not None:
                    kwargs["type"] = alert_type
                if created_at__gt is not None:
                    kwargs["created_at__gt"] = created_at__gt
                if created_at__lt is not None:
                    kwargs["created_at__lt"] = created_at__lt
                if limit is not None:
                    kwargs["limit"] = limit
                result = client.get_router_alerts(**kwargs)

            elif source == "recent_alerts":
                kwargs = {}
                if router is not None:
                    kwargs["router"] = router
                result = client.get_router_alerts_last_24hrs(
                    tzoffset_hrs=tzoffset_hrs, **kwargs
                )

            elif source == "router_logs":
                err = validate_required_params(router=router)
                if err is not None:
                    return err
                kwargs = {}
                if created_at__gt is not None:
                    kwargs["created_at__gt"] = created_at__gt
                if created_at__lt is not None:
                    kwargs["created_at__lt"] = created_at__lt
                if limit is not None:
                    kwargs["limit"] = limit
                result = client.get_router_logs(router, **kwargs)

            elif source == "activity_logs":
                kwargs = {}
                if actor is not None:
                    kwargs["actor__id"] = actor
                if action_type is not None:
                    kwargs["action__type"] = action_type
                if created_at__gt is not None:
                    kwargs["created_at__gt"] = created_at__gt
                if created_at__lt is not None:
                    kwargs["created_at__lt"] = created_at__lt
                if limit is not None:
                    kwargs["limit"] = limit
                result = client.get_activity_logs(**kwargs)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid source",
                        "details": (
                            "Valid sources: alerts, recent_alerts, "
                            "router_logs, activity_logs"
                        ),
                    },
                    "operation": "get_logs",
                }

            return handle_ncm_response(result, "get_logs")
        except Exception as e:
            return handle_exception(e, "get_logs")
