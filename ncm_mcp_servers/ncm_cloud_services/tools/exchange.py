"""MCP tools for NCM exchange site and resource management.

Consolidates exchange operations into:
- get_exchange_sites: Query exchange sites
- manage_exchange_site: Create, update, delete sites
- get_exchange_resources: Query exchange resources
- manage_exchange_resource: Create, update, delete resources
"""

from typing import List, Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register exchange management tools."""

    @mcp.tool()
    def get_exchange_sites(
        site_id: Optional[str] = None,
        exchange_network_id: Optional[str] = None,
        name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve exchange sites with optional filtering by ID, name, or network."""
        try:
            kwargs = {}
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_exchange_sites(
                site_id=site_id,
                exchange_network_id=exchange_network_id,
                name=name,
                **kwargs,
            )
            return handle_ncm_response(result, "get_exchange_sites")
        except Exception as e:
            return handle_exception(e, "get_exchange_sites")

    @mcp.tool()
    def manage_exchange_site(
        action: str = None,
        site_id: Optional[str] = None,
        site_name: Optional[str] = None,
        name: Optional[str] = None,
        exchange_network_id: Optional[str] = None,
        router_id: Optional[str] = None,
        primary_dns: Optional[str] = None,
        secondary_dns: Optional[str] = None,
        lan_as_dns: Optional[bool] = None,
        local_domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> dict:
        """Manage exchange site lifecycle operations.

        Actions:
        - "create": Create a new site. Requires name, exchange_network_id, router_id.
          Optional: primary_dns, secondary_dns, lan_as_dns, local_domain, tags.
        - "update": Update a site. Requires site_id or name.
          Optional: primary_dns, secondary_dns, lan_as_dns, local_domain, tags.
        - "delete": Delete a site. Requires site_id or site_name.
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(
                    name=name,
                    exchange_network_id=exchange_network_id,
                    router_id=router_id,
                )
                if err is not None:
                    return err
                kwargs = {}
                if primary_dns is not None:
                    kwargs["primary_dns"] = primary_dns
                if secondary_dns is not None:
                    kwargs["secondary_dns"] = secondary_dns
                if lan_as_dns is not None:
                    kwargs["lan_as_dns"] = lan_as_dns
                if local_domain is not None:
                    kwargs["local_domain"] = local_domain
                if tags is not None:
                    kwargs["tags"] = tags
                result = client.create_exchange_site(
                    name, exchange_network_id, router_id, **kwargs
                )

            elif action == "update":
                if site_id is None and name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either site_id or name",
                        },
                        "operation": "manage_exchange_site",
                    }
                kwargs = {}
                if primary_dns is not None:
                    kwargs["primary_dns"] = primary_dns
                if secondary_dns is not None:
                    kwargs["secondary_dns"] = secondary_dns
                if lan_as_dns is not None:
                    kwargs["lan_as_dns"] = lan_as_dns
                if local_domain is not None:
                    kwargs["local_domain"] = local_domain
                if tags is not None:
                    kwargs["tags"] = tags
                result = client.update_exchange_site(
                    site_id=site_id, name=name, **kwargs
                )

            elif action == "delete":
                if site_id is None and site_name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either site_id or site_name",
                        },
                        "operation": "manage_exchange_site",
                    }
                result = client.delete_exchange_site(
                    site_id=site_id, site_name=site_name
                )

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create, update, delete",
                    },
                    "operation": "manage_exchange_site",
                }

            return handle_ncm_response(result, "manage_exchange_site")
        except Exception as e:
            return handle_exception(e, "manage_exchange_site")

    @mcp.tool()
    def get_exchange_resources(
        site_id: Optional[str] = None,
        exchange_network_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        site_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve exchange resources with optional filtering."""
        try:
            kwargs = {}
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_exchange_resources(
                site_id=site_id,
                exchange_network_id=exchange_network_id,
                resource_id=resource_id,
                site_name=site_name,
                **kwargs,
            )
            return handle_ncm_response(result, "get_exchange_resources")
        except Exception as e:
            return handle_exception(e, "get_exchange_resources")

    @mcp.tool()
    def manage_exchange_resource(
        action: str = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        resource_type: Optional[str] = None,
        site_id: Optional[str] = None,
        site_name: Optional[str] = None,
        domain: Optional[str] = None,
        ip: Optional[str] = None,
        protocols: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        static_prime_ip: Optional[str] = None,
        port_ranges: Optional[List[str]] = None,
        name: Optional[str] = None,
    ) -> dict:
        """Manage exchange resource lifecycle operations.

        Actions:
        - "create": Create a resource. Requires resource_name, resource_type,
          (site_id or site_name). resource_type must be one of:
          exchange_fqdn_resources, exchange_wildcard_fqdn_resources,
          or exchange_ipsubnet_resources.
          Optional: domain, ip, protocols, tags, static_prime_ip, port_ranges.
        - "update": Update a resource. Requires resource_id.
          Optional: name, protocols, tags, domain, ip, static_prime_ip, port_ranges.
        - "delete": Delete resources. Requires resource_id, site_name, or site_id.
        """
        try:
            err = validate_required_params(action=action)
            if err is not None:
                return err

            if action == "create":
                err = validate_required_params(
                    resource_name=resource_name, resource_type=resource_type
                )
                if err is not None:
                    return err
                if site_id is None and site_name is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide either site_id or site_name",
                        },
                        "operation": "manage_exchange_resource",
                    }
                kwargs = {}
                if domain is not None:
                    kwargs["domain"] = domain
                if ip is not None:
                    kwargs["ip"] = ip
                if protocols is not None:
                    kwargs["protocols"] = protocols
                if tags is not None:
                    kwargs["tags"] = tags
                if static_prime_ip is not None:
                    kwargs["static_prime_ip"] = static_prime_ip
                if port_ranges is not None:
                    kwargs["port_ranges"] = port_ranges
                result = client.create_exchange_resource(
                    resource_name,
                    resource_type,
                    site_id=site_id,
                    site_name=site_name,
                    **kwargs,
                )

            elif action == "update":
                err = validate_required_params(resource_id=resource_id)
                if err is not None:
                    return err
                kwargs = {}
                if name is not None:
                    kwargs["name"] = name
                if protocols is not None:
                    kwargs["protocols"] = protocols
                if tags is not None:
                    kwargs["tags"] = tags
                if domain is not None:
                    kwargs["domain"] = domain
                if ip is not None:
                    kwargs["ip"] = ip
                if static_prime_ip is not None:
                    kwargs["static_prime_ip"] = static_prime_ip
                if port_ranges is not None:
                    kwargs["port_ranges"] = port_ranges
                result = client.update_exchange_resource(resource_id, **kwargs)

            elif action == "delete":
                if resource_id is None and site_name is None and site_id is None:
                    return {
                        "success": False,
                        "error": {
                            "code": 400,
                            "message": "Missing required parameters",
                            "details": "Provide resource_id, site_name, or site_id",
                        },
                        "operation": "manage_exchange_resource",
                    }
                result = client.delete_exchange_resource(
                    resource_id=resource_id,
                    site_name=site_name,
                    site_id=site_id,
                )

            else:
                return {
                    "success": False,
                    "error": {
                        "code": 400,
                        "message": "Invalid action",
                        "details": "Valid actions: create, update, delete",
                    },
                    "operation": "manage_exchange_resource",
                }

            return handle_ncm_response(result, "manage_exchange_resource")
        except Exception as e:
            return handle_exception(e, "manage_exchange_resource")
