# API Deprecation Notes

## Active Deprecations

| Item | Type | Deprecated Date | Action Required |
|------|------|----------------|-----------------|
| `overlay_network_bindings` | Endpoint | 09/30/2024 | Remove all references |
| `forwarding_lan_details` | Endpoint | 09/30/2024 | Remove all references |
| `routers.overlay_network_binding` | Field | 09/30/2024 | Remove field references |
| `net_devices.is_upgrade_available` | Field | 12/31/2023 | Remove references (field still appears but returns inaccurate data) |

## Certificate Authority Change

As of August 15, 2024, NCM uses Google Trust Services as its CA (previously DigiCert).
API clients must trust this CA or they will get SSL verification errors.

## API v1 → v2 Migration

API v1 is fully deprecated. Key differences:
- Config fields (`configuration`, `actual`, `target`, `pending`) are inline JSON, not URLs
- `resource_uri` renamed to `resource_url` (full URL)
- `pending_patch` removed (use `pending` instead)
- `account` and `router` fields are full URLs
- `lock` field removed
