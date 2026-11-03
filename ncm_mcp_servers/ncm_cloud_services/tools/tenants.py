"""MCP tools for NCM tenant management.

Provides:
- get_tenants: Query tenants
- get_tenant_authorizations: Query tenant authorizations
- manage_tenant_authorization: Update a tenant authorization
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register tenant management tools."""

    @mcp.tool()
    def get_tenants(
        tenant_id: Optional[str] = None,
        name: Optional[str] = None,
        tenant_type: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve tenants, or a single tenant when tenant_id is provided.

        Optional filters (list form only): name, tenant_type (mapped to the
        API ``type`` filter), sort, limit.
        """
        try:
            kwargs = {}
            if name is not None:
                kwargs["name"] = name
            if tenant_type is not None:
                kwargs["type"] = tenant_type
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_tenants(tenant_id=tenant_id, **kwargs)
            return handle_ncm_response(result, "get_tenants")
        except Exception as e:
            return handle_exception(e, "get_tenants")

    @mcp.tool()
    def get_tenant_authorizations(
        authorization_id: Optional[str] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve tenant authorizations, or a single one when authorization_id is set.

        Optional filters (list form only): search, sort, limit.
        """
        try:
            kwargs = {}
            if search is not None:
                kwargs["search"] = search
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_tenant_authorizations(
                authorization_id=authorization_id, **kwargs
            )
            return handle_ncm_response(result, "get_tenant_authorizations")
        except Exception as e:
            return handle_exception(e, "get_tenant_authorizations")

    @mcp.tool()
    def manage_tenant_authorization(
        action: str = None,
        authorization_id: Optional[str] = None,
        role: Optional[str] = None,
        tenant_authorization: Optional[dict] = None,
    ) -> dict:
        """Manage tenant authorization operations.

        Actions:
        - "update": Update a tenant authorization. Requires authorization_id.
          Supply either role (builds a minimal body) or tenant_authorization
          (a full JSON:API document sent verbatim).
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "update":
                err = validate_required_params(authorization_id=authorization_id)
                if err is not None:
                    return err
                result = client.update_tenant_authorization(
                    authorization_id,
                    role=role,
                    tenant_authorization=tenant_authorization,
                )

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: update",
                    },
                    "operation": "manage_tenant_authorization",
                }

            return handle_ncm_response(result, "manage_tenant_authorization")
        except Exception as e:
            return handle_exception(e, "manage_tenant_authorization")
