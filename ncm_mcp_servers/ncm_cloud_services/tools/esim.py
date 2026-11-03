"""MCP tools for NCM eSIM profile management.

Provides:
- get_esim_profiles: Query eSIM profiles
- get_esim_profiles_manage: Query managed eSIM profiles
- manage_esim_profiles_manage: Create a managed eSIM profile
- get_esim_profile_activations: Query eSIM profile activations
- manage_esim_profile_activation: Create/update an eSIM profile activation
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register eSIM profile management tools."""

    @mcp.tool()
    def get_esim_profiles(
        profile_id: Optional[str] = None,
        active: Optional[bool] = None,
        carrier: Optional[str] = None,
        classification: Optional[str] = None,
        eid: Optional[str] = None,
        iccid: Optional[str] = None,
        net_device: Optional[str] = None,
        nickname: Optional[str] = None,
        profile_name: Optional[str] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve eSIM profiles, or a single profile when profile_id is set.

        Optional filters (list form): active, carrier, classification, eid,
        iccid, net_device, nickname, profile_name, search, sort, limit.
        """
        try:
            kwargs = {}
            if active is not None:
                kwargs["active"] = active
            if carrier is not None:
                kwargs["carrier"] = carrier
            if classification is not None:
                kwargs["classification"] = classification
            if eid is not None:
                kwargs["eid"] = eid
            if iccid is not None:
                kwargs["iccid"] = iccid
            if net_device is not None:
                kwargs["net_device"] = net_device
            if nickname is not None:
                kwargs["nickname"] = nickname
            if profile_name is not None:
                kwargs["profile_name"] = profile_name
            if search is not None:
                kwargs["search"] = search
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_esim_profiles(profile_id=profile_id, **kwargs)
            return handle_ncm_response(result, "get_esim_profiles")
        except Exception as e:
            return handle_exception(e, "get_esim_profiles")

    @mcp.tool()
    def get_esim_profiles_manage(
        manage_id: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve managed eSIM profiles, or a single item when manage_id is set.

        Optional filters (list form): sort, limit.
        """
        try:
            kwargs = {}
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_esim_profiles_manage(manage_id=manage_id, **kwargs)
            return handle_ncm_response(result, "get_esim_profiles_manage")
        except Exception as e:
            return handle_exception(e, "get_esim_profiles_manage")

    @mcp.tool()
    def manage_esim_profiles_manage(
        action: str = None,
        body: Optional[dict] = None,
    ) -> dict:
        """Manage managed eSIM profile operations.

        Actions:
        - "create": Create a managed eSIM profile. Requires body, a full
          JSON:API document sent verbatim.
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(body=body)
                if err is not None:
                    return err
                result = client.create_esim_profiles_manage(body=body)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create",
                    },
                    "operation": "manage_esim_profiles_manage",
                }

            return handle_ncm_response(result, "manage_esim_profiles_manage")
        except Exception as e:
            return handle_exception(e, "manage_esim_profiles_manage")

    @mcp.tool()
    def get_esim_profile_activations(
        activation_id: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve eSIM profile activations, or one when activation_id is set.

        Optional filters (list form): sort, limit.
        """
        try:
            kwargs = {}
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_esim_profile_activations(
                activation_id=activation_id, **kwargs
            )
            return handle_ncm_response(result, "get_esim_profile_activations")
        except Exception as e:
            return handle_exception(e, "get_esim_profile_activations")

    @mcp.tool()
    def manage_esim_profile_activation(
        action: str = None,
        activation_id: Optional[str] = None,
        operation: Optional[str] = None,
        payload: Optional[str] = None,
        body: Optional[dict] = None,
    ) -> dict:
        """Manage eSIM profile activation operations.

        Actions:
        - "create": Create an activation via multipart upload. Requires
          operation and payload.
        - "update": Update an activation. Requires activation_id and body
          (a full JSON:API document sent verbatim).
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(
                    operation=operation, payload=payload
                )
                if err is not None:
                    return err
                result = client.create_esim_profile_activation(operation, payload)

            elif action == "update":
                err = validate_required_params(
                    activation_id=activation_id, body=body
                )
                if err is not None:
                    return err
                result = client.update_esim_profile_activation(
                    activation_id, body=body
                )

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create, update",
                    },
                    "operation": "manage_esim_profile_activation",
                }

            return handle_ncm_response(result, "manage_esim_profile_activation")
        except Exception as e:
            return handle_exception(e, "manage_esim_profile_activation")
