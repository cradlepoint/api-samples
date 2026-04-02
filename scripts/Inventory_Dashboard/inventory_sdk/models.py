"""Pydantic models for Ericsson NCM API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Router(BaseModel):
    """An Ericsson router/device."""

    id: str
    name: str | None = None
    mac: str | None = None
    device_type: str | None = None
    ipv4_address: str | None = None
    state: str | None = None
    state_updated_at: datetime | None = None
    group: str | None = None
    account: str | None = None
    product: str | None = None
    actual_firmware: str | None = None
    target_firmware: str | None = None
    firmware_version: str | None = None
    full_product_name: str | None = None
    config_status: str | None = None
    custom1: str | None = None
    custom2: str | None = None
    asset_id: str | None = None
    reboot_required: bool | None = None
    upgrade_pending: bool | None = None
    serial_number: str | None = None
    description: str | None = None
    locality: str | None = None
    last_known_location: Any | None = None
    configuration_manager: str | None = None
    lans: str | None = None
    overlay_network_binding: str | None = None
    updated_at: datetime | None = None
    created_at: datetime | None = None
    resource_url: str | None = None


class NetDevice(BaseModel):
    """A network device/interface on a router."""

    id: str
    account: str | None = None
    bsid: str | None = None
    carrier: str | None = None
    carrier_id: str | None = None
    channel: str | None = None
    connection_state: str | None = None
    dns0: str | None = None
    dns1: str | None = None
    esn: str | None = None
    gateway: str | None = None
    gsn: str | None = None
    homecarrid: str | None = None
    hostname: str | None = None
    iccid: str | None = None
    imei: str | None = None
    imsi: str | None = None
    ipv4_address: str | None = None
    ipv6_address: str | None = None
    is_asset: bool | None = None
    ltebandwidth: str | None = None
    mdn: str | None = None
    meid: str | None = None
    mfg_model: str | None = None
    mfg_product: str | None = None
    mil: str | None = None
    mode: str | None = None
    modem_fw: str | None = None
    mtu: int | None = None
    name: str | None = None
    neid: str | None = None
    netmask: str | None = None
    pin_status: str | None = None
    port: str | None = None
    prlv: str | None = None
    profile: str | None = None
    rfband: str | None = None
    rnc: str | None = None
    router: str | None = None
    rxchannel: str | None = None
    serial: str | None = None
    service_type: str | None = None
    ssid: str | None = None
    summary: str | None = None
    txchannel: str | None = None
    type: str | None = None
    uid: str | None = None
    updated_at: datetime | None = None
    uptime: float | None = None
    resource_url: str | None = None


class Account(BaseModel):
    """An Ericsson NCM account."""

    id: str
    name: str | None = None
    account: str | None = None
    is_disabled: bool | None = None
    resource_url: str | None = None


class Group(BaseModel):
    """A device group."""

    id: str
    name: str | None = None
    account: str | None = None
    product: str | None = None
    device_type: str | None = None
    target_firmware: str | None = None
    configuration: Any | None = None
    resource_url: str | None = None


class Product(BaseModel):
    """An Ericsson product/model."""

    id: str
    name: str | None = None
    device_type: str | None = None
    series: int | None = None
    resource_url: str | None = None


class Firmware(BaseModel):
    """A firmware version."""

    id: str
    version: str | None = None
    product: str | None = None
    hash: str | None = None
    url: str | None = None
    is_deprecated: bool | None = None
    built_at: datetime | None = None
    released_at: datetime | None = None
    uploaded_at: datetime | None = None
    expires_at: datetime | None = None
    default_configuration: str | None = None
    resource_url: str | None = None


class PaginatedResponse(BaseModel):
    """Wrapper for paginated NCM API v2 responses."""

    data: list[dict[str, Any]]
    meta: dict[str, Any] = Field(default_factory=dict)


# -- v3 models ----------------------------------------------------------------


class AssetEndpoint(BaseModel):
    """A physical device (router/adapter) from the v3 asset_endpoints API."""

    id: str
    serial_number: str | None = None
    mac_address: str | None = None
    hardware_series: str | None = None
    hardware_series_key: str | None = None
    created_date: datetime | None = None
    last_modified_date: datetime | None = None
    # Relationship IDs extracted from JSON:API relationships
    tenant_id: str | None = None
    subscription_id: str | None = None
    subscription_ids: list[str] = Field(default_factory=list)


class Subscription(BaseModel):
    """A software subscription/license from the v3 subscriptions API."""

    id: str
    name: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    quantity: int | None = None
    feature_list_id: str | None = None
    created_date: datetime | None = None
    last_modified_date: datetime | None = None
    # Relationship IDs
    tenant_id: str | None = None
    subscription_type_id: str | None = None
    # Link to associated asset_endpoints
    asset_endpoints_link: str | None = None


class SubscriptionInfo(BaseModel):
    """Summary of a single subscription attached to a device."""

    subscription_id: str
    subscription_name: str | None = None
    subscription_type: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class SoftwareLicense(BaseModel):
    """A subscription from the full software license inventory."""

    subscription_id: str
    subscription_name: str | None = None
    subscription_type: str | None = None
    quantity: int | None = None
    assigned: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None


class LicenseStatus(BaseModel):
    """Combined view showing a router's full inventory status."""

    router_id: str
    router_name: str | None = None
    mac: str | None = None
    serial_number: str | None = None
    hardware_series: str | None = None
    device_type: str | None = None
    full_product_name: str | None = None
    state: str | None = None
    config_status: str | None = None
    ipv4_address: str | None = None
    locality: str | None = None
    last_known_location: Any | None = None
    # Account / group
    account_name: str | None = None
    group_name: str | None = None
    # Firmware
    actual_firmware: str | None = None
    target_firmware: str | None = None
    upgrade_pending: bool | None = None
    reboot_required: bool | None = None
    # Custom fields
    description: str | None = None
    custom1: str | None = None
    custom2: str | None = None
    # Net device info (modem)
    imei: str | None = None
    iccid: str | None = None
    imsi: str | None = None
    mdn: str | None = None
    meid: str | None = None
    carrier: str | None = None
    carrier_id: str | None = None
    modem_name: str | None = None
    modem_fw: str | None = None
    mfg_model: str | None = None
    mfg_product: str | None = None
    connection_state: str | None = None
    service_type: str | None = None
    rfband: str | None = None
    ltebandwidth: str | None = None
    homecarrid: str | None = None
    # License state
    is_licensed: bool = False
    license_state: str | None = None  # licensed, grace-period, unlicensed
    license_state_date: datetime | None = None  # when device entered this state
    previous_license_state: str | None = None  # what the state was before the change
    state_updated_at: datetime | None = None  # last time device state (online/offline) changed
    # Base subscription
    subscription_id: str | None = None
    subscription_name: str | None = None
    subscription_type: str | None = None
    subscription_start: datetime | None = None
    subscription_end: datetime | None = None
    # Add-on subscriptions beyond the base
    add_ons: list[SubscriptionInfo] = Field(default_factory=list)
    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None
