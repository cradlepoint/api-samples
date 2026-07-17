"""NCM Fleet Management tools registration."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ncm_mcp_servers.shared.ncm import NcmClientv2

from ncm_mcp_servers.ncm_fleet.tools import (
    routers,
    groups,
    accounts,
    locations,
    configurations,
    firmware,
)


def register_all(mcp: "FastMCP", client: "NcmClientv2") -> None:
    """Registers all fleet management tools with the MCP server."""
    routers.register(mcp, client)
    groups.register(mcp, client)
    accounts.register(mcp, client)
    locations.register(mcp, client)
    configurations.register(mcp, client)
    firmware.register(mcp, client)
