"""Export NCM API historical_locations/ data to .csv file.

This script will export the data from the Cradlepoint NCM API
historical_locations/ endpoint for all devices for the given date range.
Data is written to the .csv file defined below.
Cradlepoint NCM API keys are required.

Attributes
----------
start_date : beginning of date range to export
end_date : end of date range to export
output_file : name of .csv file to be created
headers : Replace values with your NCM API keys for use in HTTP requests.
"""

import requests
import csv

start_date = '2021-09-02'
end_date = '2021-09-03'

output_file = 'historical_locations.csv'

headers = {'X-ECM-API-ID': 'YOUR',
           'X-ECM-API-KEY': 'KEYS',
           'X-CP-API-ID': 'GO',
           'X-CP-API-KEY': 'HERE',
           'Content-Type': 'application/json'}

top_line = ["router", "name", "accuracy", "carrier_id", "cinr",
            "created_at", "created_at_timeuuid", "dbm", "ecio",
            "latitude", "longitude", "mph", "net_device_name",
            "rfband", "rfband_5g", "rsrp", "rsrp_5g", "rsrq",
            "rsrq_5g", "rssi", "signal_percent", "sinr",
            "sinr_5g", "summary"]

server = 'https://www.cradlepointecm.com'

with open(output_file, 'wt') as f:
    writer = csv.writer(f, delimiter=',')
    writer.writerow(top_line)  # write header

    routers_url = f'{server}/api/v2/routers/?state__in=online,offline' \
        f'&limit=500'
    try:
        while routers_url:
            routers_req = requests.get(routers_url, headers=headers).json()
            routers = routers_req['data']
            for router in routers:
                locations_url = f'{server}/api/v2/historical_locations/' \
                    f'?router={router["id"]}&created_at__gt={start_date}' \
                    f'&created_at__lte={end_date}'
                while locations_url:
                    locations_req = requests.get(
                        locations_url, headers=headers).json()
                    print(f'Router ID: {router["id"]} Historical Locations: {locations_req["data"]}')
                    locations = locations_req['data']
                    for location in locations:
                        if location['carrier_id']:
                            loc_values = [x for x in location.values()]
                            row = [router["id"], router["name"]] + loc_values
                            writer.writerow(row)
                    locations_url = locations_req['meta']['next']
            routers_url = routers_req['meta']['next']
    except Exception as e:
        print(e)
