"""
Export connected WAN modem net_devices with router info to CSV.

Fetches all net_devices in WAN mode with connection_state=connected and
is_asset=true (modems only), expanding the router relationship inline.
Writes router ID, router name, carrier, and RF band to a CSV file.

Requirements: requests (pip install requests)

Environment variables required:
    X_CP_API_ID   - Cradlepoint API ID
    X_CP_API_KEY  - Cradlepoint API Key
    X_ECM_API_ID  - ECM API ID
    X_ECM_API_KEY - ECM API Key
"""
import csv
import os
import sys
import platform
from datetime import datetime

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("This script requires the 'requests' library.")
    print("Install it with: pip install requests")
    sys.exit(1)


# --- Configuration ---
BASE_URL = 'https://www.cradlepointecm.com/api/v2/net_devices/'
PARAMS = '?mode=wan&connection_state=connected&is_asset=true&expand=router&limit=500'
OUTPUT_FILE = f'wan_devices_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'


def check_env():
    """Validate required environment variables are set."""
    required = ['X_CP_API_ID', 'X_CP_API_KEY', 'X_ECM_API_ID', 'X_ECM_API_KEY']
    missing = [v for v in required if not os.environ.get(v)]

    if not missing:
        return

    print("\nMissing required environment variables:\n", file=sys.stderr)
    for var in missing:
        print(f"  {var}", file=sys.stderr)
    print("", file=sys.stderr)

    system = platform.system()
    if system == "Windows":
        print("Set them in PowerShell:", file=sys.stderr)
        for var in missing:
            print(f'  $env:{var} = "your_value_here"', file=sys.stderr)
    else:
        print("Set them in your terminal:", file=sys.stderr)
        for var in missing:
            print(f'  export {var}="your_value_here"', file=sys.stderr)

    print("", file=sys.stderr)
    sys.exit(1)


def get_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[408, 429, 500, 502, 503, 504],
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({
        'Content-Type': 'application/json',
        'X-CP-API-ID': os.environ['X_CP_API_ID'],
        'X-CP-API-KEY': os.environ['X_CP_API_KEY'],
        'X-ECM-API-ID': os.environ['X_ECM_API_ID'],
        'X-ECM-API-KEY': os.environ['X_ECM_API_KEY'],
    })
    return session


def fetch_all_pages(session, url):
    """Fetch all pages from a v2 paginated endpoint."""
    results = []
    while url:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get('data', []))
        url = data.get('meta', {}).get('next')
    return results


def main():
    check_env()

    session = get_session()
    url = BASE_URL + PARAMS

    print('Fetching connected WAN modems...')
    devices = fetch_all_pages(session, url)
    print(f'Retrieved {len(devices)} devices.')

    rows = []
    for device in devices:
        router = device.get('router')
        if router and isinstance(router, dict):
            router_id = router.get('id', '')
            router_name = router.get('name', '')
        else:
            router_id = ''
            router_name = ''

        carrier = device.get('carrier', '') or ''
        rfband = device.get('rfband', '') or ''
        rfband5g = device.get('rfband5g', '') or ''
        rf_band = rfband5g if rfband5g else rfband

        rows.append({
            'router_id': router_id,
            'router_name': router_name,
            'carrier': carrier,
            'rf_band': rf_band,
        })

    fields = ['router_id', 'router_name', 'carrier', 'rf_band']
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f'CSV written to: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
