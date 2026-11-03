"""MCP tools for NCM modem upgrade management.

Provides:
- get_modem_software_versions: Query available modem software versions
- get_modem_upgrades: Query modem upgrade jobs
- manage_modem_upgrade: Create/update a modem upgrade job
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register modem upgrade management tools."""

    @mcp.tool()
    def get_modem_software_versions(
        group: str = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve available modem software versions.

        Requires group (mapped to the required filter[group] query parameter).
        Optional filters: sort, limit.
        """
        try:
            err = validate_required_params(group=group)
            if err is not None:
                return err
            kwargs = {}
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_modem_software_versions(group=group, **kwargs)
            return handle_ncm_response(result, "get_modem_software_versions")
        except Exception as e:
            return handle_exception(e, "get_modem_software_versions")

    @mcp.tool()
    def get_modem_upgrades(
        modem_upgrade_id: Optional[str] = None,
        group: Optional[str] = None,
        upgrade_type: Optional[str] = None,
        modem_upgrade_parent: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve modem upgrade jobs, or one when modem_upgrade_id is set.

        The list form requires BOTH group and upgrade_type (mapped to the
        required filter[group] and filter[type] query parameters). Optional
        filters: modem_upgrade_parent, sort, limit.
        """
        try:
            kwargs = {}
            if modem_upgrade_parent is not None:
                kwargs["modem_upgrade_parent"] = modem_upgrade_parent
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_modem_upgrades(
                modem_upgrade_id=modem_upgrade_id,
                group=group,
                upgrade_type=upgrade_type,
                **kwargs,
            )
            return handle_ncm_response(result, "get_modem_upgrades")
        except Exception as e:
            return handle_exception(e, "get_modem_upgrades")

    @mcp.tool()
    def manage_modem_upgrade(
        action: str = None,
        modem_upgrade_id: Optional[str] = None,
        carrier: Optional[str] = None,
        modem_type_name: Optional[str] = None,
        operation: Optional[str] = None,
        group_id: Optional[str] = None,
        attributes: Optional[dict] = None,
    ) -> dict:
        """Manage modem upgrade operations.

        Actions:
        - "create": Create a modem upgrade job. Requires carrier,
          modem_type_name, operation, group_id. Optional: attributes, whose
          keys are merged into the request body's attributes (e.g. overwrite,
          connection_states).
        - "update": Update a modem upgrade job. Requires modem_upgrade_id.
          Optional: attributes, merged into the request body's attributes.
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(
                    carrier=carrier,
                    modem_type_name=modem_type_name,
                    operation=operation,
                    group_id=group_id,
                )
                if err is not None:
                    return err
                kwargs = dict(attributes) if attributes else {}
                result = client.create_modem_upgrade(
                    carrier, modem_type_name, operation, group_id, **kwargs
                )

            elif action == "update":
                err = validate_required_params(modem_upgrade_id=modem_upgrade_id)
                if err is not None:
                    return err
                kwargs = dict(attributes) if attributes else {}
                result = client.update_modem_upgrade(modem_upgrade_id, **kwargs)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create, update",
                    },
                    "operation": "manage_modem_upgrade",
                }

            return handle_ncm_response(result, "manage_modem_upgrade")
        except Exception as e:
            return handle_exception(e, "manage_modem_upgrade")
