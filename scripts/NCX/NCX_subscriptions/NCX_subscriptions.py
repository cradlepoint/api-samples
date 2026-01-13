# NCX_subscriptions - Apply NCX Subscriptions to routers in specified group
from ncm import ncm

# NCM Group ID of routers to apply subscriptions to
group_id = '123456'

# NCM API v2 keys and v3 token
api_keys = {
    'X-ECM-API-ID': "YOUR",
    'X-ECM-API-KEY': "APIv2",
    'X-CP-API-ID': "KEYS",
    'X-CP-API-KEY': "HERE",
    'token': 'NCM_API_v3_Token'
}

# Subscriptions:
# NCX-SCL, NCX-SCM, NCX-SCIOT, NCX-SCS, NCX-SDWANL, NCX-SDWANM, NCX-SDWANMICRO, NCX-SDWANS
subscriptions = ["NCX-SCL"]  # Subscriptions to apply to routers

n = ncm.NcmClient(api_keys=api_keys, log_events=False)
routers = n.get_routers(group=group_id, limit='all')
if not routers:
    print(f'No routers found!')
else:
    macs = [x["mac"] for x in routers]
    for profile in subscriptions:
        for mac in macs:
            r = n.v3.regrade(profile, mac)
            print(f'MAC: {mac} {r}')