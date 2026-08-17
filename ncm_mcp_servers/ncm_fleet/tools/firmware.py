"""MCP tools for NCM firmware and product information.

Consolidates firmware + products into a single tool:
- get_firmware: Query firmware versions, optionally by product
"""

from typing import Optional

from ncm_mcp_servers.shared.error_handler import (
    handle_exception,
    handle_ncm_response,
    validate_required_params,
)


def register(mcp, client):
    """Register firmware and product tools."""

    @mcp.tool()
    def get_products(
        product_id: Optional[int] = None,
        product_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve products with optional filtering by ID or name.

        If product_id is provided, returns a single product by ID.
        If product_name is provided, returns a single product by name.
        Otherwise returns all products.
        """
        try:
            if product_id is not None:
                result = client.get_product_by_id(product_id)
                return handle_ncm_response(result, "get_products")
            if product_name is not None:
                result = client.get_product_by_name(product_name)
                return handle_ncm_response(result, "get_products")
            kwargs = {}
            if limit is not None:
                kwargs["limit"] = limit
            result = client.get_products(**kwargs)
            return handle_ncm_response(result, "get_products")
        except Exception as e:
            return handle_exception(e, "get_products")

    @mcp.tool()
    def get_firmware(
        version: Optional[str] = None,
        product_id: Optional[int] = None,
        product_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Retrieve firmware versions with optional filtering.

        If product_id or product_name is provided along with version,
        retrieves firmware for that specific product and version.
        Otherwise returns all firmware matching the version filter.
        """
        try:
            if version and (product_id or product_name):
                if product_id is not None:
                    result = client.get_firmware_for_product_id_by_version(
                        product_id, version
                    )
                else:
                    result = client.get_firmware_for_product_name_by_version(
                        product_name, version
                    )
            else:
                kwargs = {}
                if version is not None:
                    kwargs["version"] = version
                if limit is not None:
                    kwargs["limit"] = limit
                result = client.get_firmwares(**kwargs)
            return handle_ncm_response(result, "get_firmware")
        except Exception as e:
            return handle_exception(e, "get_firmware")
