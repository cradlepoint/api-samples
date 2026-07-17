"""NCM Cloud Services MCP Server entry point.

Manages users, subscriptions, private cellular networks, and
NetCloud Exchange via the NCM v3 API.

Tools (13 total):
- get_users, manage_user
- get_subscriptions, manage_subscription
- get_networks, manage_network, get_radios, manage_radio, manage_sim
- get_exchange_sites, manage_exchange_site, get_exchange_resources,
  manage_exchange_resource
"""

import os
import sys
from typing import Optional, cast

from mcp.server.fastmcp import FastMCP

from ncm_mcp_servers.shared.credentials import ApiCredentials, load_credentials
from ncm_mcp_servers.shared.client import get_ncm_client
from ncm_mcp_servers.shared.logging import get_logger
from ncm_mcp_servers.ncm_cloud_services.tools import register_all

logger = get_logger("ncm_cloud_services")


def create_server(
    credentials: Optional[ApiCredentials] = None,
) -> FastMCP:
    """Creates and configures the cloud services MCP server."""
    if credentials is None:
        credentials = load_credentials()

    credentials.validate(require_v3=True)
    client = get_ncm_client(credentials)
    v3_client = client.v3 if hasattr(client, 'v3') else client

    transport = os.environ.get("MCP_TRANSPORT", "streamable-http").lower()
    port = int(os.environ.get("NCM_CLOUD_SERVICES_PORT", "3003"))

    if transport == "sse":
        mcp = FastMCP("ncm-cloud-services", host="0.0.0.0", port=port)
    else:
        mcp = FastMCP("ncm-cloud-services", host="0.0.0.0", port=port)

    register_all(mcp, v3_client)  # type: ignore[arg-type]
    logger.info("Server configured", extra={"transport": transport, "port": port})
    return mcp


def main() -> None:
    """Entry point for ncm-cloud-services server."""
    try:
        server = create_server()
        transport = cast(str, os.environ.get("MCP_TRANSPORT", "streamable-http")).lower()
        logger.info("Starting ncm-cloud-services server")
        server.run(transport=transport)  # type: ignore[arg-type]
    except ValueError as exc:
        logger.error("Failed to start server", extra={"error": str(exc)})
        sys.exit(1)


if __name__ == "__main__":
    main()
