"""Local snapshot cache for preserving device history across runs.

Saves a JSON file after each SDK run so that when devices lose v2 data
(e.g. after unlicensing), we can restore the last known info and detect
when the state change occurred.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import LicenseStatus

_DEFAULT_SNAPSHOT_PATH = Path("inventory_snapshot.json")


def _serialize(status: LicenseStatus) -> dict[str, Any]:
    """Convert a LicenseStatus to a JSON-safe dict, keyed by normalized MAC."""
    data = status.model_dump(mode="json")
    # Normalize the key
    mac = (status.mac or "").upper().replace(":", "").replace("-", "")
    data["_mac_key"] = mac
    return data


def _deserialize(data: dict[str, Any]) -> dict[str, Any]:
    """Return the raw dict (we don't need to reconstruct the full model)."""
    return data


def load_snapshot(path: Path = _DEFAULT_SNAPSHOT_PATH) -> dict[str, dict[str, Any]]:
    """Load the previous snapshot from disk, keyed by normalized MAC."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        result: dict[str, dict[str, Any]] = {}
        for entry in raw:
            mac_key = entry.get("_mac_key", "")
            if mac_key:
                result[mac_key] = entry
        return result
    except (json.JSONDecodeError, KeyError):
        return {}


def save_snapshot(
    statuses: list[LicenseStatus],
    path: Path = _DEFAULT_SNAPSHOT_PATH,
) -> None:
    """Save the current run's data as a snapshot."""
    records = [_serialize(s) for s in statuses]
    path.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")


# Fields to restore from snapshot when v2 data is lost
_RESTORABLE_FIELDS = [
    "router_id",
    "router_name",
    "account_name",
    "group_name",
    "device_type",
    "full_product_name",
    "state",
    "config_status",
    "ipv4_address",
    "locality",
    "actual_firmware",
    "target_firmware",
    "description",
    "custom1",
    "custom2",
    "imei",
    "iccid",
    "imsi",
    "mdn",
    "meid",
    "carrier",
    "carrier_id",
    "modem_name",
    "modem_fw",
    "mfg_model",
    "mfg_product",
    "connection_state",
    "service_type",
    "rfband",
    "ltebandwidth",
    "homecarrid",
    "state_updated_at",
]


def enrich_from_snapshot(
    statuses: list[LicenseStatus],
    previous: dict[str, dict[str, Any]],
) -> list[LicenseStatus]:
    """Fill in missing fields from the previous snapshot and detect state changes.

    For each device:
    - If it has no v2 data (router_id is empty) but the snapshot has it,
      restore the last known values and mark them.
    - If the license_state changed since the last snapshot, set
      license_state_date to now.
    - If the license_state is the same, carry forward the previous date.
    """
    now = datetime.now(timezone.utc)
    enriched: list[LicenseStatus] = []

    for status in statuses:
        mac_key = (status.mac or "").upper().replace(":", "").replace("-", "")
        prev = previous.get(mac_key)

        # Restore missing v2 fields from snapshot
        if not status.router_id and prev:
            updates: dict[str, Any] = {}
            for field in _RESTORABLE_FIELDS:
                current_val = getattr(status, field, None)
                prev_val = prev.get(field)
                if not current_val and prev_val:
                    updates[field] = prev_val
            if updates:
                status = status.model_copy(update=updates)

        # Detect state changes for license_state_date
        if prev:
            prev_state = prev.get("license_state")
            if status.license_state != prev_state:
                # State changed — record today and remember previous state
                status = status.model_copy(update={
                    "license_state_date": now,
                    "previous_license_state": prev_state,
                })
            elif prev.get("license_state_date"):
                # Same state — carry forward the previous date and previous state
                prev_date = prev["license_state_date"]
                if isinstance(prev_date, str):
                    try:
                        prev_date = datetime.fromisoformat(prev_date)
                    except ValueError:
                        prev_date = None
                status = status.model_copy(
                    update={
                        "license_state_date": prev_date,
                        "previous_license_state": prev.get("previous_license_state"),
                    }
                )
        else:
            # First time seeing this device — record today
            status = status.model_copy(update={"license_state_date": now})

        enriched.append(status)

    return enriched
