# NetCloud Manager API Overview

## What is the NCM API?

The NetCloud Manager (NCM) API is a RESTful API for programmatically managing Cradlepoint
network devices (routers, access points). It mirrors most functionality available in the
NCM web UI.

## API Versions

There are two active API versions:

### API v2
- Base URL: `https://www.cradlepointecm.com/api/v2/`
- Authentication: Four header-based API keys
- Content-Type: `application/json`
- Covers: routers, groups, configs, alerts, locations, net_devices, firmware, etc.

### API v3
- Base URL: `https://api.cradlepointecm.com/api/v3/`
- Authentication: Bearer token
- Content-Type: `application/vnd.api+json` (JSON:API spec)
- Covers: subscriptions, users, private cellular, NCX sites/resources

## Authentication

### API v2 Headers (all four required)
```
X-CP-API-ID: <your_cp_api_id>
X-CP-API-KEY: <your_cp_api_key>
X-ECM-API-ID: <your_ecm_api_id>
X-ECM-API-KEY: <your_ecm_api_key>
Content-Type: application/json
```

### API v3 Headers
```
Authorization: Bearer <your_token>
Content-Type: application/vnd.api+json
Accept: application/vnd.api+json
```

### Getting API Keys
1. Login to NCM at https://accounts.cradlepointecm.com
2. Click TOOLS in the left navigation
3. Scroll to the NetCloud API section
4. Click the API Portal link

## HTTP Methods

| Method | Purpose |
|--------|---------|
| GET    | Retrieve resources |
| POST   | Create resources |
| PUT    | Replace entire resource |
| PATCH  | Partial update of resource |
| DELETE | Remove resource |

Not all endpoints support all methods. Some are read-only (GET only).

## Critical Rules

1. **Trailing slash required**: All endpoint URLs MUST end with `/`. Missing trailing slash
   causes a redirect, resulting in two calls counted against your account.
   - Correct: `https://www.cradlepointecm.com/api/v2/routers/`
   - Wrong: `https://www.cradlepointecm.com/api/v2/routers`

2. **TLS 1.2+ required**: SSL and earlier TLS versions are not supported (PCI 3.2 compliance).

3. **CA Trust**: API clients must trust Google Trust Services CA.

## Pagination (v2)

All list endpoints return paginated results:
```json
{
  "data": [...],
  "meta": {
    "limit": 20,
    "next": "https://www.cradlepointecm.com/api/v2/routers/?limit=20&offset=20",
    "offset": 0,
    "previous": null
  }
}
```

Parameters:
- `limit` — max records per page (default 20, max 500)
- `offset` — starting index for pagination

To iterate all records, follow the `meta.next` URL until it is `null`.

## Filtering (v2)

Most endpoints support filtering via query parameters:
```
GET /api/v2/routers/?state=online
GET /api/v2/routers/?id__in=1,2,3
GET /api/v2/net_devices/?router__in=100,200
```

Common filter operators:
- `=` — exact match
- `__in` — match any in comma-separated list
- `__gt` — greater than
- `__lt` — less than
- `__gte` — greater than or equal
- `__lte` — less than or equal

## Partial Returns

Use `fields` parameter to request only specific fields:
```
GET /api/v2/routers/?fields=id,name,state
```

## Expanding Related Resources

Use `expand` to inline related resources instead of getting URLs:
```
GET /api/v2/routers/?expand=group,account
```

## Rate Limiting

The API has rate limits. Use retry logic with exponential backoff.
Recommended: 5 retries with backoff factor of 2, retry on 408, 503, 504.

## Environment Variables

The NCM SDK supports these environment variables:
- `CP_BASE_URL` — Override v2 base URL (default: `https://www.cradlepointecm.com/api/v2`)
- `CP_BASE_URL_V3` — Override v3 base URL (default: `https://api.cradlepointecm.com/api/v3`)
