"""
Test script for the Modem Management API (v3 beta).
Exercises all endpoints from the OpenAPI spec:
  1. GET  /api/v3/beta/modem_software_versions/
  2. GET  /api/v3/beta/modem_upgrades/  (parent jobs)
  3. GET  /api/v3/beta/modem_upgrades/  (child activities)
  4. POST /api/v3/beta/modem_upgrades/
  5. PUT  /api/v3/beta/modem_upgrades/{id}/

Usage:
  export V3_BEARER_TOKEN="your_token"
  export TEST_GROUP_ID="123"
  python scripts/test_modem_management_api.py
"""

import os
import sys
import json
from time import sleep

import requests

# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------
# check_env() requires v2 keys which we don't need here. Validate v3 vars
# manually following the same pattern (print instructions, exit on failure).
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from utils.env_check import check_env  # noqa: E402

# check_env() validates v2 keys and prints to stderr before exiting.
# This is a v3-only script so we suppress the output and swallow the exit.
import io as _io
try:
    _stderr = sys.stderr
    sys.stderr = _io.StringIO()
    check_env()
except SystemExit:
    pass  # v2 keys are optional for this v3-only script
finally:
    sys.stderr = _stderr

TOKEN = os.environ.get("V3_BEARER_TOKEN", "")
GROUP_ID = os.environ.get("TEST_GROUP_ID", "")

_missing = []
if not TOKEN:
    _missing.append("V3_BEARER_TOKEN")
if not GROUP_ID:
    _missing.append("TEST_GROUP_ID")
if _missing:
    print(f"ERROR: Set the following env vars before running: {', '.join(_missing)}", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get("CP_BASE_URL_V3", "https://api.cradlepointecm.com")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/vnd.api+json",
    "Accept": "application/vnd.api+json",
}

passed = 0
failed = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api_call_with_retry(method, url, max_retries=5, backoff=2, **kwargs):
    """Make an HTTP request with retry on transient/rate-limit errors.
    Handles 409 as rate-limit per known-issues.md, but only when the
    response body doesn't contain a JSON:API validation error."""
    for attempt in range(max_retries):
        resp = method(url, **kwargs)
        if resp.status_code in (408, 429, 500, 502, 503, 504):
            wait = backoff ** attempt
            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", wait))
            print(f"  ↻ Retry {attempt + 1}/{max_retries} after {wait}s (HTTP {resp.status_code})")
            sleep(wait)
            continue
        # 409 can be rate-limit OR a real validation error (JSON:API errors array)
        if resp.status_code == 409:
            try:
                body = resp.json()
                if "errors" in body:
                    return resp  # real validation error, don't retry
            except Exception:
                pass
            wait = backoff ** attempt
            print(f"  ↻ Retry {attempt + 1}/{max_retries} after {wait}s (HTTP 409 rate-limit)")
            sleep(wait)
            continue
        return resp
    return resp  # return last response even if still failing


def report(name, resp):
    """Print result and update pass/fail counters."""
    global passed, failed
    status = resp.status_code
    try:
        body = resp.json()
    except Exception:
        body = resp.text

    if status in (200, 201, 204):
        passed += 1
        tag = "PASS"
    else:
        failed += 1
        tag = "FAIL"

    print(f"\n[{tag}] {name} — HTTP {status}")
    if isinstance(body, (dict, list)):
        print(json.dumps(body, indent=2)[:2000])  # cap output
    else:
        print(str(body)[:2000])
    print("-" * 60)
    return body, status


# ---------------------------------------------------------------------------
# 1. GET /api/v3/beta/modem_software_versions/
# ---------------------------------------------------------------------------

def test_list_modem_software_versions():
    """List available modem firmware packages for the group."""
    url = f"{BASE_URL}/api/v3/beta/modem_software_versions"
    params = {"filter[group]": GROUP_ID, "page[size]": 5}
    resp = api_call_with_retry(requests.get, url, headers=HEADERS, params=params)
    return report("GET modem_software_versions", resp)


# ---------------------------------------------------------------------------
# 2. GET /api/v3/beta/modem_upgrades/ (parent jobs)
# ---------------------------------------------------------------------------

def test_list_modem_upgrade_jobs():
    """List modem upgrade parent jobs for the group."""
    url = f"{BASE_URL}/api/v3/beta/modem_upgrades"
    params = {
        "filter[group]": GROUP_ID,
        "filter[type]": "modem_upgrade_parent",
        "page[size]": 5,
    }
    resp = api_call_with_retry(requests.get, url, headers=HEADERS, params=params)
    return report("GET modem_upgrades (parent jobs)", resp)


# ---------------------------------------------------------------------------
# 3. GET /api/v3/beta/modem_upgrades/ (child activities)
# ---------------------------------------------------------------------------

def test_list_modem_upgrade_activities(parent_job_id):
    """List child activities for a specific parent job."""
    url = f"{BASE_URL}/api/v3/beta/modem_upgrades"
    params = {
        "filter[group]": GROUP_ID,
        "filter[type]": "modem_upgrade_child",
        "filter[modem_upgrade_parent]": parent_job_id,
        "page[size]": 5,
    }
    resp = api_call_with_retry(requests.get, url, headers=HEADERS, params=params)
    return report(f"GET modem_upgrades (child activities for job {parent_job_id})", resp)


# ---------------------------------------------------------------------------
# 4. POST /api/v3/beta/modem_upgrades/  (preview — safe dry run)
# ---------------------------------------------------------------------------

def test_create_modem_upgrade_preview(carrier, modem_type_name):
    """Create a preview (dry-run) modem upgrade job."""
    url = f"{BASE_URL}/api/v3/beta/modem_upgrades"
    payload = {
        "data": {
            "type": "modem_upgrades",
            "attributes": {
                "carrier": carrier,
                "modem_type_name": modem_type_name,
                "operation": "preview",
                "overwrite": False,
                "connection_states": ["connected"],
            },
            "relationships": {
                "group": {
                    "data": {
                        "type": "groups",
                        "id": str(GROUP_ID),
                    }
                }
            },
        }
    }
    resp = api_call_with_retry(requests.post, url, headers=HEADERS, json=payload)
    return report("POST modem_upgrades (preview)", resp)


# ---------------------------------------------------------------------------
# 5. PUT /api/v3/beta/modem_upgrades/{id}/  (cancel the preview job)
# ---------------------------------------------------------------------------

def test_update_modem_upgrade(job_id, carrier, modem_type_name):
    """Update (cancel) an existing modem upgrade job."""
    url = f"{BASE_URL}/api/v3/beta/modem_upgrades/{job_id}"
    payload = {
        "data": {
            "type": "modem_upgrades",
            "attributes": {
                "carrier": carrier,
                "modem_type_name": modem_type_name,
                "operation": "cancel",
            },
            "relationships": {
                "group": {
                    "data": {
                        "type": "groups",
                        "id": str(GROUP_ID),
                    }
                }
            },
        }
    }
    resp = api_call_with_retry(requests.put, url, headers=HEADERS, json=payload)
    return report(f"PUT modem_upgrades/{job_id} (cancel)", resp)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    global passed, failed

    print("=" * 60)
    print("Modem Management API — Test Run")
    print(f"Base URL : {BASE_URL}")
    print(f"Group ID : {GROUP_ID}")
    print("=" * 60)

    # 1 — List modem software versions
    sw_body, sw_status = test_list_modem_software_versions()

    # Pick carrier + modem_type_name from the first result (if any) for later tests
    carrier = None
    modem_type_name = None
    if sw_status == 200 and isinstance(sw_body, dict):
        items = sw_body.get("data", [])
        if items:
            attrs = items[0].get("attributes", {})
            carrier = attrs.get("carrier")
            modem_type_name = attrs.get("modem_type_name")
            print(f"\n  → Using carrier={carrier}, modem_type_name={modem_type_name} for remaining tests")

    # 2 — List parent upgrade jobs
    jobs_body, jobs_status = test_list_modem_upgrade_jobs()

    # 3 — List child activities (use first parent job if available)
    parent_id = None
    if jobs_status == 200 and isinstance(jobs_body, dict):
        items = jobs_body.get("data", [])
        if items:
            parent_id = items[0].get("id")
    if parent_id:
        test_list_modem_upgrade_activities(parent_id)
    else:
        print("\n[SKIP] GET modem_upgrades (child activities) — no parent job found")

    # 4 & 5 — POST preview then PUT cancel (only if we have carrier info)
    if carrier and modem_type_name:
        create_body, create_status = test_create_modem_upgrade_preview(carrier, modem_type_name)

        job_id = None
        if create_status in (200, 201) and isinstance(create_body, dict):
            job_id = create_body.get("data", {}).get("id")

        if job_id:
            test_update_modem_upgrade(job_id, carrier, modem_type_name)
        else:
            print("\n[SKIP] PUT modem_upgrades/{id} — no job ID from POST")
    else:
        print("\n[SKIP] POST modem_upgrades (preview) — no modem software versions found for group")
        print("[SKIP] PUT modem_upgrades/{id} — depends on POST")

    # Summary
    total = passed + failed
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} passed, {failed}/{total} failed")
    print("=" * 60)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
