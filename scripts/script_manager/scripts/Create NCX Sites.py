#!/usr/bin/env python3
"""
Create NCX sites for routers specified by router_id, group_id, or group_name.

This script uses the NCM v2 API for router lookups and the NCM v3 API client to
create an NCX exchange site in a specified NCX network. Use exactly one of:
router_id (individual device(s)), group_id, or group_name (group of devices).

CSV Format:
    Device/Group columns (use ONE of):
        - router_id: Individual router ID ("id", "router_id", or "router id"). Allows multiple rows.
        - group_id: Group ID ("group_id" or "group id"). First row only.
        - group_name: Group name ("group_name" or "group name"). First row only.
    
    Required columns:
        - ncx_network_id: NCX network ID to attach the sites to
    
    Optional columns:
        - site_name: Custom site name (defaults to router name if not provided)
    
    Example (by router):
        router_id,ncx_network_id,site_name
        12345,abcd-efgh-ijkl,My Site A
        67890,abcd-efgh-ijkl
    
    Example (by group ID):
        group_id,ncx_network_id
        1234,abcd-efgh-ijkl
    
    Example (by group name):
        group_name,ncx_network_id
        My Group,abcd-efgh-ijkl

Usage:
    python "Create NCX Sites.py" <config_csv_path>

Requirements:
    - NCM Python helper module `ncm` available in PYTHONPATH
    - NCM / NCX API access
    - API keys set as environment variables: X_ECM_API_ID, X_ECM_API_KEY,
      X_CP_API_ID, X_CP_API_KEY, TOKEN or NCM_API_TOKEN
"""

import csv
import os
import sys

from ncm import ncm


def load_config_from_csv(csv_filename: str) -> tuple[str, list[tuple[str, str, str | None]]]:
    """
    Read CSV and determine mode (router_id, group_id, or group_name) and rows.
    Returns (mode, [(identifier, ncx_network_id, site_name_override), ...]).
    site_name_override is from optional "site_name" column (router_id mode only), else None.
    For group modes there is one entry; for router_id there can be many.
    """
    try:
        with open(csv_filename, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV file has no header row")

            headers = {h.lower().strip(): h for h in reader.fieldnames}

            network_key = next(
                (headers[k] for k in ["ncx_network_id", "ncx network id"] if k in headers),
                None,
            )
            if not network_key:
                raise ValueError(
                    "CSV must contain 'ncx_network_id'. "
                    f"(found: {reader.fieldnames})"
                )

            router_key = next(
                (headers[k] for k in ["id", "router_id", "router id"] if k in headers), None
            )
            group_id_key = next(
                (headers[k] for k in ["group_id", "group id"] if k in headers), None
            )
            group_name_key = next(
                (headers[k] for k in ["group_name", "group name"] if k in headers), None
            )
            site_name_key = next(
                (headers[k] for k in ["site_name", "site name"] if k in headers), None
            )

            if router_key:
                mode = "router_id"
            elif group_id_key and group_name_key:
                raise ValueError(
                    "CSV must not contain both 'group_id' and 'group_name'; use one or the other. "
                    f"(found: {reader.fieldnames})"
                )
            elif group_id_key:
                mode = "group_id"
            elif group_name_key:
                mode = "group_name"
            else:
                raise ValueError(
                    "CSV must contain a router/device column ('id' or 'router_id') or a group "
                    "column ('group_id' or 'group_name'). " f"(found: {reader.fieldnames})"
                )
            rows = []

            for row in reader:
                network_id = row.get(network_key, "").strip()
                if not network_id:
                    continue
                site_override = None
                if site_name_key:
                    site_override = row.get(site_name_key, "").strip() or None
                if mode == "router_id":
                    ident = row.get(router_key, "").strip()
                    if ident:
                        rows.append((ident, network_id, site_override))
                elif mode == "group_id":
                    ident = row.get(group_id_key, "").strip()
                    if ident:
                        rows.append((ident, network_id, None))
                        break
                else:
                    ident = row.get(group_name_key, "").strip()
                    if ident:
                        rows.append((ident, network_id, None))
                        break

            if not rows:
                raise ValueError(
                    f"No data row with {mode} and ncx_network_id found"
                )
            return mode, rows
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_filename}") from None


def build_api_keys() -> dict:
    """Build API keys dict, preferring environment variables."""
    api_keys = {
        "X-ECM-API-ID": os.environ.get("X_ECM_API_ID", ""),
        "X-ECM-API-KEY": os.environ.get("X_ECM_API_KEY", ""),
        "X-CP-API-ID": os.environ.get("X_CP_API_ID", ""),
        "X-CP-API-KEY": os.environ.get("X_CP_API_KEY", ""),
        "token": os.environ.get("TOKEN") or os.environ.get("NCM_API_TOKEN", ""),
    }
    return api_keys


def create_ncx_sites(mode: str, rows: list[tuple[str, str, str | None]]) -> None:
    """Create NCX sites for routers specified by mode and (identifier, ncx_network_id, site_name_override) rows."""
    api_keys = build_api_keys()
    token = api_keys.get("token") or os.environ.get("TOKEN") or os.environ.get("NCM_API_TOKEN")
    if not token:
        print("Error: TOKEN or NCM_API_TOKEN is required for NCX v3 API (set in API Keys tab).")
        return

    n2 = ncm.NcmClientv2(api_keys=api_keys, log_events=True)
    n3 = ncm.NcmClientv3(api_key=token, log_events=True)  # Enable logging to see API errors

    for identifier, ncx_network_id, site_name_override in rows:
        if mode == "router_id":
            routers = n2.get_routers(id__in=[identifier])
        else:
            routers = n2.get_routers(group=identifier, limit="all")

        if not routers:
            print(f"No routers found for {mode}={identifier!r}.")
            continue

        for router in routers:
            site_name = site_name_override or router["name"]
            try:
                site = n3.create_exchange_site(
                    site_name, ncx_network_id, router["id"]
                )
            except Exception as e:
                print(f'Error creating NCX site for router {router["id"]} {router["name"]}: {e}')
                continue
            
            # API may return a string (e.g. site id) or a dict (created resource) on success
            if isinstance(site, str):
                pass  # success, continue to verify
            elif isinstance(site, dict) and (site.get("data") or site.get("id")):
                # Many REST APIs return the created object; treat as success
                pass
            else:
                # Real failure
                print(f'Error creating NCX site for router {router["id"]} {router["name"]}: API returned {type(site).__name__}: {site}')
                continue

            sites = n3.get_exchange_sites(name=site_name)
            if not sites:
                print(
                    f'Error creating NCX site for router {router["id"]} {router["name"]}.'
                )
                continue

            site_router_id = ""
            try:
                first = sites[0]
                if not isinstance(first, dict):
                    print(
                        f'Created exchange site for router {router["id"]} {router["name"]} '
                        "(could not verify endpoint: unexpected API response format)"
                    )
                else:
                    site_router_id = first["relationships"]["endpoints"]["data"][0]["id"]
                    if str(site_router_id) != str(router["id"]):
                        raise ValueError
                    print(
                        f'Successfully created exchange site for router '
                        f'{site_router_id} {router["name"]}'
                    )
            except (KeyError, IndexError, ValueError, TypeError):
                print(
                    f"Site created for router {router['id']} {router['name']}; "
                    "could not verify endpoint (unexpected API response structure)."
                )


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python "Create NCX Sites.py" <config_csv_path>')
        sys.exit(1)

    csv_filename = sys.argv[1]

    try:
        mode, rows = load_config_from_csv(csv_filename)
    except Exception as exc:
        print(f"Error reading configuration from CSV: {exc}")
        sys.exit(1)

    create_ncx_sites(mode, rows)


if __name__ == "__main__":
    main()
