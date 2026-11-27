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

**This list is persisted state, not a one-time delete, so it means different things
at group and device scope.** At group scope it prunes what the group contributes. At
device scope the stored diff *is* the override layer, so a removals path there
suppresses the path from what the **group** supplies. To make a device stop
overriding the group and inherit it instead, delete the key from the updates dict —
adding it to the removals list persists a new override that blocks the group's value.
See "The Removals List Means Different Things at Group and Device Scope" in
`known-issues.md`.

**Works with PATCH as well as PUT.** NCM's own UI removes config via PATCH with an
empty updates dict and a populated removals list, so you do not need PUT (and its
reset-unmentioned-fields behavior) just to delete something.

A path walks the config tree. Object keys are strings; **array positions are
integers**, unlike in the updates dict where the same position is a string key:

```json
[{}, [["identities", "ip", "0897fa24-b4a4-4aa2-9cab-0bed9507c233", "members", 2]]]
```

Stopping the path short removes the whole entry rather than one of its elements:

```json
[{}, [["identities", "ip", "0897fa24-b4a4-4aa2-9cab-0bed9507c233"]]]
```

Both diff slots may be used in a single PATCH — set values via updates and prune
via removals in one call. When removing several elements from one array, emit the
indices highest-first so the paths remain valid regardless of whether NCM resolves
them against the pre-change config or applies them sequentially with reindexing.

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

**Default to PATCH for every config write.** Send only the settings you are changing.
Set or change values in the updates dict. Delete a setting with a removals path.
Use PUT only when the user explicitly asks to replace or wipe the whole config.

**Never read-modify-write with PUT.** GET returns every password, PSK and key as `"*"`
(see Passwords below). A PUT of the config you just read sends `*` back as the literal
secret, which NCM either rejects
(`cannot set wlan.radio.1.bss.0.wpapsk to *: too short`) or stores.

| Behavior | PUT | PATCH |
|----------|-----|-------|
| Unmentioned fields | Reset to defaults | Left unchanged |
| Use case | Replace entire config (explicit request only) | Every other change |
| Can remove items | Yes (via removals list) | Yes (via removals list) — see below |
| Returns payload | Yes | No |

### Removing one setting (PATCH)

```json
PATCH /api/v2/configuration_managers/{id}/
{"configuration": [{}, [["wan", "rules2", "00000005-a81d-3590-93ca-8b1fcfeb8e15", "modem"]]]}
```

At device scope this deletes the device's own override for that path. No removals
entry is persisted, and the setting reverts to its default (verified live on a device
with no group). PATCHing `null` instead does **not** delete the setting; it stores an
explicit `null`. See `known-issues.md` → "PATCH Removals Delete a Device-Level
Override".

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

**Only when the user explicitly asks to wipe the device's entire individual config.**
This deliberately discards every device-level setting. To clear one setting, use
the PATCH removal above.

```json
PUT /api/v2/configuration_managers/{id}/
{"configuration": [{}, []]}
```

### Resume Suspended Sync

This is a PUT. The PATCH-only rule covers changes to actual configuration values,
and resuming sync only flips the record's `suspended` flag.

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

Password fields return `"*"` on GET. Set passwords by sending cleartext in a PATCH;
NCM encrypts them automatically.

Never send a config you read back to NCM. Every secret in it is the literal `"*"`. Only
put a password field in a write body when you are deliberately setting that password.

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
3. Extract only the branches you want to apply, and strip every `"*"` secret
   placeholder.
4. PATCH that fragment to other devices: `PATCH /api/v2/configuration_managers/{other_id}/`.
   Set any passwords explicitly in cleartext. Use PUT only if the user explicitly asks
   to replace the target's whole config.
