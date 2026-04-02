"""Main SDK client for the Ericsson NCM Inventory API.

Wraps the NCM v2 REST API with typed models and automatic pagination.
API docs: https://developer.cradlepoint.com
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from .exceptions import (
    AuthenticationError,
    BadRequestError,
    CradlepointSDKError,
    NotFoundError,
    RateLimitError,
)
from .filters import FilterBuilder
from .models import (
    Account,
    AssetEndpoint,
    Firmware,
    Group,
    LicenseStatus,
    NetDevice,
    Product,
    Router,
    SoftwareLicense,
    Subscription,
    SubscriptionInfo,
)
from .subscription_types import resolve_subscription_type, EXCLUDED_SUBSCRIPTIONS, is_pool_subscription

_DEFAULT_BASE_URL_V2 = "https://www.cradlepointecm.com/api/v2"
_DEFAULT_BASE_URL_V3 = "https://api.cradlepointecm.com/api/v3"
_DEFAULT_LIMIT = 500
_V3_MAX_PAGE_SIZE = 50

_RETRYABLE_STATUSES = {429, 409, 500, 502, 503, 504}

_ERROR_MAP: dict[int, type[CradlepointSDKError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: AuthenticationError,
    404: NotFoundError,
    429: RateLimitError,
}


class InventoryClient:
    """Read-only client for querying Ericsson NCM inventory.

    Supports both v2 (API keys) and v3 (bearer token) endpoints.

    Args:
        cp_api_id: X-CP-API-ID key (v2 auth).
        cp_api_key: X-CP-API-KEY key (v2 auth).
        ecm_api_id: X-ECM-API-ID key (v2 auth).
        ecm_api_key: X-ECM-API-KEY key (v2 auth).
        v3_bearer_token: Bearer token for v3 API (asset_endpoints, subscriptions).
        base_url_v2: NCM API v2 base URL.
        base_url_v3: NCM API v3 base URL.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        cp_api_id: str,
        cp_api_key: str,
        ecm_api_id: str,
        ecm_api_key: str,
        *,
        v3_bearer_token: str | None = None,
        base_url_v2: str = _DEFAULT_BASE_URL_V2,
        base_url_v3: str = _DEFAULT_BASE_URL_V3,
        timeout: float = 30.0,
        max_retries: int = 5,
        retry_backoff: float = 1.0,
    ) -> None:
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._log = logging.getLogger("inventory_sdk")
        # v2 client (API key auth)
        v2_headers = {
            "X-CP-API-ID": cp_api_id,
            "X-CP-API-KEY": cp_api_key,
            "X-ECM-API-ID": ecm_api_id,
            "X-ECM-API-KEY": ecm_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._base_url_v2 = base_url_v2.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url_v2,
            headers=v2_headers,
            timeout=timeout,
        )

        # v3 client (bearer token auth)
        self._v3_client: httpx.Client | None = None
        self._async_v2: httpx.AsyncClient | None = None
        self._async_v3: httpx.AsyncClient | None = None
        self._v2_headers = v2_headers
        self._timeout = timeout
        if v3_bearer_token:
            v3_headers = {
                "Authorization": f"Bearer {v3_bearer_token}",
                "Accept": "application/vnd.api+json",
            }
            self._base_url_v3 = base_url_v3.rstrip("/")
            self._v3_client = httpx.Client(
                base_url=self._base_url_v3,
                headers=v3_headers,
                timeout=timeout,
            )
            self._v3_headers = v3_headers
        else:
            self._v3_headers: dict[str, str] = {}

    # -- internal helpers ------------------------------------------------------

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        exc_cls = _ERROR_MAP.get(response.status_code, CradlepointSDKError)
        raise exc_cls(
            message=response.text,
            status_code=response.status_code,
        )

    def _request_with_retry(
        self, client: httpx.Client, url: str, params: dict[str, Any]
    ) -> httpx.Response:
        """Make a GET request with automatic retry on 429/409 rate limits."""
        for attempt in range(self._max_retries + 1):
            resp = client.get(url, params=params)
            if resp.status_code not in _RETRYABLE_STATUSES:
                self._raise_for_status(resp)
                return resp
            # Rate limited or 409 conflict — back off and retry
            retry_after = resp.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else self._retry_backoff * (2 ** attempt)
            self._log.warning(
                "Rate limited (%d), retrying in %.1fs (attempt %d/%d)",
                resp.status_code, wait, attempt + 1, self._max_retries,
            )
            time.sleep(wait)
        # Final attempt failed
        self._raise_for_status(resp)
        return resp  # unreachable but keeps type checker happy

    @staticmethod
    def _resolve_params(
        filters: FilterBuilder | dict[str, Any] | None,
    ) -> dict[str, Any]:
        if filters is None:
            return {}
        if isinstance(filters, FilterBuilder):
            return filters.build()
        return dict(filters)

    def _get_paged(
        self,
        path: str,
        params: dict[str, Any],
        *,
        limit: int | str = _DEFAULT_LIMIT,
    ) -> list[dict[str, Any]]:
        """Fetch all pages of results, respecting the NCM pagination model."""
        if "limit" not in params:
            params["limit"] = limit if limit != "all" else 1_000_000

        all_limit = int(params["limit"])
        results: list[dict[str, Any]] = []
        url: str | None = f"{path}/"
        page = 0

        while url and len(results) < all_limit:
            resp = self._request_with_retry(self._client, url, params)
            body = resp.json()
            batch = body.get("data", [])
            results.extend(batch)
            page += 1
            if page % 10 == 0 or len(results) >= all_limit:
                self._log.info("%s: fetched %d records (%d pages)", path, len(results), page)
            url = body.get("meta", {}).get("next")
            params = None

        if page > 1:
            self._log.info("%s: completed — %d records (%d pages)", path, len(results), page)
        return results[:all_limit]

    # -- routers ---------------------------------------------------------------

    def get_routers(
        self,
        filters: FilterBuilder | dict[str, Any] | None = None,
        *,
        limit: int | str = _DEFAULT_LIMIT,
    ) -> list[Router]:
        """List routers/devices with optional filters.

        Common filters: account, group, id, id__in, name, name__in,
        mac, mac__in, state, state__in, device_type, reboot_required,
        state_updated_at__gt/lt, updated_at__gt/lt, expand, order_by.
        """
        params = self._resolve_params(filters)
        data = self._get_paged("/routers", params, limit=limit)
        return [Router(**r) for r in data]

    def get_router_by_id(self, router_id: str | int) -> Router:
        """Get a single router by ID."""
        results = self.get_routers({"id": router_id}, limit=1)
        if not results:
            raise NotFoundError(f"Router {router_id} not found", status_code=404)
        return results[0]

    def get_router_by_name(self, name: str) -> Router:
        """Get a single router by name."""
        results = self.get_routers({"name": name}, limit=1)
        if not results:
            raise NotFoundError(f"Router '{name}' not found", status_code=404)
        return results[0]

    # -- net devices -----------------------------------------------------------

    def get_net_devices(
        self,
        filters: FilterBuilder | dict[str, Any] | None = None,
        *,
        limit: int | str = _DEFAULT_LIMIT,
    ) -> list[NetDevice]:
        """List network devices/interfaces.

        Common filters: account, connection_state, id, id__in, is_asset,
        ipv4_address, mode, router, router__in, expand.
        """
        params = self._resolve_params(filters)
        data = self._get_paged("/net_devices", params, limit=limit)
        return [NetDevice(**d) for d in data]

    def get_net_devices_for_router(
        self, router_id: str | int, **kwargs: Any
    ) -> list[NetDevice]:
        """Get all net devices for a specific router."""
        return self.get_net_devices({"router": router_id, **kwargs})

    # -- accounts --------------------------------------------------------------

    def get_accounts(
        self,
        filters: FilterBuilder | dict[str, Any] | None = None,
        *,
        limit: int | str = _DEFAULT_LIMIT,
    ) -> list[Account]:
        """List accounts."""
        params = self._resolve_params(filters)
        data = self._get_paged("/accounts", params, limit=limit)
        return [Account(**a) for a in data]

    def get_account_by_id(self, account_id: str | int) -> Account:
        """Get a single account by ID."""
        results = self.get_accounts({"id": account_id}, limit=1)
        if not results:
            raise NotFoundError(f"Account {account_id} not found", status_code=404)
        return results[0]

    # -- groups ----------------------------------------------------------------

    def get_groups(
        self,
        filters: FilterBuilder | dict[str, Any] | None = None,
        *,
        limit: int | str = _DEFAULT_LIMIT,
    ) -> list[Group]:
        """List device groups."""
        params = self._resolve_params(filters)
        data = self._get_paged("/groups", params, limit=limit)
        return [Group(**g) for g in data]

    def get_group_by_id(self, group_id: str | int) -> Group:
        """Get a single group by ID."""
        results = self.get_groups({"id": group_id}, limit=1)
        if not results:
            raise NotFoundError(f"Group {group_id} not found", status_code=404)
        return results[0]

    def get_group_by_name(self, name: str) -> Group:
        """Get a single group by name."""
        results = self.get_groups({"name": name}, limit=1)
        if not results:
            raise NotFoundError(f"Group '{name}' not found", status_code=404)
        return results[0]

    # -- products --------------------------------------------------------------

    def get_products(
        self,
        filters: FilterBuilder | dict[str, Any] | None = None,
        *,
        limit: int | str = _DEFAULT_LIMIT,
    ) -> list[Product]:
        """List Ericsson product models."""
        params = self._resolve_params(filters)
        data = self._get_paged("/products", params, limit=limit)
        return [Product(**p) for p in data]

    def get_product_by_id(self, product_id: str | int) -> Product:
        """Get a single product by ID."""
        results = self.get_products({"id": product_id}, limit=1)
        if not results:
            raise NotFoundError(f"Product {product_id} not found", status_code=404)
        return results[0]

    # -- firmwares -------------------------------------------------------------

    def get_firmwares(
        self,
        filters: FilterBuilder | dict[str, Any] | None = None,
        *,
        limit: int | str = _DEFAULT_LIMIT,
    ) -> list[Firmware]:
        """List firmware versions."""
        params = self._resolve_params(filters)
        data = self._get_paged("/firmwares", params, limit=limit)
        return [Firmware(**f) for f in data]

    # -- v3 helpers ------------------------------------------------------------

    def _require_v3(self) -> httpx.Client:
        """Return the v3 client or raise if no bearer token was provided."""
        if self._v3_client is None:
            raise CradlepointSDKError(
                "v3 bearer token required. Pass v3_bearer_token to the constructor."
            )
        return self._v3_client

    @staticmethod
    def _parse_v3_relationships(raw: dict[str, Any]) -> dict[str, Any]:
        """Extract relationship IDs from JSON:API relationship objects."""
        flat: dict[str, Any] = {}
        rels = raw.get("relationships", {})
        if "tenants" in rels:
            tenant_data = rels["tenants"].get("data")
            if isinstance(tenant_data, dict):
                flat["tenant_id"] = tenant_data.get("id")
            elif isinstance(tenant_data, list) and tenant_data:
                flat["tenant_id"] = tenant_data[0].get("id")
        if "subscriptions" in rels:
            sub_data = rels["subscriptions"].get("data")
            if isinstance(sub_data, dict):
                flat["subscription_id"] = sub_data.get("id")
            elif isinstance(sub_data, list) and sub_data:
                flat["subscription_id"] = sub_data[0].get("id")
                flat["subscription_ids"] = [s.get("id") for s in sub_data]
        if "subscription_type" in rels:
            st_data = rels["subscription_type"].get("data")
            if isinstance(st_data, dict):
                flat["subscription_type_id"] = st_data.get("id")
            elif isinstance(st_data, list) and st_data:
                flat["subscription_type_id"] = st_data[0].get("id")
        if "asset_endpoints" in rels:
            flat["asset_endpoints_link"] = (
                rels["asset_endpoints"].get("links", {}).get("self")
            )
        # Remaining relationships
        if "tenant" in rels:
            t_data = rels["tenant"].get("data")
            if isinstance(t_data, dict):
                flat["tenant_id"] = flat.get("tenant_id") or t_data.get("id")
        return flat

    def _get_paged_v3(
        self,
        path: str,
        params: dict[str, Any],
        *,
        max_records: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all pages from a v3 cursor-paginated endpoint.

        v3 uses ``page[after]``/``page[before]`` cursors and
        ``links.next`` for the next page URL. Max page size is 50.
        """
        client = self._require_v3()
        if "page[size]" not in params:
            params["page[size]"] = _V3_MAX_PAGE_SIZE

        results: list[dict[str, Any]] = []
        url: str | None = path
        page = 0

        while url:
            resp = self._request_with_retry(client, url, params)
            body = resp.json()

            for item in body.get("data", []):
                attrs = item.get("attributes", item)
                record = {"id": item.get("id"), **attrs}
                record.update(self._parse_v3_relationships(item))
                results.append(record)

            page += 1
            if page % 20 == 0 or (max_records and len(results) >= max_records):
                self._log.info("%s: fetched %d records (%d pages)", path, len(results), page)

            if max_records and len(results) >= max_records:
                return results[:max_records]

            url = body.get("links", {}).get("next")
            # After first request, params are in the cursor URL
            params = None

        if page > 1:
            self._log.info("%s: completed — %d records (%d pages)", path, len(results), page)
        return results

    # -- async helpers for concurrent fetching ---------------------------------

    def _ensure_async_clients(self) -> tuple[httpx.AsyncClient, httpx.AsyncClient | None]:
        """Lazily create async HTTP clients mirroring the sync ones."""
        if self._async_v2 is None:
            self._async_v2 = httpx.AsyncClient(
                base_url=self._base_url_v2,
                headers=self._v2_headers,
                timeout=self._timeout,
            )
        v3 = None
        if self._v3_client and self._async_v3 is None:
            self._async_v3 = httpx.AsyncClient(
                base_url=self._base_url_v3,
                headers=self._v3_headers,
                timeout=self._timeout,
            )
        v3 = self._async_v3
        # Semaphore limits concurrent requests to stay under 500 calls/min
        if not hasattr(self, "_semaphore") or self._semaphore is None:
            self._semaphore = asyncio.Semaphore(4)
        return self._async_v2, v3

    async def _async_request_with_retry(
        self, client: httpx.AsyncClient, url: str, params: dict[str, Any]
    ) -> httpx.Response:
        """Async GET with automatic retry on 429/409 and rate throttling."""
        async with self._semaphore:
            for attempt in range(self._max_retries + 1):
                resp = await client.get(url, params=params)
                if resp.status_code not in _RETRYABLE_STATUSES:
                    self._raise_for_status(resp)
                    # Small delay between requests to stay under 500/min
                    await asyncio.sleep(0.15)
                    return resp
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else self._retry_backoff * (2 ** attempt)
                self._log.warning(
                    "Rate limited (%d), retrying in %.1fs (attempt %d/%d)",
                    resp.status_code, wait, attempt + 1, self._max_retries,
                )
                await asyncio.sleep(wait)
            self._raise_for_status(resp)
            return resp

    async def _async_get_paged(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, Any],
        *,
        limit: int | str = _DEFAULT_LIMIT,
    ) -> list[dict[str, Any]]:
        """Async version of _get_paged for v2 endpoints."""
        if "limit" not in params:
            params["limit"] = limit if limit != "all" else 1_000_000

        all_limit = int(params["limit"])
        results: list[dict[str, Any]] = []
        url: str | None = f"{path}/"
        page = 0

        while url and len(results) < all_limit:
            resp = await self._async_request_with_retry(client, url, params)
            body = resp.json()
            results.extend(body.get("data", []))
            page += 1
            if page % 10 == 0 or len(results) >= all_limit:
                self._log.info("%s: fetched %d records (%d pages)", path, len(results), page)
            url = body.get("meta", {}).get("next")
            params = None

        if page > 1:
            self._log.info("%s: completed — %d records (%d pages)", path, len(results), page)
        return results[:all_limit]

    async def _async_get_paged_v3(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, Any],
        *,
        max_records: int | None = None,
    ) -> list[dict[str, Any]]:
        """Async version of _get_paged_v3 for v3 cursor-paginated endpoints."""
        if "page[size]" not in params:
            params["page[size]"] = _V3_MAX_PAGE_SIZE

        results: list[dict[str, Any]] = []
        url: str | None = path
        page = 0

        while url:
            resp = await self._async_request_with_retry(client, url, params)
            body = resp.json()

            for item in body.get("data", []):
                attrs = item.get("attributes", item)
                record = {"id": item.get("id"), **attrs}
                record.update(self._parse_v3_relationships(item))
                results.append(record)

            page += 1
            if page % 20 == 0 or (max_records and len(results) >= max_records):
                self._log.info("%s: fetched %d records (%d pages)", path, len(results), page)

            if max_records and len(results) >= max_records:
                return results[:max_records]

            url = body.get("links", {}).get("next")
            params = None

        if page > 1:
            self._log.info("%s: completed — %d records (%d pages)", path, len(results), page)
        return results

    # -- asset endpoints (v3) --------------------------------------------------

    def get_asset_endpoints(
        self,
        *,
        hardware_series: str | None = None,
        hardware_series_key: str | None = None,
        mac_address: str | None = None,
        serial_number: str | None = None,
        subscription: str | None = None,
        max_records: int | None = None,
    ) -> list[AssetEndpoint]:
        """List all routers/adapters from the v3 asset_endpoints API.

        Filters map to the v3 filter[] query params.
        """
        params: dict[str, Any] = {}
        if hardware_series:
            params["filter[hardware_series]"] = hardware_series
        if hardware_series_key:
            params["filter[hardware_series_key]"] = hardware_series_key
        if mac_address:
            params["filter[mac_address]"] = mac_address
        if serial_number:
            params["filter[serial_number]"] = serial_number
        if subscription:
            params["filter[subscription]"] = subscription

        data = self._get_paged_v3(
            "/asset_endpoints", params, max_records=max_records
        )
        return [AssetEndpoint(**d) for d in data]

    # -- subscriptions (v3) ----------------------------------------------------

    def get_subscriptions(
        self,
        *,
        start_time: str | None = None,
        end_time: str | None = None,
        max_records: int | None = None,
    ) -> list[Subscription]:
        """List subscriptions from the v3 subscriptions API.

        Args:
            start_time: ISO datetime filter (e.g. '2025-01-01T00:00:00Z').
            end_time: ISO datetime filter.
        """
        params: dict[str, Any] = {}
        if start_time:
            params["filter[start_time]"] = start_time
        if end_time:
            params["filter[end_time]"] = end_time

        data = self._get_paged_v3(
            "/subscriptions", params, max_records=max_records
        )
        return [Subscription(**d) for d in data]

    # -- combined license status -----------------------------------------------

    def get_license_status(
        self,
        progress_callback: Any = None,
    ) -> tuple[list[LicenseStatus], list[SoftwareLicense]]:
        """Build a combined view of all devices and their license status.

        Uses v3 asset_endpoints as the primary source so that devices
        without a v2 router (e.g. unlicensed/unassigned) still appear.
        Left-joins v2 routers, net_devices, groups, and accounts by
        normalized MAC address.

        Fetches all data sources concurrently for speed.
        Requires both v2 API keys and a v3 bearer token.

        Returns:
            A tuple of (device_statuses, software_licenses).

        Args:
            progress_callback: Optional callable(step_index, detail_str)
                called as each data source completes. Useful for updating
                a loading page.
        """
        cb = progress_callback or (lambda step, detail: None)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return self._get_license_status_sync(cb)

        return asyncio.run(self._get_license_status_async(cb))

    def _get_license_status_sync(self, cb: Any) -> tuple[list[LicenseStatus], list[SoftwareLicense]]:
        """Synchronous (sequential) license status build — fallback path."""
        self._log.info("Starting license status build (sync)…")
        t0 = time.time()

        cb(0, "loading…")
        self._log.info("Step 1/5: Fetching v3 asset_endpoints…")
        assets = self.get_asset_endpoints()
        self._log.info("  → %d asset_endpoints (%.1fs)", len(assets), time.time() - t0)

        cb(1, "loading…")
        self._log.info("Step 2/5: Fetching v3 subscriptions…")
        subs = self.get_subscriptions()
        self._log.info("  → %d subscriptions (%.1fs)", len(subs), time.time() - t0)

        cb(2, "loading…")
        self._log.info("Step 3/5: Fetching v2 routers…")
        routers = self.get_routers(limit="all")
        self._log.info("  → %d routers (%.1fs)", len(routers), time.time() - t0)

        cb(3, "loading…")
        self._log.info("Step 4/5: Fetching v2 net_devices…")
        net_devices = self.get_net_devices({"is_asset": True}, limit="all")
        self._log.info("  → %d net_devices (%.1fs)", len(net_devices), time.time() - t0)

        cb(4, "loading…")
        self._log.info("Step 5/5: Fetching v2 groups & accounts…")
        groups = self.get_groups(limit="all")
        accounts = self.get_accounts(limit="all")
        self._log.info("  → %d groups, %d accounts (%.1fs)", len(groups), len(accounts), time.time() - t0)

        cb(5, "joining data…")
        return self._join_license_data(assets, subs, routers, net_devices, groups, accounts, t0)

    async def _get_license_status_async(self, cb: Any) -> tuple[list[LicenseStatus], list[SoftwareLicense]]:
        """Async concurrent license status build — all 5 fetches in parallel."""
        self._log.info("Starting license status build (concurrent)…")
        t0 = time.time()

        v2, v3 = self._ensure_async_clients()
        if v3 is None:
            raise CradlepointSDKError(
                "v3 bearer token required. Pass v3_bearer_token to the constructor."
            )

        # Track which steps have completed for progress reporting
        completed: list[bool] = [False] * 6

        def _mark_done(step: int, detail: str) -> None:
            completed[step] = True
            # Find the next incomplete step to show as active
            next_step = next((i for i in range(6) if not completed[i]), 5)
            cb(next_step, detail)

        async def fetch_assets() -> list[dict[str, Any]]:
            self._log.info("  ↳ Fetching v3 asset_endpoints…")
            data = await self._async_get_paged_v3(v3, "/asset_endpoints", {})
            self._log.info("  ✓ %d asset_endpoints (%.1fs)", len(data), time.time() - t0)
            _mark_done(0, f"{len(data)} asset endpoints fetched")
            return data

        async def fetch_subs() -> list[dict[str, Any]]:
            self._log.info("  ↳ Fetching v3 subscriptions…")
            data = await self._async_get_paged_v3(v3, "/subscriptions", {})
            self._log.info("  ✓ %d subscriptions (%.1fs)", len(data), time.time() - t0)
            _mark_done(1, f"{len(data)} subscriptions fetched")
            return data

        async def fetch_routers() -> list[dict[str, Any]]:
            self._log.info("  ↳ Fetching v2 routers…")
            data = await self._async_get_paged(v2, "/routers", {"limit": 1_000_000})
            self._log.info("  ✓ %d routers (%.1fs)", len(data), time.time() - t0)
            _mark_done(2, f"{len(data)} routers fetched")
            return data

        async def fetch_net_devices() -> list[dict[str, Any]]:
            self._log.info("  ↳ Fetching v2 net_devices…")
            data = await self._async_get_paged(v2, "/net_devices", {"is_asset": "true", "limit": 1_000_000})
            self._log.info("  ✓ %d net_devices (%.1fs)", len(data), time.time() - t0)
            _mark_done(3, f"{len(data)} net devices fetched")
            return data

        async def fetch_groups_accounts() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
            self._log.info("  ↳ Fetching v2 groups & accounts…")
            g, a = await asyncio.gather(
                self._async_get_paged(v2, "/groups", {"limit": 1_000_000}),
                self._async_get_paged(v2, "/accounts", {"limit": 1_000_000}),
            )
            self._log.info("  ✓ %d groups, %d accounts (%.1fs)", len(g), len(a), time.time() - t0)
            _mark_done(4, f"{len(g)} groups, {len(a)} accounts fetched")
            return g, a

        # Write initial progress
        cb(0, "starting concurrent fetch…")

        # Fire all 5 streams concurrently
        (
            asset_data,
            sub_data,
            router_data,
            nd_data,
            (group_data, account_data),
        ) = await asyncio.gather(
            fetch_assets(),
            fetch_subs(),
            fetch_routers(),
            fetch_net_devices(),
            fetch_groups_accounts(),
        )

        self._log.info("All data fetched in %.1fs — joining…", time.time() - t0)
        cb(5, "resolving subscriptions…")

        # Collect unique subscription IDs referenced by asset_endpoints
        # These are assignment IDs that differ from the parent subscription IDs
        # returned by /subscriptions without filter. We must look them up via filter[id].
        all_asset_sub_ids: set[str] = set()
        for d in asset_data:
            for sid in d.get("subscription_ids", []):
                if sid:
                    all_asset_sub_ids.add(sid)
            if d.get("subscription_id"):
                all_asset_sub_ids.add(d["subscription_id"])

        # Batch-fetch subscription details for these IDs (max 50 per filter)
        extra_sub_data: list[dict[str, Any]] = []
        id_list = list(all_asset_sub_ids)
        batch_size = 50
        for i in range(0, len(id_list), batch_size):
            batch = ",".join(id_list[i:i + batch_size])
            data = await self._async_get_paged_v3(v3, "/subscriptions", {"filter[id]": batch})
            extra_sub_data.extend(data)
        self._log.info("Resolved %d assignment subscriptions from %d unique IDs (%.1fs)",
                        len(extra_sub_data), len(all_asset_sub_ids), time.time() - t0)

        # Close async clients
        await v2.aclose()
        if self._async_v3:
            await self._async_v3.aclose()
        self._async_v2 = None
        self._async_v3 = None

        # Convert raw dicts to models
        assets = [AssetEndpoint(**d) for d in asset_data]
        # Merge parent subs (from unfiltered fetch) with resolved assignment subs
        all_sub_data = sub_data + extra_sub_data
        subs = [Subscription(**d) for d in all_sub_data]
        routers = [Router(**r) for r in router_data]
        net_devices = [NetDevice(**d) for d in nd_data]
        groups = [Group(**g) for g in group_data]
        accounts = [Account(**a) for a in account_data]

        return self._join_license_data(assets, subs, routers, net_devices, groups, accounts, t0)

    def _join_license_data(
        self,
        assets: list[AssetEndpoint],
        subs: list[Subscription],
        routers: list[Router],
        net_devices: list[NetDevice],
        groups: list[Group],
        accounts: list[Account],
        t0: float,
    ) -> tuple[list[LicenseStatus], list[SoftwareLicense]]:
        """Join all fetched data into LicenseStatus rows and build software license inventory."""
        sub_by_id: dict[str, Subscription] = {s.id: s for s in subs}

        # Count how many asset endpoints are assigned to each subscription
        sub_assigned_count: dict[str, int] = {}
        for asset in assets:
            all_ids = asset.subscription_ids if asset.subscription_ids else ([asset.subscription_id] if asset.subscription_id else [])
            for sid in all_ids:
                if sid:
                    sub_assigned_count[sid] = sub_assigned_count.get(sid, 0) + 1

        router_by_mac: dict[str, Router] = {}
        router_by_serial: dict[str, Router] = {}
        for r in routers:
            if r.mac:
                norm = r.mac.upper().replace(":", "").replace("-", "")
                router_by_mac[norm] = r
            if r.serial_number:
                router_by_serial[r.serial_number] = r

        modem_by_router: dict[str, NetDevice] = {}
        for nd in net_devices:
            if nd.router and nd.router not in modem_by_router:
                modem_by_router[nd.router] = nd

        group_by_url: dict[str, Group] = {}
        for g in groups:
            if g.resource_url:
                group_by_url[g.resource_url] = g

        account_by_url: dict[str, Account] = {}
        for a in accounts:
            if a.resource_url:
                account_by_url[a.resource_url] = a

        self._log.info("Joining %d assets with %d routers…", len(assets), len(routers))
        seen_macs: set[str] = set()
        results: list[LicenseStatus] = []

        def _license_state(base_sub: Subscription | None, has_router: bool) -> tuple[bool, str, bool]:
            if base_sub is None:
                return False, "unlicensed", False
            if base_sub.name == "NON-COMPLIANT":
                if not has_router:
                    return False, "unlicensed", False
                return False, "grace-period", True
            return True, "licensed", True

        for asset in assets:
            mac_raw = asset.mac_address or ""
            mac_norm = mac_raw.upper().replace(":", "").replace("-", "")
            seen_macs.add(mac_norm)

            router = router_by_mac.get(mac_norm)
            if not router and asset.serial_number:
                router = router_by_serial.get(asset.serial_number)
            modem = modem_by_router.get(router.resource_url or "") if router else None
            grp = group_by_url.get(router.group or "") if router else None
            acct = account_by_url.get(router.account or "") if router else None

            all_sub_ids: list[str] = []
            if asset.subscription_ids:
                all_sub_ids = asset.subscription_ids
            elif asset.subscription_id:
                all_sub_ids = [asset.subscription_id]

            matched_subs = [sub_by_id[sid] for sid in all_sub_ids if sid in sub_by_id]
            base = matched_subs[0] if matched_subs else None
            add_ons = [
                SubscriptionInfo(
                    subscription_id=s.id,
                    subscription_name=s.name,
                    subscription_type=resolve_subscription_type(s.name),
                    start_time=s.start_time,
                    end_time=s.end_time,
                )
                for s in matched_subs[1:]
            ]

            raw_mac = router.mac if router else asset.mac_address or ""
            clean = raw_mac.upper().replace(":", "").replace("-", "")
            display_mac = ":".join(clean[i:i+2] for i in range(0, 12, 2)) if len(clean) == 12 else raw_mac
            is_licensed, license_state, show_sub = _license_state(base, router is not None)

            results.append(
                LicenseStatus(
                    router_id=router.id if router else "",
                    router_name=router.name if router else None,
                    mac=display_mac,
                    serial_number=asset.serial_number or (router.serial_number if router else None),
                    hardware_series=asset.hardware_series,
                    device_type=router.device_type if router else None,
                    full_product_name=router.full_product_name if router else None,
                    state=router.state if router else None,
                    config_status=router.config_status if router else None,
                    ipv4_address=router.ipv4_address if router else None,
                    locality=router.locality if router else None,
                    last_known_location=router.last_known_location if router else None,
                    account_name=acct.name if acct else None,
                    group_name=grp.name if grp else None,
                    actual_firmware=router.actual_firmware if router else None,
                    target_firmware=router.target_firmware if router else None,
                    upgrade_pending=router.upgrade_pending if router else None,
                    reboot_required=router.reboot_required if router else None,
                    description=router.description if router else None,
                    custom1=router.custom1 if router else None,
                    custom2=router.custom2 if router else None,
                    imei=modem.imei if modem else None,
                    iccid=modem.iccid if modem else None,
                    imsi=modem.imsi if modem else None,
                    mdn=modem.mdn if modem else None,
                    meid=modem.meid if modem else None,
                    carrier=modem.carrier if modem else None,
                    carrier_id=modem.carrier_id if modem else None,
                    modem_name=modem.name if modem else None,
                    modem_fw=modem.modem_fw if modem else None,
                    mfg_model=modem.mfg_model if modem else None,
                    mfg_product=modem.mfg_product if modem else None,
                    connection_state=modem.connection_state if modem else None,
                    service_type=modem.service_type if modem else None,
                    rfband=modem.rfband if modem else None,
                    ltebandwidth=modem.ltebandwidth if modem else None,
                    homecarrid=modem.homecarrid if modem else None,
                    is_licensed=is_licensed,
                    license_state=license_state,
                    state_updated_at=router.state_updated_at if router else None,
                    subscription_id=base.id if base and show_sub else None,
                    subscription_name=base.name if base and show_sub else None,
                    subscription_type=resolve_subscription_type(base.name) if base and show_sub else None,
                    subscription_start=base.start_time if base and show_sub else None,
                    subscription_end=base.end_time if base and show_sub else None,
                    add_ons=add_ons if show_sub else [],
                    created_at=router.created_at if router else None,
                    updated_at=router.updated_at if router else None,
                )
            )

        # Include any v2 routers that don't have a v3 asset_endpoint
        for r in routers:
            mac_norm = (r.mac or "").upper().replace(":", "").replace("-", "")
            if mac_norm and mac_norm in seen_macs:
                continue
            modem = modem_by_router.get(r.resource_url or "")
            grp = group_by_url.get(r.group or "")
            acct = account_by_url.get(r.account or "")
            results.append(
                LicenseStatus(
                    router_id=r.id,
                    router_name=r.name,
                    mac=r.mac,
                    serial_number=r.serial_number,
                    device_type=r.device_type,
                    full_product_name=r.full_product_name,
                    state=r.state,
                    config_status=r.config_status,
                    ipv4_address=r.ipv4_address,
                    locality=r.locality,
                    last_known_location=r.last_known_location,
                    account_name=acct.name if acct else None,
                    group_name=grp.name if grp else None,
                    actual_firmware=r.actual_firmware,
                    target_firmware=r.target_firmware,
                    upgrade_pending=r.upgrade_pending,
                    reboot_required=r.reboot_required,
                    description=r.description,
                    custom1=r.custom1,
                    custom2=r.custom2,
                    imei=modem.imei if modem else None,
                    iccid=modem.iccid if modem else None,
                    imsi=modem.imsi if modem else None,
                    mdn=modem.mdn if modem else None,
                    meid=modem.meid if modem else None,
                    carrier=modem.carrier if modem else None,
                    carrier_id=modem.carrier_id if modem else None,
                    modem_name=modem.name if modem else None,
                    modem_fw=modem.modem_fw if modem else None,
                    mfg_model=modem.mfg_model if modem else None,
                    mfg_product=modem.mfg_product if modem else None,
                    connection_state=modem.connection_state if modem else None,
                    service_type=modem.service_type if modem else None,
                    rfband=modem.rfband if modem else None,
                    ltebandwidth=modem.ltebandwidth if modem else None,
                    homecarrid=modem.homecarrid if modem else None,
                    is_licensed=False,
                    license_state="unlicensed",
                    state_updated_at=r.state_updated_at,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )

        self._log.info("License status complete: %d devices (%.1fs total)", len(results), time.time() - t0)

        # Build software license inventory from all subscriptions
        sw_licenses: list[SoftwareLicense] = []
        for sub in subs:
            if sub.name in EXCLUDED_SUBSCRIPTIONS:
                continue
            pool = is_pool_subscription(sub.name)
            sw_licenses.append(
                SoftwareLicense(
                    subscription_id=sub.id,
                    subscription_name=sub.name,
                    subscription_type=resolve_subscription_type(sub.name),
                    quantity=sub.quantity,
                    assigned=-1 if pool else sub_assigned_count.get(sub.id, 0),
                    start_time=sub.start_time,
                    end_time=sub.end_time,
                )
            )
        self._log.info("Software licenses: %d subscriptions", len(sw_licenses))

        return results, sw_licenses

    # -- lifecycle -------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP connections."""
        self._client.close()
        if self._v3_client:
            self._v3_client.close()

    def __enter__(self) -> InventoryClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
