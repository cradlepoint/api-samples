"""Unified runner — starts all three NCM MCP servers concurrently.

Usage:
    python -m ncm_mcp_servers

All servers run in a single process using asyncio. Each binds to its
own port (default: 3001, 3002, 3003). Transport defaults to Streamable HTTP.

Environment variables:
    MCP_TRANSPORT: "streamable-http" (default) or "sse"
    NCM_FLEET_PORT: Fleet server port (default 3001)
    NCM_MONITORING_PORT: Monitoring server port (default 3002)
    NCM_CLOUD_SERVICES_PORT: Cloud services server port (default 3003)
    LOG_LEVEL: Logging level (default INFO)
"""

import asyncio
import os
import signal
import sys
from typing import cast

from ncm_mcp_servers.shared.credentials import load_credentials
from ncm_mcp_servers.shared.logging import get_logger

logger = get_logger("runner")


async def run_all() -> None:
    """Start all three MCP servers concurrently."""
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

    # Select the async runner based on transport
    if transport == "sse":
        tasks = [
            asyncio.create_task(fleet.run_sse_async()),
            asyncio.create_task(monitoring.run_sse_async()),
            asyncio.create_task(cloud.run_sse_async()),
        ]
    else:
        # Default: Streamable HTTP
        tasks = [
            asyncio.create_task(fleet.run_streamable_http_async()),
            asyncio.create_task(monitoring.run_streamable_http_async()),
            asyncio.create_task(cloud.run_streamable_http_async()),
        ]

    fleet_port = os.environ.get("NCM_FLEET_PORT", "3001")
    monitoring_port = os.environ.get("NCM_MONITORING_PORT", "3002")
    cloud_port = os.environ.get("NCM_CLOUD_SERVICES_PORT", "3003")

    logger.info(f"  ncm-fleet          -> port {fleet_port}")
    logger.info(f"  ncm-monitoring     -> port {monitoring_port}")
    logger.info(f"  ncm-cloud-services -> port {cloud_port}")

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
