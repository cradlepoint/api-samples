"""MCP tools for NCM location management.

Consolidates location operations into:
- get_locations: Query current and historical locations
- manage_location: Create or delete locations
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register location management tools."""

    @mcp.tool()
    def get_locations(
        router: Optional[int] = None,
        historical: bool = False,
        created_at__gt: Optional[str] = None,
        created_at__lte: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve current or historical locations for routers.

        Args:
            router: Filter by router ID.
            historical: If True, retrieves historical location data (requires router).
            created_at__gt: Start date filter (ISO 8601). Only for historical.
            created_at__lte: End date filter (ISO 8601). Only for historical.
            limit: Max number of results to return.
        """
        try:
            if historical:
                err = validate_required_params(router=router)
                if err is not None:
                    return err
                kwargs = {}
                if created_at__gt is not None:
                    kwargs["created_at__gt"] = created_at__gt
                if created_at__lte is not None:
                    kwargs["created_at__lte"] = created_at__lte
                if limit is not None:
                    kwargs["limit"] = limit
                result = client.get_historical_locations(router, **kwargs)
            else:
                kwargs = {}
                if router is not None:
                    kwargs["router"] = router
                if limit is not None:
                    kwargs["limit"] = limit
                result = client.get_locations(**kwargs)
            return handle_ncm_response(result, "get_locations")
        except Exception as e:
            return handle_exception(e, "get_locations")

    @mcp.tool()
    def manage_location(
        action: str = None,
        router_id: int = None,
        account_id: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> dict:
        """Manage router location assignments.

        Actions:
        - "create": Create and assign a location. Requires router_id,
          account_id, latitude, longitude.
        - "delete": Remove the location from a router. Requires router_id.
        """
        try:
            err = validate_required_params(action=action, router_id=router_id)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(
                    account_id=account_id,
                    latitude=latitude,
                    longitude=longitude,
                )
                if err is not None:
                    return err
                result = client.create_location(
                    account_id, latitude, longitude, router_id
                )

            elif action == "delete":
                result = client.delete_location_for_router(router_id)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create, delete",
                    },
                    "operation": "manage_location",
                }

            return handle_ncm_response(result, "manage_location")
        except Exception as e:
            return handle_exception(e, "manage_location")
