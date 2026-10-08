# API v3 Endpoint Reference

Base URL: `https://api.cradlepointecm.com/api/v3/`

## Key Differences from v2

- Uses JSON:API specification (`application/vnd.api+json`)
- Bearer token authentication instead of four API keys
- Different base URL (`api.cradlepointecm.com` vs `www.cradlepointecm.com`)
- Response format follows JSON:API structure with `data`, `attributes`, `relationships`

## Path Conventions (read this first)

Two things about v3 paths differ from v2 and are easy to get wrong. Both are
verified against the official Swagger specs at
`developer.cradlepoint.com/swagger/spec/{endpoint}.json`.

1. **No trailing slash.** The v2 "URLs must end with `/`" rule is a v2 rule. Every
   v3 spec defines its paths **without** a trailing slash (e.g.
   `/api/v3/subscriptions`, not `/api/v3/subscriptions/`). Do not append one.
2. **Many v3 endpoints are not at the bare `/api/v3/` root.** The Private Cellular
   and NetCloud Exchange families live under `/api/v3/beta/...`, and `regrades`
   lives under `/api/v3/asset_endpoints/regrades`. The paths below are the real
   ones; do not "simplify" them to `/api/v3/<name>`.

## Authentication

```
Authorization: Bearer <token>
Content-Type: application/vnd.api+json
Accept: application/vnd.api+json
```

## Endpoints

### subscriptions

```
GET /api/v3/subscriptions
```

Returns information about the subscriptions in your account (the features available
to you in NCM). **GET only** — the spec defines no POST/PUT/DELETE and no item-read
`/{id}` path.

| Parameter | Description |
|---|---|
| `page[size]` | Default 20, **max 50**. |
| `page[after]` / `page[before]` | Cursors. |
| `filter[start_time]` | ISO 8601 date-time. |
| `filter[end_time]` | ISO 8601 date-time. |

Record attributes include `name`, `start_time`, `end_time`, `quantity`,
`feature_list_id`, plus `tenants`, `subscription_type` and `asset_endpoints`
relationships. Required on the record: `name`, `start_time`, `end_time`,
`quantity`, `feature_list_id`.

> **`users` is not a v3 endpoint.** It was previously listed here with full CRUD and
> bearer auth. That is wrong — `users` is a **v2** endpoint (four `X-` header keys,
> GET only). See `api-v2-endpoints.md`.

### regrades

```
GET  /api/v3/asset_endpoints/regrades
GET  /api/v3/asset_endpoints/regrades/{id}
POST /api/v3/asset_endpoints/regrades
```

Bulk upgrade, downgrade, license, or unlicense devices **by MAC address**. Note the
path: `regrades` is nested under `asset_endpoints`, not at `/api/v3/regrades`.

GET requires two filters:

| Filter | Required | Values |
|---|---|---|
| `filter[action]` | **Yes** | `UPGRADE`, `DOWNGRADE`, `LICENSE`, `UNLICENSE` |
| `filter[status]` | **Yes** | `RUNNING`, `COMPLETED`, `FAILED` |
| `filter[action_id]` | No | The shared id of a single bulk operation. |
| `filter[mac_address]`, `filter[subscription_type]`, `filter[created_at]`, `filter[error_code]`, `filter[id]` | No | |

POST uses the **JSON:API atomic operations** extension, so the request
`Content-Type` is `application/vnd.api+json;ext=https://jsonapi.org/ext/atomic` and
the body is an `atomic:operations` array. Each regrade requires `action` and
`mac_address`.

### asset_endpoints

```
GET /api/v3/asset_endpoints
```

### account_authorizations

```
GET /api/v3/account_authorizations
PUT /api/v3/account_authorizations/{id}
```

## Private Cellular Networks (PCN)

The PCN family is served under `/api/v3/beta/` and paths carry **no trailing
slash** (verified against the `private_cellular_*` Swagger specs). POST returns
`201 Created`.

### private_cellular_networks

```
GET    /api/v3/beta/private_cellular_networks
GET    /api/v3/beta/private_cellular_networks/{id}
POST   /api/v3/beta/private_cellular_networks
PUT    /api/v3/beta/private_cellular_networks/{id}
DELETE /api/v3/beta/private_cellular_networks/{id}
```

### private_cellular_cores

```
GET /api/v3/beta/private_cellular_cores
GET /api/v3/beta/private_cellular_cores/{id}
```

### private_cellular_radios

```
GET /api/v3/beta/private_cellular_radios
GET /api/v3/beta/private_cellular_radios/{id}
PUT /api/v3/beta/private_cellular_radios/{id}
```

### private_cellular_radio_groups

```
GET    /api/v3/beta/private_cellular_radio_groups
GET    /api/v3/beta/private_cellular_radio_groups/{id}
POST   /api/v3/beta/private_cellular_radio_groups
PUT    /api/v3/beta/private_cellular_radio_groups/{id}
DELETE /api/v3/beta/private_cellular_radio_groups/{id}
```

### private_cellular_sims

```
GET /api/v3/beta/private_cellular_sims
GET /api/v3/beta/private_cellular_sims/{id}
PUT /api/v3/beta/private_cellular_sims/{id}
```

### private_cellular_radio_statuses

```
GET /api/v3/beta/private_cellular_radio_statuses
GET /api/v3/beta/private_cellular_radio_statuses/{id}
```

## NetCloud Exchange (NCX)

The NCX family is served under `/api/v3/beta/` with **no trailing slash** (verified
against `exchange_sites.json` and `exchange_resources.json`). Resource IDs are
ULIDs. POST returns `201 Created`; DELETE returns `204 No Content`.

### exchange_sites

```
GET    /api/v3/beta/exchange_sites
GET    /api/v3/beta/exchange_sites/{id}
POST   /api/v3/beta/exchange_sites
PUT    /api/v3/beta/exchange_sites/{id}
DELETE /api/v3/beta/exchange_sites/{id}
```

Filters: `filter[name]`, `filter[exchange_network]`, `filter[exchange_site_group]`,
`filter[exchange_site_group][is_null]`. `page[size]` default 25, max 500.

### exchange_resources

```
GET    /api/v3/beta/exchange_resources
GET    /api/v3/beta/exchange_resources/{id}
POST   /api/v3/beta/exchange_resources
PUT    /api/v3/beta/exchange_resources/{id}
DELETE /api/v3/beta/exchange_resources/{id}
```

Filters: `filter[exchange_site]`, `filter[exchange_network]`, `filter[type]`,
`filter[exchange_resource_template][is_null]`. `page[size]` default 20, max 50.

## Modem Software Upgrades

Upgrades the cellular modem firmware (modem software) on the devices in a group.
Distinct from NCOS router firmware, which is v2 `firmwares`.

Source of truth: the official spec at
`https://developer.cradlepoint.com/swagger/spec/Modem_Software_Upgrades.json`
(Swagger UI: `developer.cradlepoint.com/Swagger_UI?ep=Modem_Software_Upgrades`).

These endpoints are **not** beta, despite the Postman collection and
`scripts/test_modem_management_api.py` using `/api/v3/beta/...`. Paths carry no
trailing slash. Auth is the standard v3 Bearer token; request and response bodies
are `application/json`. See `known-issues.md` for the spec-vs-reality
discrepancies — this family has more of them than any other v3 endpoint.

### modem_software_versions

```
GET /api/v3/modem_software_versions
```

| Parameter | Required | Description |
|---|---|---|
| `filter[group]` | **Yes** | Group ID (integer). |
| `page[size]` | No | Default 20, **max 50**. |
| `page[after]` / `page[before]` | No | Cursors. |

Response attributes:

| Attribute | Meaning |
|---|---|
| `carrier` | carrier name, e.g. `verizon`, `att`, `sprint` |
| `package_version` | the modem firmware package version |
| `modem_type_name` | modem module type name, e.g. `LP4` |
| `min_router_version` | minimum router (NCOS) firmware required to accept it |

`carrier` + `modem_type_name` from a record here are exactly the two required
attributes for creating an upgrade, so this is the intended way to populate a
`POST /modem_upgrades` body.

Returns **`204 No Content`** when no packages are available for the group.

### modem_upgrades

```
GET  /api/v3/modem_upgrades
POST /api/v3/modem_upgrades
PUT  /api/v3/modem_upgrades/{id}
```

There is **no `GET /modem_upgrades/{id}`** — it is undocumented and the live API
answers `403 Forbidden`. Read a single job by listing the group's jobs and matching
the ID client-side.

`filter[modem_upgrade_parent]` is genuinely required when
`filter[type]=modem_upgrade_child`; omitting it is a `400` naming the missing filter.

Jobs are modelled as a **parent** record with one **child** record per modem. The
children are the per-device progress rows — that is how you monitor an upgrade.

| Parameter | Required | Description |
|---|---|---|
| `filter[group]` | **Yes** | Group ID (integer). |
| `filter[type]` | **Yes** | `modem_upgrade_parent` (jobs) or `modem_upgrade_child` (per-modem activities). |
| `filter[modem_upgrade_parent]` | When `type=modem_upgrade_child` | Parent job ID. |
| `page[size]` | No | Default 20, **max 50**. |
| `page[after]` / `page[before]` | No | Cursors. |

Returns **`204 No Content`** when no jobs or activities match.

#### Request body

```json
{
  "data": {
    "type": "modem_upgrades",
    "attributes": {
      "carrier": "att",
      "modem_type_name": "LP4",
      "operation": "preview",
      "overwrite": false,
      "connection_states": ["connected"]
    },
    "relationships": {
      "group": { "data": { "type": "groups", "id": "123456" } }
    }
  }
}
```

Required attributes: `carrier`, `modem_type_name`, `operation`. Required
relationship: `group`. PUT uses the same body plus `data.id`.

| Attribute | Values |
|---|---|
| `operation` | `preview` \| `upgrade` \| `cancel` |
| `overwrite` | Upgrade modems already on the target version. Default `false`. |
| `connection_states` | Restrict to modems in these states: `connected`, `disconnected`, `standby`. Nullable, default null. |

`operation: "preview"` is the API's **dry run**: it creates a job and evaluates the
group without pushing anything. Preview first, then repeat the same request with
`operation: "upgrade"`. Cancel with `operation: "cancel"` as a PUT against the job
ID.

**A preview yields only a count.** Verified live 2026-09-28: preview jobs create no
child activity records, so the parent's `modem_count` is the entire answer, and the
job settles at the undocumented `status: "preview"`. Do not poll for preview
children — see `known-issues.md`.

Note the asymmetry in the `group` relationship: requests send a single object
(`"data": {"type": "groups", "id": "..."}`), responses return an **array**
(`"data": [{"type": "groups", "id": "..."}]`). Parse defensively.

The spec documents `201 Created` for POST; in practice the API returns `200 OK`
(see `known-issues.md`). Accept both.

#### Status values

`status` is an enum, and the values are not the conventional ones:

| Status | Terminal? |
|---|---|
| `created`, `queued`, `initializing`, `running` | no |
| `finished` | yes — succeeded |
| `error` | yes — failed |
| `canceled` | yes — cancelled (single `l`) |

Matching on `completed` or `cancelled` will never fire.

#### Jobs are group-scoped — there is no per-router target

The only target this endpoint accepts is the `group` relationship. There is no
`router`, `net_device`, or ID-list attribute, so an upgrade necessarily applies to
every matching modem in the group. Narrow the blast radius by moving devices into
their own group first; filtering a device list client-side does **not** reduce what
the job touches.

#### Progress fields

The spec defines one schema for both parents and children:

`carrier`, `overwrite`, `operation`, `package_version`, `modem_count`,
`success_count`, `failed_count`, `status`, `modem_type_name`, `connection_states`,
`created_at`, `updated_at`, plus a `group` relationship.

That is a gap for children: the schema says nothing about how a child identifies
*which* modem it represents. In practice children reference a modem by
`net_device` ID, and the SDK's older code lists `router_name`, `net_device_name`
and `current_version` as available. Extract these defensively.

Because a `net_device` ID is not human-readable, join it against v2
`net_devices/?id__in=...&expand=router` to get the parent router name, model and
the firmware the modem is currently on. That join needs v2 header credentials in
addition to the v3 token.

SDK: `get_modem_software_versions()`, `get_modem_upgrades()`,
`create_modem_upgrade()`, `update_modem_upgrade()`. Their paths match the spec, but
`get_modem_upgrades(modem_upgrade_id=...)` builds an item-read URL the spec does
not define.

## Public SIM Management

Paths follow the v3 no-trailing-slash convention. The exact base (bare `/api/v3/`
vs `/api/v3/beta/`) was not cross-checked against a Swagger spec here — confirm
against `swagger/spec/public_sim_mgmt_*.json` before relying on it.

### public_sim_mgmt_assets

```
GET /api/v3/public_sim_mgmt_assets
```

### public_sim_mgmt_rate_plans

```
GET /api/v3/public_sim_mgmt_rate_plans
```

## JSON:API Response Format

v3 responses follow JSON:API format:

```json
{
  "data": [
    {
      "type": "subscriptions",
      "id": "123",
      "attributes": {
        "name": "...",
        "status": "..."
      },
      "relationships": {
        "account": {
          "data": { "type": "accounts", "id": "456" }
        }
      }
    }
  ],
  "meta": {
    "pagination": {
      "count": 100,
      "pages": 5
    }
  }
}
```
