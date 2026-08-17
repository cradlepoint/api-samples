"""NCM Monitoring MCP Server entry point.

Monitors network health: net devices, alerts/logs, and speed tests
via the NCM v2 API.

Tools (6 total):
- get_net_devices, get_net_device_health, get_net_device_metrics
- get_logs
- create_speed_test, get_speed_test
"""

import os
import sys
from typing import Optional, cast

from mcp.server.fastmcp import FastMCP

from ncm_mcp_servers.shared.credentials import ApiCredentials, load_credentials
from ncm_mcp_servers.shared.client import get_ncm_client
from ncm_mcp_servers.shared.logging import get_logger
from ncm_mcp_servers.ncm_monitoring.tools import register_all

logger = get_logger("ncm_monitoring")


def create_server(
    credentials: Optional[ApiCredentials] = None,
) -> FastMCP:
    """Creates and configures the monitoring MCP server."""
    if credentials is None:
        credentials = load_credentials()

    credentials.validate(require_v2=True)
    client = get_ncm_client(credentials)
    v2_client = client.v2 if hasattr(client, 'v2') else client

    transport = os.environ.get("MCP_TRANSPORT", "streamable-http").lower()
    port = int(os.environ.get("NCM_MONITORING_PORT", "3002"))

    if transport == "sse":
        mcp = FastMCP("ncm-monitoring", host="0.0.0.0", port=port)
    else:
        mcp = FastMCP("ncm-monitoring", host="0.0.0.0", port=port)

    register_all(mcp, v2_client)  # type: ignore[arg-type]
    logger.info("Server configured", extra={"transport": transport, "port": port})
    return mcp


def main() -> None:
    """Entry point for ncm-monitoring server."""
    try:
        server = create_server()
        transport = cast(str, os.environ.get("MCP_TRANSPORT", "streamable-http")).lower()
        logger.info("Starting ncm-monitoring server")
        server.run(transport=transport)  # type: ignore[arg-type]
    except ValueError as exc:
        logger.error("Failed to start server", extra={"error": str(exc)})
        sys.exit(1)


if __name__ == "__main__":
    main()
