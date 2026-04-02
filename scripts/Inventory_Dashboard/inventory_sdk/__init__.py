"""Ericsson NCM Inventory SDK — query routers, devices, and licenses."""

from .client import InventoryClient
from .models import (
    Account,
    AssetEndpoint,
    Firmware,
    Group,
    LicenseStatus,
    NetDevice,
    PaginatedResponse,
    Product,
    Router,
    SoftwareLicense,
    Subscription,
    SubscriptionInfo,
)
from .exceptions import (
    AuthenticationError,
    BadRequestError,
    CradlepointSDKError,
    NotFoundError,
    RateLimitError,
)
from .filters import FilterBuilder
from .snapshot import enrich_from_snapshot, load_snapshot, save_snapshot
from .html_report import generate_html_report, generate_loading_html, update_progress_html

__all__ = [
    "InventoryClient",
    "Account",
    "AssetEndpoint",
    "Firmware",
    "Group",
    "LicenseStatus",
    "NetDevice",
    "PaginatedResponse",
    "Product",
    "Router",
    "SoftwareLicense",
    "Subscription",
    "SubscriptionInfo",
    "AuthenticationError",
    "BadRequestError",
    "CradlepointSDKError",
    "NotFoundError",
    "RateLimitError",
    "FilterBuilder",
    "enrich_from_snapshot",
    "load_snapshot",
    "save_snapshot",
    "generate_html_report",
    "generate_loading_html",
    "update_progress_html",
]

__version__ = "0.1.0"
