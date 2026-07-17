"""MCP tools for NCM user management.

Consolidates user CRUD into:
- get_users: Query/list users
- manage_user: Create, update, delete, change role
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register user management tools."""

    @mcp.tool()
    def get_users(
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve NCM users with optional filtering by email, name, or active status."""
        try:
            kwargs = {}
            if email is not None:
                kwargs["email"] = email
            if first_name is not None:
                kwargs["first_name"] = first_name
            if last_name is not None:
                kwargs["last_name"] = last_name
            if is_active is not None:
                kwargs["is_active"] = is_active
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_users(**kwargs)
            return handle_ncm_response(result, "get_users")
        except Exception as e:
            return handle_exception(e, "get_users")

    @mcp.tool()
    def manage_user(
        action: str = None,
        email: str = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        new_role: Optional[str] = None,
    ) -> dict:
        """Manage NCM user lifecycle operations.

        Actions:
        - "create": Create a new user. Requires email, first_name, last_name.
        - "update": Update user details. Requires email + any of
          first_name, last_name, is_active.
        - "delete": Delete a user. Requires email.
        - "change_role": Change user role. Requires email + new_role.
        """
        try:
            err = validate_required_params(action=action, email=email)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(
                    first_name=first_name, last_name=last_name
                )
                if err is not None:
                    return err
                result = client.create_user(email, first_name, last_name)

            elif action == "update":
                kwargs = {}
                if first_name is not None:
                    kwargs["first_name"] = first_name
                if last_name is not None:
                    kwargs["last_name"] = last_name
                if is_active is not None:
                    kwargs["is_active"] = is_active
                result = client.update_user(email, **kwargs)

            elif action == "delete":
                result = client.delete_user(email)

            elif action == "change_role":
                err = validate_required_params(new_role=new_role)
                if err is not None:
                    return err
                result = client.update_user_role(email, new_role)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create, update, delete, change_role",
                    },
                    "operation": "manage_user",
                }

            return handle_ncm_response(result, "manage_user")
        except Exception as e:
            return handle_exception(e, "manage_user")
