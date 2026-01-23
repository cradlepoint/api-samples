# NCX_sites - Create an NCX Site for all routers in specified group
from ncm import ncm

# NCM Group ID of routers to create sites for
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
routers = n.get_routers(group=group_id, limit='all')
if not routers:
    print(f'No routers found!')
else:
    for router in routers:
        site = n.v3.create_exchange_site(router["name"], NCX_network_id, router["id"])
        if not isinstance(site, str):
            print(f'Error creating NCX site for router {router["id"]} {router["name"]}.  Check Subscriptions!')
        else:
            sites = n.v3.get_exchange_sites(name=router["name"])
            if not sites:
                print(f'Error creating NCX site for router {router["id"]} {router["name"]}.')
            site_router_id = ''
            try:
                site_router_id = sites[0]['relationships']['endpoints']['data'][0]['id']
                if site_router_id != router["id"]:
                    raise ValueError
                print(f'Successfully created exchange site for router {site_router_id} {router["name"]}')
            except (KeyError, IndexError, ValueError):
                print(f'site exists but wrong router: {site_router_id} != {router["id"]}')
