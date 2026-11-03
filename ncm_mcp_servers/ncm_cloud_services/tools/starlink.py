"""MCP tools for NCM Starlink interface management.

Provides:
- get_starlink_interfaces: Query Starlink interfaces
- get_starlink_interface_reboots: Query interface reboots
- get_starlink_interface_stows: Query interface stows
- get_starlink_diagnostics: Query Starlink diagnostics
- manage_starlink_interface: Request a reboot or stow/unstow
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register Starlink interface management tools."""

    @mcp.tool()
    def get_starlink_interfaces(
        interface_id: Optional[str] = None,
        carrier: Optional[str] = None,
        gateway_ip: Optional[str] = None,
        net_device: Optional[str] = None,
        port: Optional[str] = None,
        software_version: Optional[str] = None,
        terminal_identifier: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve Starlink interfaces, or one when interface_id is set.

        Optional filters (list form): carrier, gateway_ip, net_device, port,
        software_version, terminal_identifier, sort, limit.
        """
        try:
            kwargs = {}
            if carrier is not None:
                kwargs["carrier"] = carrier
            if gateway_ip is not None:
                kwargs["gateway_ip"] = gateway_ip
            if net_device is not None:
                kwargs["net_device"] = net_device
            if port is not None:
                kwargs["port"] = port
            if software_version is not None:
                kwargs["software_version"] = software_version
            if terminal_identifier is not None:
                kwargs["terminal_identifier"] = terminal_identifier
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_starlink_interfaces(
                interface_id=interface_id, **kwargs
            )
            return handle_ncm_response(result, "get_starlink_interfaces")
        except Exception as e:
            return handle_exception(e, "get_starlink_interfaces")

    @mcp.tool()
    def get_starlink_interface_reboots(
        reboot_id: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve Starlink interface reboots, or one when reboot_id is set.

        Optional filters (list form): sort, limit.
        """
        try:
            kwargs = {}
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_starlink_interface_reboots(
                reboot_id=reboot_id, **kwargs
            )
            return handle_ncm_response(result, "get_starlink_interface_reboots")
        except Exception as e:
            return handle_exception(e, "get_starlink_interface_reboots")

    @mcp.tool()
    def get_starlink_interface_stows(
        stow_id: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve Starlink interface stows, or one when stow_id is set.

        Optional filters (list form): sort, limit.
        """
        try:
            kwargs = {}
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_starlink_interface_stows(
                stow_id=stow_id, **kwargs
            )
            return handle_ncm_response(result, "get_starlink_interface_stows")
        except Exception as e:
            return handle_exception(e, "get_starlink_interface_stows")

    @mcp.tool()
    def get_starlink_diagnostics(
        diagnostics_id: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve Starlink diagnostics, or one when diagnostics_id is set.

        Optional filters (list form): sort, limit.
        """
        try:
            kwargs = {}
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_starlink_diagnostics(
                diagnostics_id=diagnostics_id, **kwargs
            )
            return handle_ncm_response(result, "get_starlink_diagnostics")
        except Exception as e:
            return handle_exception(e, "get_starlink_diagnostics")

    @mcp.tool()
    def manage_starlink_interface(
        action: str = None,
        interface_id: Optional[str] = None,
        stow_action: Optional[str] = None,
    ) -> dict:
        """Manage Starlink interface operations.

        Actions:
        - "reboot": Request a reboot of an interface. Requires interface_id.
        - "stow": Request a stow or unstow. Requires interface_id and
          stow_action (one of "stow" or "unstow").
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "reboot":
                err = validate_required_params(interface_id=interface_id)
                if err is not None:
                    return err
                result = client.create_starlink_interface_reboot(interface_id)

            elif action == "stow":
                err = validate_required_params(
                    interface_id=interface_id, stow_action=stow_action
                )
                if err is not None:
                    return err
                result = client.create_starlink_interface_stow(
                    interface_id, stow_action
                )

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: reboot, stow",
                    },
                    "operation": "manage_starlink_interface",
                }

            return handle_ncm_response(result, "manage_starlink_interface")
        except Exception as e:
            return handle_exception(e, "manage_starlink_interface")
