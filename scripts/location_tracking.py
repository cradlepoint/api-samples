#! /usr/bin/env python
"""Query api/v2/historical_locations/.

This is an example script showing how to query and page through router
GPS/signal strength samples. The endpoint used is
api/v2/historical_locations. It is only available on accounts with the Mobile
Advanced package.

The API endpoint requires a router ID for it to look up the data. Only routers
with Location Tracking enabled will send data to be fetched by this endpoint.

"""
import argparse
from datetime import datetime, timedelta
import dateutil
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


def url2id(url):
    """Extract the ID from a URL"""
    return int(url.split("/")[-2])


def get(url, filt=None):
    """Do an HTTP GET on `url`.

    Returns the data as a python dict. Forces a program exit on HTTP error.
    """
    r = requests.get(url, headers=HEADERS)
    if r.status_code not in (200, 201):
        print(f"Request failed with HTTP status {r.status_code}", file=sys.stderr)
        print(r.text, file=sys.stderr)
        sys.exit(1)
    return r.json()


def get_previous_datetime(args):
    """Get a datetime for --previous."""
    if args.until:
        date = dateutil.parser.parse(args.until)
    else:
        date = datetime.now()
    kwargs = {args.units: args.previous}
    diff = timedelta(**kwargs)
    return date - diff


def get_router_data(args, router=None):
    """Query data for a singl;e router.

    Prints the data to stdout.
    """
    facts = []
    router = router or args.router_id

    url = f"{args.server}/api/v2/historical_locations/?router={router}"
    if args.after:
        url += f"&created_at__gt={args.after}"
    if args.previous:
        date = datetime.now()
        kwargs = {args.units: args.previous}
        diff = timedelta(**kwargs)
        date -= diff
        url += f"&created_at__gt={date.isoformat()}"
    elif args.until:
        url += f"&created_at__lte={args.until}"
    if args.limit:
        url += f"&limit={args.limit}"

    def fetch(url):
        data = get(url)
        facts.extend(data["data"])
        return data["meta"]["next"]

    url = fetch(url)
    steps = 1

    while args.walk and steps < args.steps and url:
        url = fetch(url)
        steps += 1

    return facts


def get_locations(args):
    """Get a list of locations."""
    locations = []
    start = get_previous_datetime(args).isoformat() if args.previous else None
    url = f"{args.server}/api/v2/locations/?fields=router,updated_at"

    if args.limit:
        url += f"&limit={args.limit}"

    def _fetch(url):
        data = get(url)
        if start:
            data["data"] = [x for x in data["data"] if x["updated_at"] >= start]
        locations.extend(data["data"])
        return data["meta"]["next"]

    while url:
        url = _fetch(url)

    return locations


def get_all_data(args):
    """Query for all routers that have locations."""
    # Limit the list of routers to those that have locations. If the
    # commandline args limit the query to a time range, filter by locations
    # that have been updated in that time range. This way we don't waste
    # queries on routers that have not reported locations in the time we are
    # interested in.
    facts = {}
    locations = get_locations(args)
    routers = [url2id(x["router"]) for x in locations]
    for router in routers:
        facts[router] = get_router_data(args, router=router)
    return facts


if __name__ == "__main__":

    # Parse commandline options.
    parser = argparse.ArgumentParser(description="Query api/v2/historical_locations")
    cmd = parser.add_subparsers(title="commands", dest="cmd")

    parser.add_argument(
        "--after",
        help="Return data only after a date and time (YYYY-mm-DDTHH:MM:SS) [default is 24 hours ago]",
    )
    parser.add_argument("--api-id", help="Override X_ECM_API_ID")
    parser.add_argument("--api-key", help="Override X_ECM_API_KEY")
    parser.add_argument(
        "--until",
        help="Return data only before a date and time (YYYY-mm-DDTHH:MM:SS) [default is now]",
    )
    parser.add_argument("--limit", default=25000)
    parser.add_argument(
        "--previous",
        type=int,
        help="Return data starting this many hours before the --before option (overrides --after)",
    )
    parser.add_argument(
        "--server", default="https://www.cradlepointecm.com", help="Base URL of server"
    )
    parser.add_argument(
        "--steps", type=int, help="If --walk, walk only this many steps.", default=0
    )
    parser.add_argument(
        "--units",
        help="Use these units instead of hours for the --previous option",
        default="hours",
        choices=["seconds", "minutes", "hours", "days", "weeks"],
    )
    parser.add_argument("--walk", action="store_true")

    rcmd = cmd.add_parser("router", help="Get data for a single router")
    rcmd.add_argument("router_id", help="Router ID")
    rcmd.set_defaults(func=get_router_data)

    acmd = cmd.add_parser("all", help="Get data for all routers")
    acmd.set_defaults(func=get_all_data)

    args = parser.parse_args()

    if args.api_id:
        HEADERS["X-ECM-API-ID"] = args.api_id
    if args.api_key:
        HEADERS["X-ECM-API-KEY"] = args.api_key

    data = args.func(args)

    pprint.pprint(data)
