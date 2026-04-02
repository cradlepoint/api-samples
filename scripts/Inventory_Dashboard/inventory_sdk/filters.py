"""Filter builder for Ericsson NCM API query parameters.

Supports the NCM v2 filter syntax including __in, __lt, __gt, __lte, __gte suffixes.
"""

from __future__ import annotations

from typing import Any


class FilterBuilder:
    """Fluent builder for constructing NCM API query parameters.

    Usage:
        filters = (
            FilterBuilder()
            .field("state", "online")
            .field_in("id", [123, 456, 789])
            .field_gt("updated_at", "2025-01-01T00:00:00")
            .order_by("name")
            .page(limit=50, offset=0)
        )
        routers = client.get_routers(filters=filters)
    """

    def __init__(self) -> None:
        self._params: dict[str, Any] = {}

    def field(self, name: str, value: Any) -> FilterBuilder:
        """Set an exact-match filter (e.g. state=online)."""
        self._params[name] = value
        return self

    def field_in(self, name: str, values: list[Any]) -> FilterBuilder:
        """Set an __in filter (e.g. id__in=1,2,3)."""
        self._params[f"{name}__in"] = ",".join(str(v) for v in values)
        return self

    def field_gt(self, name: str, value: Any) -> FilterBuilder:
        """Set a __gt (greater than) filter."""
        self._params[f"{name}__gt"] = value
        return self

    def field_gte(self, name: str, value: Any) -> FilterBuilder:
        """Set a __gte (greater than or equal) filter."""
        self._params[f"{name}__gte"] = value
        return self

    def field_lt(self, name: str, value: Any) -> FilterBuilder:
        """Set a __lt (less than) filter."""
        self._params[f"{name}__lt"] = value
        return self

    def field_lte(self, name: str, value: Any) -> FilterBuilder:
        """Set a __lte (less than or equal) filter."""
        self._params[f"{name}__lte"] = value
        return self

    def order_by(self, *fields: str) -> FilterBuilder:
        """Set ordering. Prefix with '-' for descending."""
        self._params["order_by"] = ",".join(fields)
        return self

    def fields(self, *field_names: str) -> FilterBuilder:
        """Limit returned fields (sparse fieldset)."""
        self._params["fields"] = ",".join(field_names)
        return self

    def expand(self, *relations: str) -> FilterBuilder:
        """Expand related resources inline."""
        self._params["expand"] = ",".join(relations)
        return self

    def page(self, *, limit: int = 500, offset: int = 0) -> FilterBuilder:
        """Set pagination parameters."""
        self._params["limit"] = limit
        self._params["offset"] = offset
        return self

    def custom(self, key: str, value: Any) -> FilterBuilder:
        """Add an arbitrary query parameter."""
        self._params[key] = value
        return self

    def build(self) -> dict[str, Any]:
        """Return the query parameters as a dict."""
        return dict(self._params)
