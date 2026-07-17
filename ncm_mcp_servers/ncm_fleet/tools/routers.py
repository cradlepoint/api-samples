"""MCP tools for NCM router management.

Consolidates router CRUD operations into:
- get_routers: Query/list routers
- manage_router: Create, rename, delete, update fields, assign/remove from group/account
- reboot_router: Reboot a single router
- reboot_group: Reboot all routers in a group
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register router management tools."""

    @mcp.tool()
    def get_routers(
        router_id: Optional[int] = None,
        name: Optional[str] = None,
        account: Optional[str] = None,
        group: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve routers with optional filtering by ID, name, account, or group."""
        try:
            kwargs = {}
            if router_id is not None:
                kwargs["id"] = router_id
            if name is not None:
                kwargs["name"] = name
            if account is not None:
                kwargs["account"] = account
            if group is not None:
                kwargs["group"] = group
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_routers(**kwargs)
            return handle_ncm_response(result, "get_routers")
        except Exception as e:
            return handle_exception(e, "get_routers")

    @mcp.tool()
    def manage_router(
        action: str = None,
        router_id: Optional[int] = None,
        router_name: Optional[str] = None,
        new_name: Optional[str] = None,
        description: Optional[str] = None,
        asset_id: Optional[str] = None,
        custom1: Optional[str] = None,
        custom2: Optional[str] = None,
        group_id: Optional[int] = None,
        account_id: Optional[int] = None,
    ) -> dict:
        """Manage router lifecycle operations.

        Actions:
        - "rename": Rename a router. Requires router_id or router_name + new_name.
        - "delete": Delete a router. Requires router_id or router_name.
        - "update": Update router fields. Requires router_id + any of
          new_name, description, asset_id, custom1, custom2.
        - "assign_to_group": Assign router to group. Requires router_id + group_id.
        - "remove_from_group": Remove router from group. Requires router_id or router_name.
        - "assign_to_account": Move router to account. Requires router_id + account_id.
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "rename":
                err = validate_required_params(new_name=new_name)
                if err is not None:
                    return err
                if router_id is None and router_name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either router_id or router_name",
                        },
                        "operation": "manage_router",
                    }
                if router_id is not None:
                    result = client.rename_router_by_id(router_id, new_name)
                else:
                    result = client.rename_router_by_name(router_name, new_name)

            elif action == "delete":
                if router_id is None and router_name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either router_id or router_name",
                        },
                        "operation": "manage_router",
                    }
                if router_id is not None:
                    result = client.delete_router_by_id(router_id)
                else:
                    result = client.delete_router_by_name(router_name)

            elif action == "update":
                err = validate_required_params(router_id=router_id)
                if err is not None:
                    return err
                kwargs = {}
                if new_name is not None:
                    kwargs["name"] = new_name
                if description is not None:
                    kwargs["description"] = description
                if asset_id is not None:
                    kwargs["asset_id"] = asset_id
                if custom1 is not None:
                    kwargs["custom1"] = custom1
                if custom2 is not None:
                    kwargs["custom2"] = custom2
                result = client.set_router_fields(router_id, **kwargs)

            elif action == "assign_to_group":
                err = validate_required_params(router_id=router_id, group_id=group_id)
                if err is not None:
                    return err
                result = client.assign_router_to_group(router_id, group_id)

            elif action == "remove_from_group":
                if router_id is None and router_name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either router_id or router_name",
                        },
                        "operation": "manage_router",
                    }
                result = client.remove_router_from_group(
                    router_id=router_id, router_name=router_name
                )

            elif action == "assign_to_account":
                err = validate_required_params(router_id=router_id, account_id=account_id)
                if err is not None:
                    return err
                result = client.assign_router_to_account(router_id, account_id)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": (
                            "Valid actions: rename, delete, update, "
                            "assign_to_group, remove_from_group, assign_to_account"
                        ),
                    },
                    "operation": "manage_router",
                }

            return handle_ncm_response(result, "manage_router")
        except Exception as e:
            return handle_exception(e, "manage_router")

    @mcp.tool()
    def reboot_router(router_id: int = None) -> dict:
        """Reboot a single router by its ID."""
        try:
            err = validate_required_params(router_id=router_id)
            if err is not None:
                return err
            result = client.reboot_device(router_id)
            return handle_ncm_response(result, "reboot_router")
        except Exception as e:
            return handle_exception(e, "reboot_router")

    @mcp.tool()
    def reboot_group(group_id: int = None) -> dict:
        """Reboot all routers in a group by group ID."""
        try:
            err = validate_required_params(group_id=group_id)
            if err is not None:
                return err
            result = client.reboot_group(group_id)
            return handle_ncm_response(result, "reboot_group")
        except Exception as e:
            return handle_exception(e, "reboot_group")
