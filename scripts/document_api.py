"""
Fetch swagger specs and sample GET responses for all NCM API v2 endpoints.
Outputs a comprehensive doc and a gaps file.

Usage:
    source .venv/bin/activate
    python scripts/document_api.py
"""

import os
import sys
import json
import time
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

ENDPOINTS = [
    "accounts",
    "activity_logs",
    "alerts",
    "alert_rules",
    "alert_push_destinations",
    "batteries",
    "configuration_managers",
    "device_apps",
    "device_app_bindings",
    "device_app_states",
    "device_app_versions",
    "failovers",
    "firmwares",
    "groups",
    "historical_locations",
    "locations",
    "net_devices",
    "net_device_health",
    "net_device_metrics",
    "net_device_signal_samples",
    "net_device_usage_samples",
    "products",
    "reboot_activity",
    "router_alerts",
    "router_logs",
    "router_state_samples",
    "router_stream_usage_samples",
    "routers",
    "speed_test",
    "users",
]

SPEC_BASE = "https://developer.cradlepoint.com/swagger/spec"
API_BASE = "https://www.cradlepointecm.com/api/v2"

def get_headers():
    return {
        "X-CP-API-ID": os.environ.get("X_CP_API_ID", ""),
        "X-CP-API-KEY": os.environ.get("X_CP_API_KEY", ""),
        "X-ECM-API-ID": os.environ.get("X_ECM_API_ID", ""),
        "X-ECM-API-KEY": os.environ.get("X_ECM_API_KEY", ""),
        "Content-Type": "application/json",
    }


def fetch_spec(endpoint):
    """Fetch the swagger spec for an endpoint."""
    url = f"{SPEC_BASE}/{endpoint}.json"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def fetch_sample(endpoint, headers):
    """Fetch one sample record from the endpoint."""
    url = f"{API_BASE}/{endpoint}/?limit=1"
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}", "body": resp.text[:500]}
    except Exception as e:
        return {"error": str(e)}


def extract_params(spec):
    """Extract query parameters from spec."""
    params = []
    apis = spec.get("apis", [])
    for api in apis:
        for op in api.get("operations", []):
            for p in op.get("parameters", []):
                if p.get("paramType") == "query":
                    params.append({
                        "name": p.get("name"),
                        "type": p.get("type", ""),
                        "required": p.get("required", False),
                        "description": p.get("description", ""),
                    })
    return params


def extract_response_fields(sample):
    """Extract field names and types from a sample response."""
    data = sample.get("data", [])
    if not data:
        return []
    record = data[0] if isinstance(data, list) else data
    fields = []
    for key, val in sorted(record.items()):
        val_type = type(val).__name__ if val is not None else "null"
        sample_val = val
        if isinstance(val, str) and len(val) > 80:
            sample_val = val[:80] + "..."
        fields.append({
            "name": key,
            "type": val_type,
            "sample": sample_val,
        })
    return fields


def main():
    headers = get_headers()
    if not headers["X-CP-API-ID"]:
        print("ERROR: API keys not set. Source .venv/bin/activate first.")
        sys.exit(1)

    docs_output = []
    gaps = []

    print(f"Documenting {len(ENDPOINTS)} endpoints...\n")

    for endpoint in ENDPOINTS:
        print(f"  {endpoint}...", end=" ", flush=True)

        # Fetch spec
        spec = fetch_spec(endpoint)
        spec_ok = "error" not in spec
        params = extract_params(spec) if spec_ok else []

        # Fetch sample
        sample = fetch_sample(endpoint, headers)
        sample_ok = "error" not in sample
        fields = extract_response_fields(sample) if sample_ok else []

        # Track gaps
        if not spec_ok:
            gaps.append(f"{endpoint}: Spec not available ({spec.get('error', 'unknown')})")
        if not sample_ok:
            gaps.append(f"{endpoint}: GET failed ({sample.get('error', 'unknown')})")
        if spec_ok and not params:
            gaps.append(f"{endpoint}: Spec has no query parameters documented")
        if sample_ok and not fields:
            gaps.append(f"{endpoint}: GET returned no data (empty account or POST-only)")

        # Build doc entry
        entry = f"## {endpoint}\n\n"
        entry += f"```\nGET /api/v2/{endpoint}/\n```\n\n"

        if params:
            entry += "### Query Parameters\n\n"
            entry += "| Name | Type | Required | Description |\n"
            entry += "|------|------|----------|-------------|\n"
            for p in params:
                desc = p['description'].replace('<strong>', '').replace('</strong>', '').replace('<br />', ' / ')
                entry += f"| `{p['name']}` | {p['type']} | {p['required']} | {desc} |\n"
            entry += "\n"

        if fields:
            entry += "### Response Fields\n\n"
            entry += "| Field | Type | Sample Value |\n"
            entry += "|-------|------|--------------|\n"
            for f in fields:
                sv = str(f['sample']) if f['sample'] is not None else "null"
                if len(sv) > 60:
                    sv = sv[:60] + "..."
                sv = sv.replace("|", "\\|")
                entry += f"| `{f['name']}` | {f['type']} | {sv} |\n"
            entry += "\n"
        elif sample_ok:
            entry += "*No data returned (endpoint may be empty or POST-only)*\n\n"

        entry += "---\n\n"
        docs_output.append(entry)

        status = "✓" if (spec_ok and sample_ok and fields) else "⚠"
        print(status)

        # Rate limit courtesy
        time.sleep(0.5)

    # Write docs
    docs_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'api-v2-full-reference.md')
    with open(docs_path, 'w') as f:
        f.write("# NCM API v2 Full Endpoint Reference\n\n")
        f.write("Auto-generated from Swagger specs and live API responses.\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
        f.write(f"Base URL: `https://www.cradlepointecm.com/api/v2/`\n\n")
        f.write("---\n\n")
        for entry in docs_output:
            f.write(entry)

    print(f"\n✓ Documentation written to: {docs_path}")

    # Write gaps
    gaps_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'api-documentation-gaps.md')
    with open(gaps_path, 'w') as f:
        f.write("# NCM API Documentation Gaps\n\n")
        f.write("Issues found while auto-documenting the API.\n\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
        if gaps:
            for g in gaps:
                f.write(f"- {g}\n")
        else:
            f.write("No gaps found.\n")

    print(f"✓ Gaps written to: {gaps_path}")
    if gaps:
        print(f"\n⚠ {len(gaps)} documentation gap(s) found:")
        for g in gaps:
            print(f"  - {g}")


if __name__ == "__main__":
    main()
