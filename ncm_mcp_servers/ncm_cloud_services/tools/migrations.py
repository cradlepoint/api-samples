"""MCP tools for NCM organization migration management.

Provides:
- get_migrations: Query organization migration jobs
- manage_migration: Create an organization migration job
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register organization migration management tools."""

    @mcp.tool()
    def get_migrations(
        migration_id: Optional[str] = None,
        source: Optional[str] = None,
        status: Optional[str] = None,
        target: Optional[str] = None,
        migration_type: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve organization migrations, or one when migration_id is set.

        Optional filters (list form): source, status, target, migration_type
        (mapped to the ``type`` filter), sort, limit.
        """
        try:
            kwargs = {}
            if source is not None:
                kwargs["source"] = source
            if status is not None:
                kwargs["status"] = status
            if target is not None:
                kwargs["target"] = target
            if migration_type is not None:
                kwargs["type"] = migration_type
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_migrations(migration_id=migration_id, **kwargs)
            return handle_ncm_response(result, "get_migrations")
        except Exception as e:
            return handle_exception(e, "get_migrations")

    @mcp.tool()
    def manage_migration(
        action: str = None,
        migration_type: Optional[str] = None,
        attributes: Optional[dict] = None,
        relationships: Optional[dict] = None,
    ) -> dict:
        """Manage organization migration operations.

        Actions:
        - "create": Create a migration job. Requires migration_type, one of
          create_organizations, elevate_organizations, merge_organizations.
          create_organizations / elevate_organizations require attributes
          (organization_name, idle_timeout, enhanced_login_security_enabled,
          mfa_required) and relationships (organization_administrator; account
          also required for elevate). merge_organizations requires the
          source_tenant relationship.
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(migration_type=migration_type)
                if err is not None:
                    return err
                result = client.create_migration(
                    migration_type,
                    attributes=attributes,
                    relationships=relationships,
                )

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create",
                    },
                    "operation": "manage_migration",
                }

            return handle_ncm_response(result, "manage_migration")
        except Exception as e:
            return handle_exception(e, "manage_migration")
