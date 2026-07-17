"""MCP tools for NCM group management.

Consolidates group CRUD operations into:
- get_groups: Query/list groups
- manage_group: Create, rename, delete, update
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register group management tools."""

    @mcp.tool()
    def get_groups(
        group_id: Optional[int] = None,
        name: Optional[str] = None,
        account: Optional[str] = None,
    ) -> dict:
        """Retrieve groups with optional filtering by ID, name, or account."""
        try:
            kwargs = {}
            if group_id is not None:
                kwargs["id"] = group_id
            if name is not None:
                kwargs["name"] = name
            if account is not None:
                kwargs["account"] = account
            result = client.get_groups(**kwargs)
            return handle_ncm_response(result, "get_groups")
        except Exception as e:
            return handle_exception(e, "get_groups")

    @mcp.tool()
    def manage_group(
        action: str = None,
        group_id: Optional[int] = None,
        group_name: Optional[str] = None,
        new_name: Optional[str] = None,
        parent_account_id: Optional[int] = None,
        parent_account_name: Optional[str] = None,
        product_name: Optional[str] = None,
        firmware_version: Optional[str] = None,
        product: Optional[str] = None,
        target_firmware: Optional[str] = None,
        configuration: Optional[dict] = None,
    ) -> dict:
        """Manage group lifecycle operations.

        Actions:
        - "create": Create a new group. Requires group_name +
          (parent_account_id or parent_account_name). Optional: product_name, firmware_version.
        - "rename": Rename a group. Requires (group_id or group_name) + new_name.
        - "delete": Delete a group. Requires group_id or group_name.
        - "update": Update group fields. Requires group_id.
          Optional: new_name, product, target_firmware, configuration.
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(group_name=group_name)
                if err is not None:
                    return err
                if parent_account_id is None and parent_account_name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either parent_account_id or parent_account_name",
                        },
                        "operation": "manage_group",
                    }
                if parent_account_id is not None:
                    result = client.create_group_by_parent_id(
                        parent_account_id, group_name, product_name, firmware_version
                    )
                else:
                    result = client.create_group_by_parent_name(
                        parent_account_name, group_name, product_name, firmware_version
                    )

            elif action == "rename":
                err = validate_required_params(new_name=new_name)
                if err is not None:
                    return err
                if group_id is None and group_name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either group_id or group_name",
                        },
                        "operation": "manage_group",
                    }
                if group_id is not None:
                    result = client.rename_group_by_id(group_id, new_name)
                else:
                    result = client.rename_group_by_name(group_name, new_name)

            elif action == "delete":
                if group_id is None and group_name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either group_id or group_name",
                        },
                        "operation": "manage_group",
                    }
                if group_id is not None:
                    result = client.delete_group_by_id(group_id)
                else:
                    result = client.delete_group_by_name(group_name)

            elif action == "update":
                err = validate_required_params(group_id=group_id)
                if err is not None:
                    return err
                kwargs = {}
                if new_name is not None:
                    kwargs["name"] = new_name
                if product is not None:
                    kwargs["product"] = product
                if target_firmware is not None:
                    kwargs["target_firmware"] = target_firmware
                if configuration is not None:
                    kwargs["configuration"] = configuration
                result = client.patch_group(group_id, **kwargs)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create, rename, delete, update",
                    },
                    "operation": "manage_group",
                }

            return handle_ncm_response(result, "manage_group")
        except Exception as e:
            return handle_exception(e, "manage_group")
