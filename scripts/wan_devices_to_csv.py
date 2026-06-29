"""
Export connected WAN net_devices with router info to CSV.

Fetches all net_devices in WAN mode with connection_state=connected,
expanding the router relationship inline. Writes router ID, router name,
net_device carrier, and net_device RF band to a CSV file.
"""
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.env_check import check_env
from utils.session import APISession
from utils.logger import get_logger


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    f'wan_devices_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
)


def main():
    check_env()
    logger = get_logger()

    session = APISession(
        logger=logger,
        cp_api_id=os.environ['X_CP_API_ID'],
        cp_api_key=os.environ['X_CP_API_KEY'],
        ecm_api_id=os.environ['X_ECM_API_ID'],
        ecm_api_key=os.environ['X_ECM_API_KEY'],
    )

    url = ('https://www.cradlepointecm.com/api/v2/net_devices/'
           '?mode=wan&connection_state=connected&is_asset=true'
           '&expand=router&limit=500')

    print('Fetching connected WAN devices...')
    results = []

    for device in session.get(url=url, batchsize=500):
        router = device.get('router')

        # router is expanded inline as an object when expand=router is used
        if router and isinstance(router, dict):
            router_id = router.get('id', '')
            router_name = router.get('name', '')
        else:
            router_id = ''
            router_name = ''

        carrier = device.get('carrier', '') or ''
        rfband = device.get('rfband', '') or ''
        rfband5g = device.get('rfband5g', '') or ''
        # Use 5G band if available, otherwise use LTE band
        rf_band = rfband5g if rfband5g else rfband

        results.append({
            'router_id': router_id,
            'router_name': router_name,
            'carrier': carrier,
            'rf_band': rf_band,
        })

    print(f'Retrieved {len(results)} connected WAN devices.')

    # Write CSV
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fields = ['router_id', 'router_name', 'carrier', 'rf_band']
    with open(OUTPUT_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    print(f'CSV written to: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
