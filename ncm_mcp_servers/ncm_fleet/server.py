"""NCM Fleet Management MCP Server entry point.

Manages routers, groups, accounts, locations, configurations,
firmware, and products via the NCM v2 API.

Tools (17 total):
- get_routers, manage_router, reboot_router, reboot_group
- get_groups, manage_group
- get_accounts, manage_subaccount
- get_locations, manage_location
- get_configuration_managers, patch_config, put_router_config,
  copy_router_config, resume_updates
- get_firmware
- get_products
"""

import os
import sys
from typing import Optional, cast

from mcp.server.fastmcp import FastMCP

from ncm_mcp_servers.shared.credentials import ApiCredentials, load_credentials
from ncm_mcp_servers.shared.client import get_ncm_client
from ncm_mcp_servers.shared.logging import get_logger
from ncm_mcp_servers.ncm_fleet.tools import register_all

logger = get_logger("ncm_fleet")


def create_server(
    credentials: Optional[ApiCredentials] = None,
) -> FastMCP:
    """Creates and configures the fleet management MCP server."""
    if credentials is None:
        credentials = load_credentials()

    credentials.validate(require_v2=True)
    client = get_ncm_client(credentials)
    v2_client = client.v2 if hasattr(client, 'v2') else client

    transport = os.environ.get("MCP_TRANSPORT", "streamable-http").lower()
    port = int(os.environ.get("NCM_FLEET_PORT", "3001"))

    if transport == "sse":
        mcp = FastMCP("ncm-fleet", host="0.0.0.0", port=port)
    else:
        mcp = FastMCP("ncm-fleet", host="0.0.0.0", port=port)

    register_all(mcp, v2_client)  # type: ignore[arg-type]
    logger.info("Server configured", extra={"transport": transport, "port": port})
    return mcp


def main() -> None:
    """Entry point for ncm-fleet server."""
    try:
        server = create_server()
        transport = cast(str, os.environ.get("MCP_TRANSPORT", "streamable-http")).lower()
        logger.info("Starting ncm-fleet server")
        server.run(transport=transport)  # type: ignore[arg-type]
    except ValueError as exc:
        logger.error("Failed to start server", extra={"error": str(exc)})
        sys.exit(1)


if __name__ == "__main__":
    main()
