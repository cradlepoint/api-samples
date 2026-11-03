"""MCP tools for NCM remote connect profile management.

Provides:
- get_remote_connect_profiles: Query remote connect profiles
- manage_remote_connect_profile: Create/update/delete a profile
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register remote connect profile management tools."""

    @mcp.tool()
    def get_remote_connect_profiles(
        profile_id: Optional[str] = None,
        address: Optional[str] = None,
        name: Optional[str] = None,
        router: Optional[str] = None,
        profile_type: Optional[str] = None,
        sort: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve remote connect profiles, or one when profile_id is set.

        Optional filters (list form): address, name, router, profile_type
        (mapped to the ``type`` filter), sort, limit.
        """
        try:
            kwargs = {}
            if address is not None:
                kwargs["address"] = address
            if name is not None:
                kwargs["name"] = name
            if router is not None:
                kwargs["router"] = router
            if profile_type is not None:
                kwargs["type"] = profile_type
            if sort is not None:
                kwargs["sort"] = sort
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_remote_connect_profiles(
                profile_id=profile_id, **kwargs
            )
            return handle_ncm_response(result, "get_remote_connect_profiles")
        except Exception as e:
            return handle_exception(e, "get_remote_connect_profiles")

    @mcp.tool()
    def manage_remote_connect_profile(
        action: str = None,
        profile_id: Optional[str] = None,
        profile_type: Optional[str] = None,
        attributes: Optional[dict] = None,
        relationships: Optional[dict] = None,
    ) -> dict:
        """Manage remote connect profile operations.

        Actions:
        - "create": Create a profile. Requires profile_type, attributes, and
          relationships (must include the required ``router`` relationship).
          profile_type must be one of: remote_connect_ssh_profile,
          remote_connect_http_profile, remote_connect_https_profile,
          remote_connect_rdp_profile, remote_connect_vnc_profile,
          remote_connect_serial_profile.
        - "update": Update a profile. Requires profile_id.
          Optional: profile_type, attributes, relationships.
        - "delete": Delete a profile. Requires profile_id.
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(profile_type=profile_type)
                if err is not None:
                    return err
                result = client.create_remote_connect_profile(
                    profile_type,
                    attributes=attributes,
                    relationships=relationships,
                )

            elif action == "update":
                err = validate_required_params(profile_id=profile_id)
                if err is not None:
                    return err
                kwargs = {}
                if profile_type is not None:
                    kwargs["profile_type"] = profile_type
                if attributes is not None:
                    kwargs["attributes"] = attributes
                if relationships is not None:
                    kwargs["relationships"] = relationships
                result = client.update_remote_connect_profile(profile_id, **kwargs)

            elif action == "delete":
                err = validate_required_params(profile_id=profile_id)
                if err is not None:
                    return err
                result = client.delete_remote_connect_profile(profile_id)

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create, update, delete",
                    },
                    "operation": "manage_remote_connect_profile",
                }

            return handle_ncm_response(result, "manage_remote_connect_profile")
        except Exception as e:
            return handle_exception(e, "manage_remote_connect_profile")
