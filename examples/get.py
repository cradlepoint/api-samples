#! /usr/bin/env python
"""Query api/v2/.

This is an example script showing how to do a simple query of a v2 endpoint.

"""
import argparse
from datetime import datetime, timedelta
from os import environ
import pprint
import requests
import sys

# THE ECM API keys should be exported to the environment before running this
# script.
HEADERS = {
    "Content-Type": "application/json",
    "X-CP-API-ID": environ.get("X_CP_API_ID"),
    "X-CP-API-KEY": environ.get("X_CP_API_KEY"),
    "X-ECM-API-ID": environ.get("X_ECM_API_ID"),
    "X-ECM-API-KEY": environ.get("X_ECM_API_KEY"),
}


def get(url):
    """Do an HTTP GET on `url`.

    Returns the data as a python dict. Forces a program exit on HTTP error.
    """
    r = requests.get(url, headers=HEADERS)
    if r.status_code not in (200, 201):
        print(f"Request failed with HTTP status {r.status_code}", file=sys.stderr)
        print(r.text, file=sys.stderr)
        sys.exit(1)
    return r.json()


if __name__ == "__main__":

    # Parse commandline options.
    parser = argparse.ArgumentParser(description="Query api/v2/historical_locations")

    parser.add_argument("endpoint")
    parser.add_argument("--api-id", help="Override X_ECM_API_ID")
    parser.add_argument("--api-key", help="Override X_ECM_API_KEY")
    parser.add_argument("--limit", help="Limit elements in reply")
    parser.add_argument(
        "--page", action="store_true", help="Keep following the next URL."
    )
    parser.add_argument(
        "--server", default="https://cradlepointecm.com", help="Base URL of server"
    )
    parser.add_argument(
        "--steps", type=int, help="If --walk, Walk only this many steps.", default=-1
    )

    args = parser.parse_args()

    if args.api_id:
        HEADERS["X-ECM-API-ID"] = args.api_id
    if args.api_key:
        HEADERS["X-ECM-API-KEY"] = args.api_key

    url = f"{args.server}/api/v2/{args.endpoint}/"
    if args.limit:
        url += f"?limit={args.limit}"

    data = get(url)
    pprint.pprint(data["data"])
    while args.page and data["meta"]["next"]:
        data = get(data["meta"]["next"])
        pprint.pprint(data["data"])
