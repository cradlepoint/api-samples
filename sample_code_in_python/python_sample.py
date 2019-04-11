"""
The following Python code sample shows how to access the "routers"
endpoint of the NCM REST API using the Python "requests" module with
paging. It makes use of the NCM and CP credential headers to
authenticate and access the router data. The data is returned as a
JSON encoded object.
"""

import json
import requests

url = 'https://www.cradlepointecm.com/api/v2/routers/'

headers = {
    'X-CP-API-ID': '…',
    'X-CP-API-KEY': '…',
    'X-ECM-API-ID': '…',
    'X-ECM-API-KEY': '…',
    'Content-Type': 'application/json'
}

# Get routers
while url:
    req = requests.get(url, headers=headers)
    routers_resp = req.json()

    # Get URL for next set of resources
    url = routers_resp['meta']['next']
