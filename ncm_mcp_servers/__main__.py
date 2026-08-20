"""Unified runner — starts all three NCM MCP servers concurrently.

Usage:
    python -m ncm_mcp_servers

All servers run in a single process using asyncio. Each binds to its
own port (default: 3001, 3002, 3003). Transport defaults to Streamable HTTP
with stateless mode enabled for both 2026-07-28 and legacy clients.

Environment variables:
    MCP_TRANSPORT: "streamable-http" (default) or "stdio"
    NCM_FLEET_PORT: Fleet server port (default 3001)
    NCM_MONITORING_PORT: Monitoring server port (default 3002)
    NCM_CLOUD_SERVICES_PORT: Cloud services server port (default 3003)
    LOG_LEVEL: Logging level (default INFO)
"""

import asyncio
import os
import signal
import sys

import uvicorn

from ncm_mcp_servers.shared.credentials import load_credentials
from ncm_mcp_servers.shared.logging import get_logger

logger = get_logger("runner")


async def run_all() -> None:
    """Start all three MCP servers concurrently via their ASGI apps."""
    credentials = load_credentials()
    transport = os.environ.get("MCP_TRANSPORT", "streamable-http").lower()

    logger.info(
        "Starting all NCM MCP servers",
        extra={"transport": transport},
    )

    # Import here to avoid circular import issues at module level
    from ncm_mcp_servers.ncm_fleet.server import create_server as create_fleet
    from ncm_mcp_servers.ncm_monitoring.server import create_server as create_monitoring
    from ncm_mcp_servers.ncm_cloud_services.server import create_server as create_cloud

    fleet = create_fleet(credentials)
    monitoring = create_monitoring(credentials)
    cloud = create_cloud(credentials)

    fleet_port = int(os.environ.get("NCM_FLEET_PORT", "3001"))
    monitoring_port = int(os.environ.get("NCM_MONITORING_PORT", "3002"))
    cloud_port = int(os.environ.get("NCM_CLOUD_SERVICES_PORT", "3003"))

    if transport == "stdio":
        # stdio only supports a single server; run fleet as default
        logger.warning("stdio transport only supports one server; starting ncm-fleet only")
        fleet.run(transport="stdio")
        return

    # Build ASGI apps with stateless_http for load-balancer-friendly operation
    fleet_app = fleet.streamable_http_app(stateless_http=True)
    monitoring_app = monitoring.streamable_http_app(stateless_http=True)
    cloud_app = cloud.streamable_http_app(stateless_http=True)

    # Create uvicorn server configs
    fleet_config = uvicorn.Config(fleet_app, host="0.0.0.0", port=fleet_port, log_level="info")
    monitoring_config = uvicorn.Config(monitoring_app, host="0.0.0.0", port=monitoring_port, log_level="info")
    cloud_config = uvicorn.Config(cloud_app, host="0.0.0.0", port=cloud_port, log_level="info")

    fleet_server = uvicorn.Server(fleet_config)
    monitoring_server = uvicorn.Server(monitoring_config)
    cloud_server = uvicorn.Server(cloud_config)

    logger.info(f"  ncm-fleet          -> http://0.0.0.0:{fleet_port}/mcp")
    logger.info(f"  ncm-monitoring     -> http://0.0.0.0:{monitoring_port}/mcp")
    logger.info(f"  ncm-cloud-services -> http://0.0.0.0:{cloud_port}/mcp")

    # Run all three servers concurrently
    tasks = [
        asyncio.create_task(fleet_server.serve()),
        asyncio.create_task(monitoring_server.serve()),
        asyncio.create_task(cloud_server.serve()),
    ]

    # Wait for all tasks; if one fails, cancel the rest
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

    for task in pending:
        task.cancel()

    # Re-raise any exceptions from completed tasks
    for task in done:
        if task.exception():
            raise task.exception()


def main() -> None:
    """Entry point for unified server runner."""
    # Handle Ctrl+C gracefully
    def handle_signal(sig, frame):
        logger.info("Shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        asyncio.run(run_all())
    except ValueError as exc:
        logger.error("Failed to start servers", extra={"error": str(exc)})
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
