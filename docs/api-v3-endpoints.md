# API v3 Endpoint Reference

Base URL: `https://api.cradlepointecm.com/api/v3/`

## Key Differences from v2

- Uses JSON:API specification (`application/vnd.api+json`)
- Bearer token authentication instead of four API keys
- Different base URL (`api.cradlepointecm.com` vs `www.cradlepointecm.com`)
- Response format follows JSON:API structure with `data`, `attributes`, `relationships`

## Authentication

```
Authorization: Bearer <token>
Content-Type: application/vnd.api+json
Accept: application/vnd.api+json
```

## Endpoints

### subscriptions

```
GET /api/v3/subscriptions/
GET /api/v3/subscriptions/{id}/
```

Manage account subscription information.

### users

```
GET /api/v3/users/
GET /api/v3/users/{id}/
POST /api/v3/users/
PUT /api/v3/users/{id}/
PATCH /api/v3/users/{id}/
DELETE /api/v3/users/{id}/
```

View, add, modify and delete account users.

### regrades

```
GET /api/v3/regrades/
POST /api/v3/regrades/
```

Upgrade/downgrade device subscriptions.

### asset_endpoints

```
GET /api/v3/asset_endpoints/
```

### account_authorizations

```
GET /api/v3/account_authorizations/
PUT /api/v3/account_authorizations/{id}/
```

## Private Cellular Networks (PCN)

### private_cellular_networks

```
GET /api/v3/private_cellular_networks/
GET /api/v3/private_cellular_networks/{id}/
POST /api/v3/private_cellular_networks/
PUT /api/v3/private_cellular_networks/{id}/
DELETE /api/v3/private_cellular_networks/{id}/
```

### private_cellular_cores

```
GET /api/v3/private_cellular_cores/
GET /api/v3/private_cellular_cores/{id}/
```

### private_cellular_radios

```
GET /api/v3/private_cellular_radios/
GET /api/v3/private_cellular_radios/{id}/
PUT /api/v3/private_cellular_radios/{id}/
```

### private_cellular_radio_groups

```
GET /api/v3/private_cellular_radio_groups/
GET /api/v3/private_cellular_radio_groups/{id}/
POST /api/v3/private_cellular_radio_groups/
PUT /api/v3/private_cellular_radio_groups/{id}/
DELETE /api/v3/private_cellular_radio_groups/{id}/
```

### private_cellular_sims

```
GET /api/v3/private_cellular_sims/
GET /api/v3/private_cellular_sims/{id}/
PUT /api/v3/private_cellular_sims/{id}/
```

### private_cellular_radio_statuses

```
GET /api/v3/private_cellular_radio_statuses/
GET /api/v3/private_cellular_radio_statuses/{id}/
```

## NetCloud Exchange (NCX)

### exchange_sites

```
GET /api/v3/exchange_sites/
GET /api/v3/exchange_sites/{id}/
POST /api/v3/exchange_sites/
PUT /api/v3/exchange_sites/{id}/
DELETE /api/v3/exchange_sites/{id}/
```

### exchange_resources

```
GET /api/v3/exchange_resources/
GET /api/v3/exchange_resources/{id}/
POST /api/v3/exchange_resources/
PUT /api/v3/exchange_resources/{id}/
DELETE /api/v3/exchange_resources/{id}/
```

## Public SIM Management

### public_sim_mgmt_assets

```
GET /api/v3/public_sim_mgmt_assets/
```

### public_sim_mgmt_rate_plans

```
GET /api/v3/public_sim_mgmt_rate_plans/
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
