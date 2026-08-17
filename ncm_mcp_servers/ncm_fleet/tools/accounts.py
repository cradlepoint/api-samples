"""MCP tools for NCM account management.

Consolidates account CRUD operations into:
- get_accounts: Query/list accounts
- manage_subaccount: Create, rename, delete subaccounts
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register account management tools."""

    @mcp.tool()
    def get_accounts(
        account_id: Optional[int] = None,
        name: Optional[str] = None,
    ) -> dict:
        """Retrieve accounts with optional filtering by ID or name."""
        try:
            kwargs = {}
            if account_id is not None:
                kwargs["id"] = account_id
            if name is not None:
                kwargs["name"] = name
            result = client.get_accounts(**kwargs)
            return handle_ncm_response(result, "get_accounts")
        except Exception as e:
            return handle_exception(e, "get_accounts")

    @mcp.tool()
    def manage_subaccount(
        action: str = None,
        subaccount_id: Optional[int] = None,
        subaccount_name: Optional[str] = None,
        new_name: Optional[str] = None,
        parent_account_id: Optional[int] = None,
        parent_account_name: Optional[str] = None,
    ) -> dict:
        """Manage subaccount lifecycle operations.

        Actions:
        - "create": Create a subaccount. Requires new_name +
          (parent_account_id or parent_account_name).
        - "rename": Rename a subaccount. Requires (subaccount_id or subaccount_name)
          + new_name.
        - "delete": Delete a subaccount. Requires subaccount_id or subaccount_name.
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(new_name=new_name)
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
                        "operation": "manage_subaccount",
                    }
                if parent_account_id is not None:
                    result = client.create_subaccount_by_parent_id(
                        parent_account_id, new_name
                    )
                else:
                    result = client.create_subaccount_by_parent_name(
                        parent_account_name, new_name
                    )

            elif action == "rename":
                err = validate_required_params(new_name=new_name)
                if err is not None:
                    return err
                if subaccount_id is None and subaccount_name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either subaccount_id or subaccount_name",
                        },
                        "operation": "manage_subaccount",
                    }
                if subaccount_id is not None:
                    result = client.rename_subaccount_by_id(subaccount_id, new_name)
                else:
                    result = client.rename_subaccount_by_name(
                        subaccount_name, new_name
                    )

            elif action == "delete":
                if subaccount_id is None and subaccount_name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either subaccount_id or subaccount_name",
                        },
                        "operation": "manage_subaccount",
                    }
                if subaccount_id is not None:
                    result = client.delete_subaccount_by_id(subaccount_id)
                else:
                    result = client.delete_subaccount_by_name(subaccount_name)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create, rename, delete",
                    },
                    "operation": "manage_subaccount",
                }

            return handle_ncm_response(result, "manage_subaccount")
        except Exception as e:
            return handle_exception(e, "manage_subaccount")
