"""NCM Monitoring tools registration."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ncm_mcp_servers.shared.ncm import NcmClientv2

from ncm_mcp_servers.ncm_monitoring.tools import (
    net_devices,
    alerts,
    speed_tests,
)


def register_all(mcp: "FastMCP", client: "NcmClientv2") -> None:
    """Registers all monitoring tools with the MCP server."""
    net_devices.register(mcp, client)
    alerts.register(mcp, client)
    speed_tests.register(mcp, client)
