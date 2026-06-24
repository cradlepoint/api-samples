# Geo IP Blocker

A web application for generating and deploying geographic IP blocking rules to Cradlepoint routers via the NetCloud Manager API. Select countries or entire regions to block, and the tool converts their IP address ranges into zone firewall (ZFW) filter policy rules that can be pushed directly to NCM groups.

<img width="1639" height="845" alt="image" src="https://github.com/user-attachments/assets/4142307a-14ba-4261-b217-8a1bb0e17fb6" />
<img width="1639" height="845" alt="image" src="https://github.com/user-attachments/assets/c85e2921-a97f-4213-bead-141cef0c572c" />
<img width="1639" height="845" alt="image" src="https://github.com/user-attachments/assets/38a97809-5547-4c7d-aa92-e8921447302e" />

## How It Works

1. **Select Regions** — Choose individual countries or entire geographic regions to block. IP address ranges are sourced from [ipdeny.com](https://www.ipdeny.com/ipblocks/) aggregated zone files.

2. **Review Rules** — The tool generates a ZFW filter policy named `GeoBlock-Policy` containing deny rules for each selected country. Each country's IP blocks are stored as an IP identity, and the corresponding deny rule references that identity. The policy's default action is `allow`, so only traffic from the selected countries is blocked. The generated configuration can be copied to clipboard or downloaded as JSON.

3. **Push to Groups** — Select one or more NCM groups and apply the configuration via PATCH. This merges the geo-blocking rules into the existing group configuration without removing any existing ZFW rules.

## Important: Applying the Filter Policy to Forwarding Rules

This tool creates the ZFW filter policy and associated IP identities, but **does not automatically assign the policy to any zone forwarding rules**. After pushing the configuration to a group, you must manually assign the `GeoBlock-Policy` to the appropriate forwarding rule(s) in the device or group configuration to activate enforcement.

To apply the policy:
1. Navigate to the group or device configuration in NetCloud Manager
2. Open **Security > Zone Firewall > Forwarding Rules**
3. Edit the relevant forwarding rule (e.g., LAN-to-WAN or WAN-to-LAN)
4. Assign `GeoBlock-Policy` as the filter policy for that forwarding rule
5. Save the configuration

Without this step, the filter policy exists in the configuration but does not actively filter traffic.

## Usage

```bash
.venv/bin/python web_apps/geo_ip_blocker/serve.py
```

Open http://localhost:8065 in your browser.

## Requirements

- Python 3.12+ with the project virtual environment (`.venv`)
- FastAPI, uvicorn, httpx (included in project `requirements.txt`)
- NCM SDK (`ncm` package in this repository)
- Valid NCM API credentials (v2)

## Configuration

API credentials can be provided in two ways:

- **Environment variables** — Set `X_CP_API_ID`, `X_CP_API_KEY`, `X_ECM_API_ID`, and `X_ECM_API_KEY` before starting the server. These load automatically on startup.
- **Settings panel** — Click the gear icon in the application header to enter credentials directly. Credentials can be saved as named profiles for reuse.

## Generated Configuration Structure

The tool produces a configuration diff suitable for PATCH operations:

```json
{
  "configuration": [
    {
      "security": {
        "zfw": {
          "filter_policies": {
            "<uuid>": {
              "_id_": "<uuid>",
              "name": "GeoBlock-Policy",
              "default_action": "allow",
              "rules": {
                "0": {
                  "action": "deny",
                  "ip_version": "ip4",
                  "name": "Block <Country> (<CODE>)",
                  "src": { "ip": { "0": { "identity": "<identity-uuid>" } } }
                }
              }
            }
          }
        }
      },
      "identities": {
        "ip": {
          "<identity-uuid>": {
            "_id_": "<identity-uuid>",
            "name": "GeoBlock-<CODE>-<Country>",
            "members": [
              { "address": "x.x.x.x/xx" }
            ]
          }
        }
      }
    },
    []
  ]
}
```

## IP Block Source

Country-level IP address ranges are fetched in real time from [ipdeny.com](https://www.ipdeny.com/ipblocks/) aggregated zone files. These are CIDR-notation blocks allocated to each country by regional internet registries.
