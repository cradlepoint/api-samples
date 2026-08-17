"""MCP tools for NCM subscription and licensing management.

Provides:
- get_subscriptions: Query subscriptions
- manage_subscription: Upgrade/downgrade/unlicense devices
"""

from typing import List, Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register subscription management tools."""

    @mcp.tool()
    def get_subscriptions(
        subscription_id: Optional[str] = None,
        name: Optional[str] = None,
        tenant: Optional[str] = None,
        subscription_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve subscriptions with optional filtering by ID, name, tenant, or type."""
        try:
            kwargs = {}
            if subscription_id is not None:
                kwargs["id"] = subscription_id
            if name is not None:
                kwargs["name"] = name
            if tenant is not None:
                kwargs["tenant"] = tenant
            if subscription_type is not None:
                kwargs["type"] = subscription_type
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_subscriptions(**kwargs)
            return handle_ncm_response(result, "get_subscriptions")
        except Exception as e:
            return handle_exception(e, "get_subscriptions")

    @mcp.tool()
    def manage_subscription(
        action: str = None,
        subscription_id: Optional[str] = None,
        mac: Optional[str] = None,
        mac_addresses: Optional[List[str]] = None,
        regrade_action: Optional[str] = "UPGRADE",
    ) -> dict:
        """Manage device subscriptions and licensing.

        Actions:
        - "regrade": Upgrade or downgrade a device subscription.
          Requires subscription_id + mac. Optional: regrade_action
          ("UPGRADE" or "DOWNGRADE", default "UPGRADE").
        - "unlicense": Remove licenses from devices.
          Requires mac_addresses (list of MAC addresses).
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "regrade":
                err = validate_required_params(
                    subscription_id=subscription_id, mac=mac
                )
                if err is not None:
                    return err
                result = client.regrade(
                    subscription_id, mac, action=regrade_action
                )

            elif action == "unlicense":
                err = validate_required_params(mac_addresses=mac_addresses)
                if err is not None:
                    return err
                result = client.unlicense_devices(mac_addresses)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: regrade, unlicense",
                    },
                    "operation": "manage_subscription",
                }

            return handle_ncm_response(result, "manage_subscription")
        except Exception as e:
            return handle_exception(e, "manage_subscription")
