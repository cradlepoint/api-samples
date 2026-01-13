# NCX_resources - Create an NCX IP Subnet resource for all LANs on all routers in specified group
from ncm import ncm
import ipaddress

# NCM Group ID of routers to create resources for
group_id = 'NCM Group ID'

# NCX Network ID
NCX_network_id = 'YOUR NCX NETWORK ID'

# NCM API v2 keys and v3 token
api_keys = {
    'X-ECM-API-ID': "YOUR",
    'X-ECM-API-KEY': "APIv2",
    'X-CP-API-ID': "KEYS",
    'X-CP-API-KEY': "HERE",
    'token': 'NCM_API_v3_Token'
}

n = ncm.NcmClient(api_keys=api_keys, log_events=False)

def get_site(router):
    sites = n.get_exchange_sites(name=router["name"])
    if not sites:
        print(f'Site not found for router {router["id"]} {router["name"]}.')
        return
    site_router_id = ''
    try:
        site_router_id = sites[0]['relationships']['endpoints']['data'][0]['id']
        if str(site_router_id) != str(router["id"]):
            raise ValueError
    except (KeyError, IndexError, ValueError):
        print(f"site exists but wrong router: {site_router_id} != {router["id"]}")
        return
    return sites[0]

def get_lans(router):
    r = n.v2.session.get(f"{n.v2.base_url}/routers/{router["id"]}/lans/")
    if not r.ok:
        print("Failed to get lans: %s", r.text)
        return []
    lans = []
    for lan in r.json():
        network = ipaddress.ip_network(f"{lan['ip_address']}/{lan['netmask']}", strict=False)
        lans.append(str(network))
    return lans

routers = n.get_routers(group=group_id, limit='all')
if not routers:
    print(f'No routers found!')
else:
    for router in routers:
        print(f'Creating NCX resources for router {router["id"]} {router["name"]}...')
        site = get_site(router)
        lans = get_lans(router)
        if not lans:
            print("No lans found")
            continue
        for lan in lans:
            resource = n.create_exchange_resource(site['id'], f"{lan}", "exchange_ipsubnet_resources", ip=lan)
            if isinstance(resource, str):
                if not "overlapping_resource" in resource:
                    print(resource)
                    continue
            print(f'Created NCX IP Subnet Resource {lan} for router {router["name"]}, site {site["name"]}.')
        print('Success!\n')
