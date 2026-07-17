"""MCP tools for NCM private cellular network management.

Consolidates private cellular operations into:
- get_networks: Query private cellular networks
- manage_network: Create, update, delete networks
- get_radios: Query radios and their statuses
- manage_radio: Update radio settings
- manage_sim: Query and update SIMs
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register private cellular management tools."""

    @mcp.tool()
    def get_networks(
        network_id: Optional[str] = None,
        name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve private cellular networks with optional filtering."""
        try:
            if network_id is not None:
                result = client.get_private_cellular_network(network_id)
                return handle_ncm_response(result, "get_networks")
            kwargs = {}
            if name is not None:
                kwargs["name"] = name
            if status is not None:
                kwargs["status"] = status
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_private_cellular_networks(**kwargs)
            return handle_ncm_response(result, "get_networks")
        except Exception as e:
            return handle_exception(e, "get_networks")

    @mcp.tool()
    def manage_network(
        action: str = None,
        network_id: Optional[str] = None,
        name: Optional[str] = None,
        core_ip: Optional[str] = None,
        ha_enabled: Optional[bool] = None,
        mobility_gateway_virtual_ip: Optional[str] = None,
        mobility_gateways: Optional[str] = None,
    ) -> dict:
        """Manage private cellular network lifecycle.

        Actions:
        - "create": Create a network. Requires name + core_ip.
          Optional: ha_enabled, mobility_gateway_virtual_ip, mobility_gateways.
        - "update": Update a network. Requires network_id or name.
          Optional: core_ip, ha_enabled, mobility_gateway_virtual_ip.
        - "delete": Delete a network. Requires network_id.
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(name=name, core_ip=core_ip)
                if err is not None:
                    return err
                result = client.create_private_cellular_network(
                    name,
                    core_ip,
                    ha_enabled=ha_enabled if ha_enabled is not None else False,
                    mobility_gateway_virtual_ip=mobility_gateway_virtual_ip,
                    mobility_gateways=mobility_gateways,
                )

            elif action == "update":
                if network_id is None and name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either network_id or name",
                        },
                        "operation": "manage_network",
                    }
                kwargs = {}
                if core_ip is not None:
                    kwargs["core_ip"] = core_ip
                if ha_enabled is not None:
                    kwargs["ha_enabled"] = ha_enabled
                if mobility_gateway_virtual_ip is not None:
                    kwargs["mobility_gateway_virtual_ip"] = mobility_gateway_virtual_ip
                result = client.update_private_cellular_network(
                    id=network_id, name=name, **kwargs
                )

            elif action == "delete":
                err = validate_required_params(network_id=network_id)
                if err is not None:
                    return err
                result = client.delete_private_cellular_network(network_id)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create, update, delete",
                    },
                    "operation": "manage_network",
                }

            return handle_ncm_response(result, "manage_network")
        except Exception as e:
            return handle_exception(e, "manage_network")

    @mcp.tool()
    def get_radios(
        radio_id: Optional[str] = None,
        network: Optional[str] = None,
        name: Optional[str] = None,
        status: Optional[str] = None,
        include_status: bool = False,
        online_status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve private cellular radios or their operational statuses.

        Args:
            radio_id: Get a specific radio by ID.
            network: Filter by network.
            name: Filter by name.
            status: Filter by admin state.
            include_status: If True, retrieves operational status instead of radio config.
            online_status: Filter operational status (only when include_status=True).
            limit: Max results.
        """
        try:
            if include_status:
                kwargs = {}
                if online_status is not None:
                    kwargs["online_status"] = online_status
                if limit is not None:
                    kwargs["limit"] = limit
                if radio_id is not None:
                    result = client.get_private_cellular_radio_status(radio_id)
                else:
                    result = client.get_private_cellular_radio_statuses(**kwargs)
            else:
                if radio_id is not None:
                    result = client.get_private_cellular_radio(radio_id)
                else:
                    kwargs = {}
                    if network is not None:
                        kwargs["network"] = network
                    if name is not None:
                        kwargs["name"] = name
                    if status is not None:
                        kwargs["admin_state"] = status
                    if limit is not None:
                        kwargs["limit"] = limit
                    result = client.get_private_cellular_radios(**kwargs)
            return handle_ncm_response(result, "get_radios")
        except Exception as e:
            return handle_exception(e, "get_radios")

    @mcp.tool()
    def manage_radio(
        radio_id: Optional[str] = None,
        name: Optional[str] = None,
        admin_state: Optional[str] = None,
        description: Optional[str] = None,
        network: Optional[str] = None,
        tx_power: Optional[int] = None,
    ) -> dict:
        """Update a private cellular radio by ID or name.

        Requires radio_id or name to identify the radio.
        Optional fields to update: admin_state, description, network, tx_power.
        """
        try:
            if radio_id is None and name is None:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Missing required parameters",
                        "details": "Provide either radio_id or name",
                    },
                    "operation": "manage_radio",
                }
            kwargs = {}
            if admin_state is not None:
                kwargs["admin_state"] = admin_state
            if description is not None:
                kwargs["description"] = description
            if network is not None:
                kwargs["network"] = network
            if tx_power is not None:
                kwargs["tx_power"] = tx_power
            result = client.update_private_cellular_radio(
                id=radio_id, name=name, **kwargs
            )
            return handle_ncm_response(result, "manage_radio")
        except Exception as e:
            return handle_exception(e, "manage_radio")

    @mcp.tool()
    def manage_sim(
        action: str = None,
        sim_id: Optional[str] = None,
        iccid: Optional[str] = None,
        imsi: Optional[str] = None,
        network: Optional[str] = None,
        name: Optional[str] = None,
        state: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Query or update private cellular SIMs.

        Actions:
        - "get": Retrieve SIMs. Optional filters: sim_id, network, iccid, name, limit.
        - "update": Update a SIM. Requires sim_id, iccid, or imsi.
          Optional: name, state, network.
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "get":
                if sim_id is not None:
                    result = client.get_private_cellular_sim(sim_id)
                else:
                    kwargs = {}
                    if network is not None:
                        kwargs["network"] = network
                    if iccid is not None:
                        kwargs["iccid"] = iccid
                    if name is not None:
                        kwargs["name"] = name
                    if limit is not None:
                        kwargs["limit"] = limit
                    result = client.get_private_cellular_sims(**kwargs)

            elif action == "update":
                if sim_id is None and iccid is None and imsi is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide sim_id, iccid, or imsi",
                        },
                        "operation": "manage_sim",
                    }
                kwargs = {}
                if name is not None:
                    kwargs["name"] = name
                if state is not None:
                    kwargs["state"] = state
                if network is not None:
                    kwargs["network"] = network
                result = client.update_private_cellular_sim(
                    id=sim_id, iccid=iccid, imsi=imsi, **kwargs
                )

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: get, update",
                    },
                    "operation": "manage_sim",
                }

            return handle_ncm_response(result, "manage_sim")
        except Exception as e:
            return handle_exception(e, "manage_sim")
