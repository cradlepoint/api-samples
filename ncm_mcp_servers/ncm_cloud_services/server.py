"""NCM Cloud Services MCP Server entry point.

Manages users, subscriptions, NetCloud Exchange, tenants, eSIM, Starlink,
LAN, remote connect, modem upgrades, migrations, and Wi-Fi passwords via
the NCM v3 API.

Tools:
- get_users, manage_user
- get_subscriptions, get_regrade, manage_subscription
- get_exchange_sites, manage_exchange_site, get_exchange_resources,
  manage_exchange_resource
- get_tenants, get_tenant_authorizations, manage_tenant_authorization
- get_esim_profiles, get_esim_profiles_manage, manage_esim_profiles_manage,
  get_esim_profile_activations, manage_esim_profile_activation
- get_starlink_interfaces, get_starlink_interface_reboots,
  get_starlink_interface_stows, get_starlink_diagnostics,
  manage_starlink_interface
- get_lan_devices, get_lan_product_infos, get_lan_manager_options,
  manage_lan_manager_option
- get_remote_connect_profiles, manage_remote_connect_profile
- get_modem_software_versions, get_modem_upgrades, manage_modem_upgrade
- get_migrations, manage_migration
- get_unmasked_wifi_passwords
"""

import os
import sys
from typing import Optional, cast

from mcp.server import MCPServer

from ncm_mcp_servers.shared.credentials import ApiCredentials, load_credentials
from ncm_mcp_servers.shared.client import get_ncm_client
from ncm_mcp_servers.shared.logging import get_logger
from ncm_mcp_servers.ncm_cloud_services.tools import register_all

logger = get_logger("ncm_cloud_services")


def create_server(
    credentials: Optional[ApiCredentials] = None,
) -> MCPServer:
    """Creates and configures the cloud services MCP server."""
    if credentials is None:
        credentials = load_credentials()

    credentials.validate(require_v3=True)
    client = get_ncm_client(credentials)
    v3_client = client.v3 if hasattr(client, 'v3') else client

    mcp = MCPServer("ncm-cloud-services")

    register_all(mcp, v3_client)  # type: ignore[arg-type]
    logger.info("Server configured")
    return mcp


def main() -> None:
    """Entry point for ncm-cloud-services server."""
    try:
        server = create_server()
        transport = cast(str, os.environ.get("MCP_TRANSPORT", "streamable-http")).lower()
        port = int(os.environ.get("NCM_CLOUD_SERVICES_PORT", "3003"))

        logger.info("Starting ncm-cloud-services server", extra={"transport": transport, "port": port})

        if transport == "stdio":
            server.run(transport="stdio")
        else:
            server.run(
                transport="streamable-http",
                host="0.0.0.0",
                port=port,
                stateless_http=True,
            )
    except ValueError as exc:
        logger.error("Failed to start server", extra={"error": str(exc)})
        sys.exit(1)


if __name__ == "__main__":
    main()
