__version__ = "0.1.0"

import cgi
import csv
import json
from functools import lru_cache
from http.server import HTTPServer, SimpleHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor
import threading
import ipaddress
import logging
from ncm import ncm

### These settings should be modified to fit the environment ###
api_keys = {
    "token": "NCM_API_v3_Token",
    'X-ECM-API-ID': "YOUR",
    'X-ECM-API-KEY': "APIv2",
    'X-CP-API-ID': "KEYS",
    'X-CP-API-KEY': "HERE"
}

# Subscriptions:
# NCX-SCL, NCX-SCM, NCX-SCIOT, NCX-SCS, NCX-SDWANL, NCX-SDWANM, NCX-SDWANMICRO, NCX-SDWANS
subscriptions = ["NCX-SCL"]  # Subscriptions to apply to routers
prod_group_id = '12345'  # NCM Group ID for Processed Routers
exchange_network_id = 'YOUR NCX NETWORK ID'  # Exchange Network ID
csv_file = 'routers.csv'

# lan uuids
lan0 = "00000000-0d93-319d-8220-4a1fb0372b51"

# csv columns
SERIAL_NUMBER_COLUMN = "serial_number"
MAC_COLUMN = "mac"
LAN_SUBNET_COLUMN = "lan_subnet"

######

LOGGER = logging.getLogger()
fmt = '%(asctime)s | %(levelname)8s | %(message)s'
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(fmt))
LOGGER.addHandler(stream_handler)
LOGGER.setLevel(logging.DEBUG)

status = {}

def log_status(source, message, level="info"):
    try:
        status[source].append(message)
    except KeyError:
        status[source] = [message]
    getattr(LOGGER, level)(message)


def provision_router(serial_number_or_mac, name):
    n = ncm.NcmClient(api_keys=api_keys, log_events=False)
    try:
        if len(serial_number_or_mac) == 14:
            kwargs = {"serial_number": serial_number_or_mac}
        else:
            kwargs = {"mac": serial_number_or_mac}
        router_id = n.v2.get_routers(**kwargs)[0]['id']
    except IndexError:
        return {"success": False, "message": "Serial Number not found in NCM API"}
    lan_subnet = get_subnet(**kwargs)
    if not lan_subnet:
        return {"success": False, "message": "Serial Number not found in Subnets file."}

    LOG = lambda x: log_status(serial_number_or_mac, x)

    # Step 0 - License routers
    def regrade(mac, profile):
        LOG(f"Regrading {mac} with {profile}")
        result = n.v3.regrade(profile, mac)
        LOGGER.debug(f"Regrade result: {result}")
        if "ERROR" in result:
            return {"success": False, "message": result}
        return {"success": True, "message": result}

    mac = get_mac(**kwargs)
    for profile in subscriptions:
        r = regrade(mac, profile)
        if not r["success"]:
            return r
        else:
            LOG(f"{r['message']}")

    # Step 1 - Move router to Provisioned Group
    LOG(f"Assigning to Provisioned Group ({prod_group_id})")
    n.v2.assign_router_to_group(router_id, prod_group_id)

    # Step 2 - Configure router with name and subnet
    lan_ip_address = str(ipaddress.ip_network(lan_subnet).network_address + 1)
    lan_netmask = str(ipaddress.ip_network(lan_subnet).netmask)

    config = {"configuration": [{"system": {"system_id": name}, "lan": {
        lan0: {"ip_address": lan_ip_address, "netmask": lan_netmask, "_id_": lan0}}}, []]}
    LOG(f"Configure with: {config}")
    n.v2.patch_configuration_managers(router_id, config)

    # Step 3 - Create NCX Site
    LOG(f"Creating site named {name} for {router_id}")
    site = n.v3.create_exchange_site(name, exchange_network_id, router_id)
    if isinstance(site, str):
        sites = n.v3.get_exchange_sites(name=name)
        if not sites:
            return {"success": False, "message": site}
        site_router_id = ''
        try:
            site_router_id = sites[0]['relationships']['endpoints']['data'][0]['id']
            if site_router_id != router_id:
                raise ValueError
        except (KeyError, IndexError, ValueError):
            return {"success": False, "message": f"site exists but wrong router: {site_router_id} != {router_id}"}
        site = sites[0]

    # Step 4 - Create NCX Resource
    LOG(f"Creating resources for {router_id}")
    resource = n.v3.create_exchange_resource(site['id'], f"{name}-LAN", "exchange_ipsubnet_resources", ip=lan_subnet)
    if isinstance(resource, str):
        if not "overlapping_resource" in resource:
            return {"success": False, "message": resource}

    return {"success": True,
            "message": f"Provisioned router with {list(kwargs.keys())[0]} {serial_number_or_mac} on subnet {lan_subnet}"}


@lru_cache(maxsize=None)
def open_csv(file=csv_file):
    with open(file, 'r') as f:
        reader = csv.DictReader(f)
        d = {row[SERIAL_NUMBER_COLUMN]: row for row in reader}
        d.update({row[MAC_COLUMN]: row for row in reader})
        return d


def get_subnet(serial_number=None, mac=None):
    r = open_csv()
    return r[serial_number or mac][LAN_SUBNET_COLUMN]


def get_mac(serial_number=None, mac=None):
    r = open_csv()
    return r[serial_number or mac][MAC_COLUMN]


class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
            return
        if self.path == '/':
            self.path = '/index.html'
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/submit':
            if status and status['system'][-1] != "Done":
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Provisioning in progress")
                return
            status.clear()
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST',
                         'CONTENT_TYPE': self.headers['Content-Type'],
                         })

            to_provision = []

            serial_number = form.getvalue("serial_number_or_mac")
            if serial_number:
                name = form.getvalue("name")
                to_provision.append((serial_number, name))
            i = 0
            while True:
                serial_number = form.getvalue(f"serial_number_or_mac[{i}]")
                if not serial_number:
                    break
                name = form.getvalue(f"name[{i}]")
                to_provision.append((serial_number, name))
                i += 1
            log_status("system", f"Provisioning {len(to_provision)} routers...")
            LOGGER.debug(to_provision)

            def background_task():
                messages = []
                with ThreadPoolExecutor(max_workers=10) as executor:
                    for r in executor.map(lambda x: provision_router(*x), to_provision):
                        if r["success"]:
                            messages.append(r["message"])
                        else:
                            messages.append(f"Error: {r['message']}")
                for m in messages:
                    log_status("system", m)
                log_status("system", "Done")

            threading.Thread(target=background_task, daemon=True).start()

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Provisioning...")
        else:
            self.send_response(404)
            self.end_headers()


def run(server_class=HTTPServer, handler_class=CustomHandler, port=8888):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    print(f"Server started at http://localhost:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run()
