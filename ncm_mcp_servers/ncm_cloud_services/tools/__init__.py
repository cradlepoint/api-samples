"""NCM Cloud Services tools registration."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import MCPServer
    from ncm_mcp_servers.shared.ncm import NcmClientv3

from ncm_mcp_servers.ncm_cloud_services.tools import (
    users,
    subscriptions,
    exchange,
    tenants,
    esim,
    starlink,
    lan,
    remote_connect,
    modem_upgrades,
    migrations,
    wifi,
)


def register_all(mcp: "MCPServer", client: "NcmClientv3") -> None:
    """Registers all cloud services tools with the MCP server."""
    users.register(mcp, client)
    subscriptions.register(mcp, client)
    exchange.register(mcp, client)
    tenants.register(mcp, client)
    esim.register(mcp, client)
    starlink.register(mcp, client)
    lan.register(mcp, client)
    remote_connect.register(mcp, client)
    modem_upgrades.register(mcp, client)
    migrations.register(mcp, client)
    wifi.register(mcp, client)
