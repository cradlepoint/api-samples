# NetCloud Webhooks

## Overview

Webhooks notify your application when NCM alerts occur. They use a direct-messaging
approach following RFC 8030.

## Setup Process

1. Create an Alert Push Destination via `alert_push_destinations` endpoint
   - Set `endpoint` to your webhook URL
   - Set `authentication` to a secret value for HMAC validation
2. Test it via `test_alert_push_destination` endpoint
3. Create an Alert Rule and link it to the push destination
   - Add the `destination_config_id` from step 1 to the `http_destinations` field in the alert rule

## Webhook Validation

NCM signs webhook payloads with HMAC-SHA256. Validate using the `x-cp-signature` header:

### Python Example
```python
import hmac

def validate_webhook(body: str, headers: dict, secret: str) -> bool:
    h = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), "sha256")
    signature = h.hexdigest()
    return signature == headers.get("x-cp-signature")
```

## Alert Types

Webhooks can be triggered by these alert types:
- `connection_state` — online/offline
- `cpu_utilization` — CPU threshold exceeded
- `data_cap_threshold` — data cap reached
- `ethernet_wan_connected` / `ethernet_wan_disconnected`
- `ethernet_wan_plugged` / `ethernet_wan_standby`
- `ipsec_tunnel_down` / `ipsec_tunnel_up`
- `login_success` — successful router login
- `memory_utilization` — memory threshold exceeded
- `modem_wan_connected` / `modem_wan_disconnected`
- `modem_wan_plugged` / `modem_wan_unplugged`
- `reboot_status_change`
- `sim_door_event`
- `sustained_system_overload`
- `thermal_exceeds_limit`
- `wan_service_type`
- `wifi_client_state_change`
- `wwan_connected` / `wwan_disconnected`
- `wwan_network_available` / `wwan_network_unavailable`
- `wwan_standby`

## Payload Format

```json
{
  "type": "connection_state",
  "info": { ... },
  "router": { ... },
  "account": { ... }
}
```

The `info` object varies by alert type. The `type` field identifies which alert triggered.

## Troubleshooting Suspended Webhooks

Webhooks can enter a Suspended state due to:
1. Invalid authentication secret — verify the secret matches in NCM config
2. Unreachable URL — verify the webhook URL is correct and accessible
3. SSL vulnerabilities — ensure destination endpoint SSL libraries are up-to-date
