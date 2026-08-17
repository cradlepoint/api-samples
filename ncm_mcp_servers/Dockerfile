FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY __init__.py ./ncm_mcp_servers/
COPY shared/ ./ncm_mcp_servers/shared/
COPY ncm_fleet/ ./ncm_mcp_servers/ncm_fleet/
COPY ncm_monitoring/ ./ncm_mcp_servers/ncm_monitoring/
COPY ncm_cloud_services/ ./ncm_mcp_servers/ncm_cloud_services/
COPY entrypoint.sh /app/entrypoint.sh

RUN pip install --no-cache-dir -e . && chmod +x /app/entrypoint.sh

ENV MCP_TRANSPORT=streamable-http
ENV NCM_FLEET_PORT=3001
ENV NCM_MONITORING_PORT=3002
ENV NCM_CLOUD_SERVICES_PORT=3003

EXPOSE 3001 3002 3003

ENTRYPOINT ["/app/entrypoint.sh"]
