"""NCM Cloud Services tools registration."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ncm_mcp_servers.shared.ncm import NcmClientv3

from ncm_mcp_servers.ncm_cloud_services.tools import (
    users,
    subscriptions,
    private_cellular,
    exchange,
)


def register_all(mcp: "FastMCP", client: "NcmClientv3") -> None:
    """Registers all cloud services tools with the MCP server."""
    users.register(mcp, client)
    subscriptions.register(mcp, client)
    private_cellular.register(mcp, client)
    exchange.register(mcp, client)
