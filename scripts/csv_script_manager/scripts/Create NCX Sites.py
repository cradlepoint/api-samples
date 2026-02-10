#!/usr/bin/env python3
"""
Create NCX sites for all routers in an NCM group.

This script uses the NCM v3 API client to create an NCX exchange site in a
specified NCX network for every router in a specified NCM group. All user
inputs (group and network IDs) are read from a CSV file.

CSV Format:
    Required columns (case-insensitive):
        - group_id: NCM group ID that contains the routers
        - ncx_network_id: NCX network ID to attach the sites to

    The first data row is used; additional rows are ignored.

    Example CSV:
        group_id,ncx_network_id
        1234,abcd-efgh-ijkl

Usage:
    python "Create NCX Sites.py" <config_csv_path>

Requirements:
    - NCM Python helper module `ncm` available in PYTHONPATH
    - NCM / NCX API access
    - CSV config file providing group_id and ncx_network_id
    - API keys and token provided via environment variables:
        - X_ECM_API_ID
        - X_ECM_API_KEY
        - X_CP_API_ID
        - X_CP_API_KEY
        - NCM_API_TOKEN
"""

import csv
import os
import sys

from ncm import ncm


def load_group_and_network_from_csv(csv_filename: str) -> tuple[str, str]:
    """Read required group_id and ncx_network_id from the first CSV row."""
    try:
        with open(csv_filename, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV file has no header row")

            headers = {h.lower().strip(): h for h in reader.fieldnames}

            group_key = next(
                (headers[k] for k in ["group_id", "group id"] if k in headers), None
            )
            network_key = next(
                (headers[k] for k in ["ncx_network_id", "ncx network id"] if k in headers),
                None,
            )

            if not group_key or not network_key:
                raise ValueError(
                    "CSV must contain 'group_id' and 'ncx_network_id' columns "
                    f"(found: {reader.fieldnames})"
                )

            for row in reader:
                group_id = row.get(group_key, "").strip()
                network_id = row.get(network_key, "").strip()
                if group_id and network_id:
                    return group_id, network_id

            raise ValueError("No data row with both group_id and ncx_network_id found")
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_filename}") from None


def build_api_keys() -> dict:
    """Build API keys dict, preferring environment variables."""
    api_keys = {
        "X-ECM-API-ID": os.environ.get("X_ECM_API_ID", ""),
        "X-ECM-API-KEY": os.environ.get("X_ECM_API_KEY", ""),
        "X-CP-API-ID": os.environ.get("X_CP_API_ID", ""),
        "X-CP-API-KEY": os.environ.get("X_CP_API_KEY", ""),
        "token": os.environ.get("NCM_API_TOKEN", ""),
    }
    return api_keys


def create_ncx_sites(group_id: str, ncx_network_id: str) -> None:
    """Create NCX sites for all routers in the specified NCM group."""
    api_keys = build_api_keys()

    n = ncm.NcmClient(api_keys=api_keys, log_events=False)
    routers = n.get_routers(group=group_id, limit="all")
    if not routers:
        print("No routers found!")
        return

    for router in routers:
        site = n.v3.create_exchange_site(router["name"], ncx_network_id, router["id"])
        if not isinstance(site, str):
            print(
                f'Error creating NCX site for router {router["id"]} {router["name"]}.  '
                "Check subscriptions!"
            )
            continue

        sites = n.v3.get_exchange_sites(name=router["name"])
        if not sites:
            print(
                f'Error creating NCX site for router {router["id"]} {router["name"]}.'
            )
            continue

        site_router_id = ""
        try:
            site_router_id = sites[0]["relationships"]["endpoints"]["data"][0]["id"]
            if str(site_router_id) != str(router["id"]):
                raise ValueError
            print(
                f'Successfully created exchange site for router '
                f'{site_router_id} {router["name"]}'
            )
        except (KeyError, IndexError, ValueError):
            print(
                f"Site exists but wrong router: {site_router_id} != {router['id']}"
            )


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python "Create NCX Sites.py" <config_csv_path>')
        sys.exit(1)

    csv_filename = sys.argv[1]

    try:
        group_id, ncx_network_id = load_group_and_network_from_csv(csv_filename)
    except Exception as exc:
        print(f"Error reading configuration from CSV: {exc}")
        sys.exit(1)

    create_ncx_sites(group_id, ncx_network_id)


if __name__ == "__main__":
    main()

