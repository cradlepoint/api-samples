"""MCP tools for NCM LAN management.

Provides:
- get_lan_devices: Query LAN devices
- get_lan_product_infos: Query LAN product infos
- get_lan_manager_options: Query LAN manager options
- manage_lan_manager_option: Create/update a LAN manager option
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register LAN management tools."""

    @mcp.tool()
    def get_lan_devices(
        device_id: Optional[str] = None,
        account: Optional[str] = None,
        device_status: Optional[str] = None,
        group: Optional[str] = None,
        lan_firmware_upgrade_status: Optional[str] = None,
        lan_product_info: Optional[str] = None,
        mac_address: Optional[str] = None,
        name: Optional[str] = None,
        router: Optional[str] = None,
        serial_number: Optional[str] = None,
        device_type: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve LAN devices, or a single device when device_id is set.

        Optional filters (list form): account, device_status, group,
        lan_firmware_upgrade_status, lan_product_info, mac_address, name,
        router, serial_number, device_type (mapped to the ``type`` filter),
        sort, limit.
        """
        try:
            kwargs = {}
            if account is not None:
                kwargs["account"] = account
            if device_status is not None:
                kwargs["device_status"] = device_status
            if group is not None:
                kwargs["group"] = group
            if lan_firmware_upgrade_status is not None:
                kwargs["lan_firmware_upgrade_status"] = lan_firmware_upgrade_status
            if lan_product_info is not None:
                kwargs["lan_product_info"] = lan_product_info
            if mac_address is not None:
                kwargs["mac_address"] = mac_address
            if name is not None:
                kwargs["name"] = name
            if router is not None:
                kwargs["router"] = router
            if serial_number is not None:
                kwargs["serial_number"] = serial_number
            if device_type is not None:
                kwargs["type"] = device_type
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_lan_devices(device_id=device_id, **kwargs)
            return handle_ncm_response(result, "get_lan_devices")
        except Exception as e:
            return handle_exception(e, "get_lan_devices")

    @mcp.tool()
    def get_lan_product_infos(
        product_info_id: Optional[str] = None,
        name: Optional[str] = None,
        product_type: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve LAN product infos, or one when product_info_id is set.

        Optional filters (list form): name, product_type, sort, limit.
        """
        try:
            kwargs = {}
            if name is not None:
                kwargs["name"] = name
            if product_type is not None:
                kwargs["product_type"] = product_type
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_lan_product_infos(
                product_info_id=product_info_id, **kwargs
            )
            return handle_ncm_response(result, "get_lan_product_infos")
        except Exception as e:
            return handle_exception(e, "get_lan_product_infos")

    @mcp.tool()
    def get_lan_manager_options(
        option_id: Optional[str] = None,
        enabled: Optional[bool] = None,
        router: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve LAN manager options, or one when option_id is set.

        Optional filters (list form): enabled, router, sort, limit.
        """
        try:
            kwargs = {}
            if enabled is not None:
                kwargs["enabled"] = enabled
            if router is not None:
                kwargs["router"] = router
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_lan_manager_options(option_id=option_id, **kwargs)
            return handle_ncm_response(result, "get_lan_manager_options")
        except Exception as e:
            return handle_exception(e, "get_lan_manager_options")

    @mcp.tool()
    def manage_lan_manager_option(
        action: str = None,
        option_id: Optional[str] = None,
        enabled: Optional[bool] = None,
        router_id: Optional[str] = None,
        account_id: Optional[str] = None,
        attributes: Optional[dict] = None,
        relationships: Optional[dict] = None,
    ) -> dict:
        """Manage LAN manager option operations.

        Actions:
        - "create": Create a LAN manager option. Requires enabled and
          router_id. Optional: account_id.
        - "update": Update a LAN manager option. Requires option_id.
          Optional: attributes, relationships (JSON:API dicts).
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(
                    enabled=enabled, router_id=router_id
                )
                if err is not None:
                    return err
                result = client.create_lan_manager_option(
                    enabled, router_id, account_id=account_id
                )

            elif action == "update":
                err = validate_required_params(option_id=option_id)
                if err is not None:
                    return err
                kwargs = {}
                if attributes is not None:
                    kwargs["attributes"] = attributes
                if relationships is not None:
                    kwargs["relationships"] = relationships
                result = client.update_lan_manager_option(option_id, **kwargs)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create, update",
                    },
                    "operation": "manage_lan_manager_option",
                }

            return handle_ncm_response(result, "manage_lan_manager_option")
        except Exception as e:
            return handle_exception(e, "manage_lan_manager_option")
