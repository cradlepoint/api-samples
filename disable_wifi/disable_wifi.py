"""
disable_wifi.py uses the NCM API to disable the 2.4ghz and 5ghz wifi radios on a list of routers.
It uses an HTTP PATCH so that only WiFi is erased and your entire configuration doesn't get overwritten.

Made by Harvey Breaux for use with the Cradlepoint NCM APIv2
"""

from ncm import RouterConfig

# Put your NCM API headers into this dictionary
headers = {
    'X-CP-API-ID': 'your cp api id here',
    'X-CP-API-KEY': 'your cp api key here',
    'X-ECM-API-ID': 'your ecm api id here',
    'X-ECM-API-KEY': 'your ecm api key here',
    'Content-Type': 'application/json'
}

# The json payload that disables wifi on the 2.4ghz and 5ghz radios
payload = \
    {
        "configuration": [{
            "wlan": {
                "radio": {
                    "0": {
                        "enabled": False
                    },
                    "1": {
                        "enabled": False
                    }
                }
            }
        },
            []]
    }

# The NCM Router IDs of the Routers we want to interact with
router_ids = ['router id goes here', 'additional router id goes here', 'etc']

# Create a RouterConfig object to interact with router configurations in NCM using our headers
ncm_routers = RouterConfig(headers)

# Patch configuration to routers using the NCM api
ncm_routers.patch(router_ids, payload)
