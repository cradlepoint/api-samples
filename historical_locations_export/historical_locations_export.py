# historical_locations_export.py
# Enter Cradlepoint NCM API Keys below to export data from the historical_locations/ endpoint to .csv file
# Set start_date and end_date for dates you want to export data for
# Drag and drop .csv file to https://kepler.gl/demo to create maps based on data such as signal strength

import requests
import csv

api_keys = {'X-ECM-API-ID': 'YOUR',
           'X-ECM-API-KEY': 'KEYS',
           'X-CP-API-ID': 'GO',
           'X-CP-API-KEY': 'HERE',
           'Content-Type': 'application/json'}

start_date = '2021-09-01'
end_date = '2021-09-04'

output_file = 'historical_locations.csv'

server = 'https://www.cradlepointecm.com'
col_headings = ["router", "name", "accuracy", "carrier_id", "cinr", "created_at", "created_at_timeuuid", "dbm", "ecio",
                "latitude",
                "longitude", "mph", "net_device_name", "rfband", "rfband_5g", "rsrp", "rsrp_5g", "rsrq", "rsrq_5g",
                "rssi", "signal_percent", "sinr", "sinr_5g", "summary"]

with open(output_file, 'wt') as f:
    writer = csv.writer(f, delimiter=',')
    writer.writerow(col_headings)  # write header

    routers_url = f'{server}/api/v2/routers/?state__in=online,offline&limit=500'
    try:
        while routers_url:
            routers_req = requests.get(routers_url, headers=api_keys).json()
            routers = routers_req['data']
            for router in routers:
                locations_url = f'{server}/api/v2/historical_locations/?router=' \
                    f'{router["id"]}&created_at__gt={start_date}&created_at__lt={end_date}'
                while locations_url:
                    locations_req = requests.get(locations_url, headers=api_keys).json()
                    locations = locations_req['data']
                    for location in locations:
                        if location['carrier_id']:
                            loc_values = [x for x in location.values()]
                            row = [router["id"], router["name"]] + loc_values
                            print(row)
                            writer.writerow(row)
                    locations_url = locations_req['meta']['next']
            routers_url = routers_req['meta']['next']
    except Exception as e:
        print(e)
