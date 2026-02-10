#!/usr/bin/env python3
"""
Create NCX IP subnet resources for all LANs on routers in a group.

This script uses the NCM v3 API client to create NCX IP subnet resources for
every LAN on every router in a specified NCM group. All user inputs (group and
network IDs) are read from a CSV file.

CSV Format:
    Required columns (case-insensitive):
        - group_id: NCM group ID that contains the routers
        - ncx_network_id: NCX network ID that the sites/resources belong to

    The first data row is used; additional rows are ignored.

    Example CSV:
        group_id,ncx_network_id
        1234,abcd-efgh-ijkl

Usage:
    python "Create NCX Resources.py" <config_csv_path>

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
import ipaddress
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


def get_site(n: ncm.NcmClient, router: dict) -> dict | None:
    """Get the NCX site associated with the given router."""
    sites = n.get_exchange_sites(name=router["name"])
    if not sites:
        print(f'Site not found for router {router["id"]} {router["name"]}.')
        return None

    site_router_id = ""
    try:
        site_router_id = sites[0]["relationships"]["endpoints"]["data"][0]["id"]
        if str(site_router_id) != str(router["id"]):
            raise ValueError
    except (KeyError, IndexError, ValueError):
        print(f"Site exists but wrong router: {site_router_id} != {router['id']}")
        return None

    return sites[0]


def get_lans(n: ncm.NcmClient, router: dict) -> list[str]:
    """Return list of LAN networks (CIDR strings) for the given router."""
    url = f"{n.v2.base_url}/routers/{router['id']}/lans/"
    response = n.v2.session.get(url)
    if not response.ok:
        print(f"Failed to get LANs for router {router['id']}: {response.text}")
        return []

    lans: list[str] = []
    for lan in response.json():
        try:
            network = ipaddress.ip_network(
                f"{lan['ip_address']}/{lan['netmask']}", strict=False
            )
            lans.append(str(network))
        except (KeyError, ValueError):
            continue
    return lans


def create_ncx_resources(group_id: str, ncx_network_id: str) -> None:
    """Create NCX IP subnet resources for all routers in the group."""
    api_keys = build_api_keys()
    n = ncm.NcmClient(api_keys=api_keys, log_events=False)

    routers = n.get_routers(group=group_id, limit="all")
    if not routers:
        print("No routers found!")
        return

    for router in routers:
        print(
            f'Creating NCX resources for router {router["id"]} {router["name"]} '
            f"in network {ncx_network_id}..."
        )
        site = get_site(n, router)
        if not site:
            continue

        lans = get_lans(n, router)
        if not lans:
            print("No LANs found")
            continue

        for lan in lans:
            resource = n.create_exchange_resource(
                site["id"],
                f"{lan}",
                "exchange_ipsubnet_resources",
                ip=lan,
            )
            if isinstance(resource, str):
                if "overlapping_resource" not in resource:
                    print(resource)
                    continue
            print(
                f"Created NCX IP Subnet Resource {lan} for router "
                f'{router["name"]}, site {site["name"]}.'
            )
        print("Success!\n")


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python "Create NCX Resources.py" <config_csv_path>')
        sys.exit(1)

    csv_filename = sys.argv[1]

    try:
        group_id, ncx_network_id = load_group_and_network_from_csv(csv_filename)
    except Exception as exc:
        print(f"Error reading configuration from CSV: {exc}")
        sys.exit(1)

    create_ncx_resources(group_id, ncx_network_id)


if __name__ == "__main__":
    main()

