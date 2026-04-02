# Device and Group Configuration via API

## Overview

Device configuration is managed through the `configuration_managers` endpoint (individual device config)
and the `groups` endpoint (group-level config). The final device config (target) is the result of
layering the individual config over the group config.

## Config Diff Format

Configurations are expressed as "diffs" — a two-element list:
```json
[{updates_dict}, [removals_list]]
```

An empty diff: `[{}, []]`

### Updates Dictionary
The first element contains key-value pairs to set/change:
```json
[{"system": {"gps": {"enabled": true}}}, []]
```

### Removals List
The second element lists paths to remove from defaults:
```json
[{}, [["lan", "00000001-0d93-319d-8220-4a1fb0372b51"]]]
```

## Endpoints

### Device Config
```
GET    /api/v2/configuration_managers/{id}/
PUT    /api/v2/configuration_managers/{id}/
PATCH  /api/v2/configuration_managers/{id}/
```

### Group Config
```
GET    /api/v2/groups/{id}/?fields=configuration
PUT    /api/v2/groups/{id}/
PATCH  /api/v2/groups/{id}/
```

## PUT vs PATCH

| Behavior | PUT | PATCH |
|----------|-----|-------|
| Unmentioned fields | Reset to defaults | Left unchanged |
| Use case | Replace entire config | Adjust existing config |
| Can remove items | Yes (via removals list) | No |
| Returns payload | Yes | No |

## _id_ Fields

Arrays with default elements use UUID-based `_id_` fields for unambiguous identification.
When referencing array elements, use the `_id_` as the key:

```json
{
  "lan": {
    "00000000-0d93-319d-8220-4a1fb0372b51": {
      "_id_": "00000000-0d93-319d-8220-4a1fb0372b51",
      "ip_address": "192.168.30.1",
      "name": "LAN0"
    }
  }
}
```

**Important**: When using `_id_` as a key, you MUST also include the `_id_` field inside the object.

### Arrays that support _id_ fields (firmware 6.1.0+)

```
asavie.tunnels, certmgmt.certs, dns.dnsmasq_options, gre.tunnels,
identities.ip, identities.mac, identities.port, lan,
openvpn.tunnels, routing.access_list, routing.bgp.access_list,
routing.bgp.community_list, routing.prefix_list, routing.route_map,
routing.tables, security.app_sets, security.ips.cat_cfg,
security.ips.sig_cfg, security.zfw.filter_policies,
security.zfw.forwardings, security.zfw.zones, split_dns.domain_lists,
split_dns.servers, system.gps.connections, vpn.tunnels,
wan.rules, wan.rules2
```

## Common Configuration Examples

### Enable GPS
```json
PATCH /api/v2/configuration_managers/{id}/
{
  "configuration": [{"system": {"gps": {"enabled": true}}}, []]
}
```

### Change LAN IP Address
```json
PATCH /api/v2/configuration_managers/{id}/
{
  "configuration": [{
    "lan": {
      "00000000-0d93-319d-8220-4a1fb0372b51": {
        "_id_": "00000000-0d93-319d-8220-4a1fb0372b51",
        "ip_address": "192.168.30.1"
      }
    }
  }, []]
}
```

### Change WiFi SSID and Password
```json
PATCH /api/v2/configuration_managers/{id}/
{
  "configuration": [{
    "wlan": {
      "radio": {
        "0": {
          "bss": {
            "0": {
              "ssid": "MyNetwork",
              "wpapsk": "MyPassword123"
            }
          }
        }
      }
    }
  }, []]
}
```

### Set Static WAN IP (firmware >= 6.0)
```json
PATCH /api/v2/configuration_managers/{id}/
{
  "configuration": [{
    "wan": {
      "rules2": {
        "00000000-a81d-3590-93ca-8b1fcfeb8e14": {
          "_id_": "00000000-a81d-3590-93ca-8b1fcfeb8e14",
          "ip_mode": "static",
          "static": {
            "ip_address": "172.19.9.30",
            "netmask": "255.255.252.0"
          }
        }
      }
    }
  }, []]
}
```

### Set Custom APN
```json
PATCH /api/v2/configuration_managers/{id}/
{
  "configuration": [{
    "wan": {
      "rules2": {
        "00000002-a81d-3590-93ca-8b1fcfeb8e14": {
          "_id_": "00000002-a81d-3590-93ca-8b1fcfeb8e14",
          "modem": {
            "apn_mode": "manual",
            "manual_apn": "myapn"
          }
        }
      }
    }
  }, []]
}
```

### Clear Individual Config (reset to group/defaults)
```json
PUT /api/v2/configuration_managers/{id}/
{"configuration": [{}, []]}
```

### Resume Suspended Sync
```json
PUT /api/v2/configuration_managers/{id}/
{"suspended": false}
```

## Config Layering

Target config = Group config + Individual config (individual overrides group).

- Removing a device from a group removes group config contributions from target
- Clearing individual config makes target = group config only
- If neither group nor individual sets a value, the firmware default applies

## Config Validation

Configs are validated against the firmware DTD (Document Type Definition).
Even DTD-valid configs can be rejected by the device for dynamic constraint violations.

### Common Validation Errors
- `invalid path` — key doesn't exist in DTD
- `invalid id` — _id_ is not a valid UUID
- `not a string`, `not an integer`, `not a boolean` — type mismatch
- `too large (max=n)`, `too small (min=n)` — value out of range
- `invalid ip address`, `invalid mac address` — format error
- `invalid option` — select value not in allowed list

## Config Rollback

If a device applies a config but can't reach NCM within 15 minutes, it automatically
rolls back to the previous working config and suspends sync.

## Passwords

Password fields return `"*"` on GET. Set passwords by sending cleartext in PUT/PATCH — they are automatically encrypted.

## PATCH with Arrays vs Objects

- Arrays in PATCH body: entire array is replaced
- Objects in PATCH body: only specified keys are updated

Use objects with string keys for partial updates:
```json
{"0": "value at position 0", "1": "value at position 1"}
```

## Recommended Workflow

1. Use NCM UI to create a config on one device (as template)
2. GET the config: `GET /api/v2/configuration_managers/{id}/`
3. Edit the downloaded config
4. PUT/PATCH to other devices: `PUT /api/v2/configuration_managers/{other_id}/`
