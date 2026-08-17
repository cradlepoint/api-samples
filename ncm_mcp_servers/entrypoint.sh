#!/bin/bash
# Start all three NCM MCP servers in a single container.
# Each server runs on its own port (default: 3001, 3002, 3003).
set -e

PIDS=()

# Trap SIGTERM/SIGINT and forward to child processes
cleanup() {
    echo "Received shutdown signal. Stopping servers..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    wait
    exit 0
}
trap cleanup SIGTERM SIGINT

echo "Starting NCM MCP Servers..."
echo "  ncm-fleet          -> port ${NCM_FLEET_PORT:-3001}"
echo "  ncm-monitoring     -> port ${NCM_MONITORING_PORT:-3002}"
echo "  ncm-cloud-services -> port ${NCM_CLOUD_SERVICES_PORT:-3003}"

python -m ncm_mcp_servers.ncm_fleet &
PIDS+=($!)

python -m ncm_mcp_servers.ncm_monitoring &
PIDS+=($!)

python -m ncm_mcp_servers.ncm_cloud_services &
PIDS+=($!)

# Wait for any process to exit
wait -n
EXIT_CODE=$?

echo "A server process exited (code=$EXIT_CODE). Shutting down..."
cleanup
