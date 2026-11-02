"""LAN Manager Profile Manager — bulk-manage Remote Connect LAN Manager profiles.

What it does:

* **Create** a Remote Connect profile and push it to many routers, or to every
  router in one or more groups.
* **Copy** one or more profiles from a source router to many routers or groups.
* **Delete** profiles from routers (by router, by group, or by profile name).
* **Disable LAN Manager** on routers or groups.
* **Orphans**: find and delete profiles whose router no longer exists.

Pushes are idempotent, so the same push can be re-run against a group after
new routers join it. A push matches existing profiles by name
(case-insensitive): an existing profile is updated in place, extra same-name
copies are deleted, and a router never ends up with duplicates. LAN Manager is
enabled automatically on every router a profile is pushed to. Deleting
profiles never disables LAN Manager; that is a separate action.

APIs:
  v2 /routers/, /groups/, /accounts/       — names, groups, accounts (read-only)
  v3 /remote_connect_profiles              — profiles (read/write)
  v3 /lan_manager_options                  — LAN Manager on/off (read/write)
v3 needs NCM_API_TOKEN, and the v3 `router` relationship ID is the v2 router ID.

Usage:
    source .venv/bin/activate && python3 -u web_apps/lan_manager_profile_manager/serve.py

Then open http://localhost:8000 in your browser.

Binds 127.0.0.1 because it writes to fleet configuration. There is no
authentication: anyone who can reach the port can read the credentials in the
Settings panel and change profiles, so do not expose it on a network.
"""

import json
import os
import ssl
import sys
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests
from fastapi import Body, FastAPI
from fastapi.requests import Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import ncm

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
import profile_logic as pl  # noqa: E402

PORT = 8000
MAX_THREADS = 8
DEFAULT_THREADS = 4

LOG_DIR = APP_DIR / "logs"
PROFILES_PATH = APP_DIR / "profiles.json"     # saved *credential* profiles
_SETTINGS_PATH = APP_DIR / "settings.json"

V3_PAGE_SIZE = 50          # both v3 endpoints reject page[size] > 50 with a 400
CONNECT_RETRIES = 3        # extra attempts on connection-level failures


# ---------------------------------------------------------------------------
# Settings (SSL verification toggle)
# ---------------------------------------------------------------------------

_ssl_verify = True


def _read_settings():
    if _SETTINGS_PATH.exists():
        try:
            return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _write_settings(settings):
    try:
        _SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except OSError:
        pass


def _load_settings():
    global _ssl_verify
    _ssl_verify = _read_settings().get("ssl_verify", True)
    if not _ssl_verify:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


_load_settings()


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

_V2_KEYS = [
    ("X_CP_API_ID", "Cradlepoint API ID"),
    ("X_CP_API_KEY", "Cradlepoint API Key"),
    ("X_ECM_API_ID", "ECM API ID"),
    ("X_ECM_API_KEY", "ECM API Key"),
]
_V3_KEY = ("NCM_API_TOKEN", "NCM API v3 token")
_ALL_KEYS = _V2_KEYS + [_V3_KEY]


def _missing_keys():
    return [k for k, _ in _ALL_KEYS if not os.environ.get(k)]


def check_env():
    """Warn and exit if any of the five credentials is not set."""
    missing = _missing_keys()
    if missing:
        print(f"WARNING: Missing environment variables: {', '.join(missing)}",
              file=sys.stderr)
        if "NCM_API_TOKEN" in missing:
            print("NCM_API_TOKEN is required: Remote Connect profiles and LAN "
                  "Manager options are v3-only endpoints.", file=sys.stderr)
        print("Use the Settings panel (gear icon) to configure credentials.",
              file=sys.stderr)
        raise SystemExit(1)


def _build_clients():
    """Create the v2 and v3 SDK clients from the current environment."""
    missing = _missing_keys()
    if missing:
        extra = (" NCM_API_TOKEN is required because Remote Connect profiles "
                 "and LAN Manager options exist only in API v3."
                 if "NCM_API_TOKEN" in missing else "")
        raise RuntimeError(
            f"Missing credentials: {', '.join(missing)}. Use the Settings "
            f"panel (gear icon) to configure them.{extra}")
    v2 = ncm.NcmClientv2(api_keys={
        "X-CP-API-ID": os.environ["X_CP_API_ID"],
        "X-CP-API-KEY": os.environ["X_CP_API_KEY"],
        "X-ECM-API-ID": os.environ["X_ECM_API_ID"],
        "X-ECM-API-KEY": os.environ["X_ECM_API_KEY"],
    }, log_events=False)
    # The v3 client's adapter retries 408/429/502/503/504 with exponential
    # backoff, and _v3_request retries the rate-limit flavour of 409.
    v3 = ncm.NcmClientv3(api_key=os.environ["NCM_API_TOKEN"], log_events=False)
    if not _ssl_verify:
        v2.session.verify = False
        v3.session.verify = False
    return v2, v3


# ---------------------------------------------------------------------------
# Saved credential profiles
# ---------------------------------------------------------------------------

def _load_profiles():
    if PROFILES_PATH.exists():
        try:
            return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_profiles(profiles):
    PROFILES_PATH.write_text(json.dumps(profiles, indent=2), encoding="utf-8")
    try:
        os.chmod(PROFILES_PATH, 0o600)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Logging — one datetime-stamped file per run
# ---------------------------------------------------------------------------

_log_lock = threading.Lock()


def create_log_file(kind):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = LOG_DIR / f"lan_manager_{kind}_{stamp}.log"
    path.touch()
    return path


def write_log(log_path, message):
    """Append a timestamped line. Lock-guarded — workers run concurrently."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    if log_path:
        try:
            with _log_lock:
                with open(log_path, "a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
        except OSError as exc:
            print(f"Log write failed: {exc}", file=sys.stderr)
    print(line, flush=True)


# ---------------------------------------------------------------------------
# v3 HTTP helpers
# ---------------------------------------------------------------------------

class ApiError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _error_detail(resp):
    try:
        body = resp.json()
    except ValueError:
        return (resp.text or "").strip()[:300] or resp.reason or ""
    errors = body.get("errors") if isinstance(body, dict) else None
    if isinstance(errors, list) and errors:
        parts = []
        for e in errors[:3]:
            if not isinstance(e, dict):
                parts.append(str(e))
                continue
            text = e.get("detail") or e.get("message") or e.get("title") or ""
            pointer = (e.get("source") or {}).get("pointer")
            parts.append(f"{text} ({pointer})" if pointer else text)
        return "; ".join(p for p in parts if p)[:400]
    return json.dumps(body)[:300]


def _v3_call(v3, verb, path, **kwargs):
    """One v3 request, with extra retries on connection-level failures.

    HTTP-level retries (429/5xx and the rate-limit 409) are already handled by
    the SDK client; this only covers drops and timeouts.
    """
    url = path if path.startswith("http") else f"{v3.base_url}{path}"
    kwargs.setdefault("timeout", 60)
    delay = 2
    for attempt in range(CONNECT_RETRIES + 1):
        try:
            return v3._v3_request(verb, url, **kwargs)
        except (requests.ConnectionError, requests.Timeout):
            if attempt >= CONNECT_RETRIES:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def _expect(resp, ok, action):
    if resp.status_code not in ok:
        raise ApiError(resp.status_code,
                       f"{action}: HTTP {resp.status_code} {_error_detail(resp)}")


def v3_get_all(v3, path, params=None):
    """Every record from a cursor-paginated v3 list. 204 = empty."""
    query = dict(params or {})
    query["page[size]"] = V3_PAGE_SIZE
    resp = _v3_call(v3, "get", path, params=query)
    results = []
    pages = 0
    while True:
        if resp.status_code == 204:
            return results
        _expect(resp, (200,), f"GET {path}")
        body = resp.json()
        data = body.get("data") or []
        results.extend(data if isinstance(data, list) else [data])
        nxt = (body.get("links") or {}).get("next")
        pages += 1
        if not nxt or pages > 5000:
            return results
        resp = _v3_call(v3, "get", nxt)


def _router_rel(router_id, account_id=None):
    rels = {"router": {"data": {"type": "routers", "id": str(router_id)}}}
    if account_id:
        rels["account"] = {"data": {"type": "accounts", "id": str(account_id)}}
    return rels


def get_router_profiles(v3, router_id):
    raw = v3_get_all(v3, "/remote_connect_profiles",
                     {"filter[router]": str(router_id)})
    return [pl.normalize_profile(p) for p in raw]


def get_router_lmo(v3, router_id):
    raw = v3_get_all(v3, "/lan_manager_options",
                     {"filter[router]": str(router_id)})
    return raw[0] if raw else None


def create_profile(v3, router_id, account_id, spec):
    body = {"data": {"type": pl.full_type(spec["type"]),
                     "attributes": pl.api_attributes(spec),
                     "relationships": _router_rel(router_id, account_id)}}
    resp = _v3_call(v3, "post", "/remote_connect_profiles", json=body)
    _expect(resp, (200, 201), "Create profile")
    try:
        return str((resp.json().get("data") or {}).get("id"))
    except ValueError:
        return None


def update_profile(v3, profile_id, router_id, account_id, spec):
    body = {"data": {"type": pl.full_type(spec["type"]), "id": str(profile_id),
                     "attributes": pl.api_attributes(spec, for_update=True),
                     "relationships": _router_rel(router_id, account_id)}}
    resp = _v3_call(v3, "put", f"/remote_connect_profiles/{profile_id}",
                    json=body)
    _expect(resp, (200,), f"Update profile {profile_id}")


def delete_profile(v3, profile_id):
    """Delete one profile. Returns False if it was already gone (404)."""
    resp = _v3_call(v3, "delete", f"/remote_connect_profiles/{profile_id}")
    if resp.status_code == 404:
        return False
    _expect(resp, (200, 202, 204), f"Delete profile {profile_id}")
    return True


def set_lan_manager(v3, router_id, account_id, enabled):
    """Make LAN Manager on/off for a router. Returns (changed, message).

    PUTs the router's existing lan_manager_options record when there is one;
    POSTs only when there is none. When disabling, a router with no record is
    left alone rather than given a new disabled one.
    """
    rec = get_router_lmo(v3, router_id)
    if rec is None and not enabled:
        return False, "No LAN Manager record — nothing to disable"
    if rec is None:
        body = {"data": {"type": "lan_manager_options",
                         "attributes": {"enabled": True},
                         "relationships": _router_rel(router_id, account_id)}}
        resp = _v3_call(v3, "post", "/lan_manager_options", json=body)
        if resp.status_code in (200, 201):
            return True, "LAN Manager enabled (new record)"
        if resp.status_code != 409:
            _expect(resp, (200, 201), "Enable LAN Manager")
        # 409 on POST: a record appeared between read and write. Re-read it.
        rec = get_router_lmo(v3, router_id)
        if rec is None:
            _expect(resp, (200, 201), "Enable LAN Manager")

    current = bool((rec.get("attributes") or {}).get("enabled"))
    if current == enabled:
        return False, f"LAN Manager already {'enabled' if enabled else 'disabled'}"
    rels = rec.get("relationships") or _router_rel(router_id, account_id)
    body = {"data": {"type": "lan_manager_options", "id": str(rec["id"]),
                     "attributes": {"enabled": enabled},
                     "relationships": rels}}
    resp = _v3_call(v3, "put", f"/lan_manager_options/{rec['id']}", json=body)
    _expect(resp, (200,), f"{'Enable' if enabled else 'Disable'} LAN Manager")
    return True, f"LAN Manager {'enabled' if enabled else 'disabled'}"


# ---------------------------------------------------------------------------
# Inventory cache
# ---------------------------------------------------------------------------

_inv = {"routers": {}, "groups": {}, "accounts": {}, "profiles": {},
        "lmo": {}, "v2_at": None, "v3_at": None}
_inv_lock = threading.Lock()


def _tail_id(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return str(int(value))
    text = str(value).rstrip("/")
    return text.split("/")[-1] or None


def _fetch_v2(v2):
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_routers = pool.submit(v2.get_routers, limit="all",
                                fields="id,name,group,account,state,device_type")
        f_accounts = pool.submit(v2.get_accounts, limit="all", fields="id,name")
        routers, accounts = f_routers.result(), f_accounts.result()
    if isinstance(routers, str) or routers is None:
        raise RuntimeError(f"Failed to read routers: {routers}")
    # Only groups that contain routers: an account can hold thousands of empty
    # groups (6,000+ took ~60s to list in testing), and an empty group has no
    # routers to push to. The SDK chunks id__in into batches of 100.
    group_ids = sorted({_tail_id(r.get("group")) for r in routers} - {None},
                       key=pl._id_sort_key)
    groups = (v2.get_groups(id__in=",".join(group_ids), limit="all",
                            fields="id,name,account") if group_ids else [])
    for label, value in (("routers", routers), ("groups", groups),
                         ("accounts", accounts)):
        if isinstance(value, str) or value is None:
            raise RuntimeError(f"Failed to read {label}: {value}")

    account_names = {str(a["id"]): a.get("name") or "" for a in accounts}
    group_rows = {}
    for g in groups:
        gid = str(g["id"])
        acct = _tail_id(g.get("account"))
        group_rows[gid] = {"id": gid, "name": g.get("name") or "",
                           "account_id": acct,
                           "account_name": account_names.get(acct, ""),
                           "device_count": 0}
    router_rows = {}
    for r in routers:
        rid = str(r["id"])
        gid = _tail_id(r.get("group"))
        acct = _tail_id(r.get("account"))
        if gid in group_rows:
            group_rows[gid]["device_count"] += 1
        router_rows[rid] = {
            "id": rid, "name": r.get("name") or "",
            "group_id": gid,
            "group_name": group_rows.get(gid, {}).get("name", "") if gid else "",
            "account_id": acct, "account_name": account_names.get(acct, ""),
            "state": r.get("state") or "",
            "device_type": r.get("device_type") or "",
        }
    return router_rows, group_rows, account_names


def _fetch_v3(v3):
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_prof = pool.submit(v3_get_all, v3, "/remote_connect_profiles")
        f_lmo = pool.submit(v3_get_all, v3, "/lan_manager_options")
        raw_profiles, raw_lmo = f_prof.result(), f_lmo.result()
    profiles = {}
    for raw in raw_profiles:
        p = pl.normalize_profile(raw)
        profiles[p["id"]] = p
    lmo = {}
    for rec in raw_lmo:
        rid = (((rec.get("relationships") or {}).get("router") or {})
               .get("data") or {}).get("id")
        if rid is not None:
            lmo[str(rid)] = {"id": str(rec["id"]), "enabled": bool(
                (rec.get("attributes") or {}).get("enabled"))}
    return profiles, lmo


def refresh_inventory(part="all"):
    """Re-read v2 inventory and/or v3 profile data. part: all | v3."""
    v2, v3 = _build_clients()
    if part == "all":
        with ThreadPoolExecutor(max_workers=2) as pool:
            f2 = pool.submit(_fetch_v2, v2)
            f3 = pool.submit(_fetch_v3, v3)
            routers, groups, accounts = f2.result()
            profiles, lmo = f3.result()
        with _inv_lock:
            _inv.update(routers=routers, groups=groups, accounts=accounts,
                        profiles=profiles, lmo=lmo, v2_at=_now_iso(),
                        v3_at=_now_iso())
    else:
        profiles, lmo = _fetch_v3(v3)
        with _inv_lock:
            _inv.update(profiles=profiles, lmo=lmo, v3_at=_now_iso())


def _ensure_inventory():
    with _inv_lock:
        have = bool(_inv["v2_at"] and _inv["v3_at"])
    if not have:
        refresh_inventory("all")


def _clear_inventory():
    with _inv_lock:
        _inv.update(routers={}, groups={}, accounts={}, profiles={}, lmo={},
                    v2_at=None, v3_at=None)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _snapshot():
    with _inv_lock:
        return {k: (dict(v) if isinstance(v, dict) else v)
                for k, v in _inv.items()}


def _router_view(inv, rid):
    """Router row for display; placeholder for routers missing from v2."""
    r = inv["routers"].get(rid)
    if r:
        return dict(r, orphan=False)
    acct = None
    for p in inv["profiles"].values():
        if p["router_id"] == rid:
            acct = p["account_id"]
            break
    return {"id": rid, "name": "", "group_id": None, "group_name": "",
            "account_id": acct,
            "account_name": inv["accounts"].get(acct, "") if acct else "",
            "state": "", "device_type": "", "orphan": True}


def _profiles_by_router(inv):
    out = {}
    for p in inv["profiles"].values():
        out.setdefault(p["router_id"], []).append(p)
    return out


def _profile_view(inv, p):
    r = _router_view(inv, p["router_id"])
    return dict(p, router_name=r["name"], group_id=r["group_id"],
                group_name=r["group_name"],
                account_name=r["account_name"], orphan=r["orphan"],
                summary=pl.describe_settings(p["type"], p["settings"]))


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------

def resolve_router_ids(inv, target):
    """Expand a destination selection into router IDs.

    target = {"mode": "routers"|"groups"|"profiles", "ids": [...]}
    In "profiles" mode the ids are profile IDs (from the profile-name variant
    picker or the orphan list) and resolve to the routers carrying them.
    """
    mode = target.get("mode")
    ids = [str(i) for i in (target.get("ids") or [])]
    if mode == "groups":
        wanted = set(ids)
        return sorted((rid for rid, r in inv["routers"].items()
                       if r["group_id"] in wanted), key=pl._id_sort_key)
    if mode == "profiles":
        rids = {inv["profiles"][pid]["router_id"] for pid in ids
                if pid in inv["profiles"]}
        return sorted(rids, key=pl._id_sort_key)
    return sorted(set(ids), key=pl._id_sort_key)


# ---------------------------------------------------------------------------
# Jobs — one at a time
# ---------------------------------------------------------------------------

_job = {"state": "idle"}
_job_lock = threading.Lock()


def _job_busy():
    with _job_lock:
        return _job.get("state") in ("preparing", "running", "refreshing")


def _set_row(router_id, **fields):
    with _job_lock:
        for row in _job.get("rows", []):
            if row["router_id"] == router_id:
                row.update(fields)
                return


def _tally(outcome):
    with _job_lock:
        _job["processed"] += 1
        _job[outcome] = _job.get(outcome, 0) + 1


def _cancel_requested():
    with _job_lock:
        return bool(_job.get("cancel"))


def _start_job(kind, label, inv, router_ids, worker, threads, header_lines):
    """Initialise the shared job record and run ``worker(row)`` per router."""
    log_path = create_log_file(kind)
    rows = []
    for rid in router_ids:
        r = _router_view(inv, rid)
        rows.append({"router_id": rid, "router_name": r["name"],
                     "group_name": r["group_name"],
                     "account_id": r["account_id"],
                     "account_name": r["account_name"], "orphan": r["orphan"],
                     "status": "pending", "message": ""})
    with _job_lock:
        _job.clear()
        _job.update({
            "id": uuid.uuid4().hex[:12], "kind": kind, "label": label,
            "state": "running", "threads": threads, "total": len(rows),
            "processed": 0, "changed": 0, "unchanged": 0, "failed": 0,
            "canceled": 0, "cancel": False, "error": None,
            "started_at": time.time(), "finished_at": None,
            "log_name": log_path.name, "rows": rows,
        })

    def run():
        try:
            write_log(log_path, "=" * 72)
            write_log(log_path, f"LAN Manager Profile Manager — {label}")
            for line in header_lines:
                write_log(log_path, line)
            write_log(log_path, f"Target routers: {len(rows)} | threads: {threads}")
            write_log(log_path, "=" * 72)

            def work(row):
                label_r = (f"{row['router_name'] or '(router not in v2)'} "
                           f"[{row['router_id']}]")
                if _cancel_requested():
                    _set_row(row["router_id"], status="canceled",
                             message="Canceled before start")
                    _tally("canceled")
                    return
                _set_row(row["router_id"], status="running", message="Working…")
                try:
                    outcome, message = worker(row, label_r, log_path)
                except Exception as exc:  # noqa: BLE001 — never lose a worker
                    outcome, message = "failed", f"{type(exc).__name__}: {exc}"
                    write_log(log_path, f"FAILED {label_r}: {message}")
                _set_row(row["router_id"], status=outcome, message=message)
                _tally(outcome)

            if threads <= 1:
                for row in list(rows):
                    work(row)
            else:
                with ThreadPoolExecutor(max_workers=threads,
                                        thread_name_prefix="lmpm") as pool:
                    list(pool.map(work, list(rows)))

            with _job_lock:
                canceled = bool(_job.get("cancel"))
                counts = {k: _job[k] for k in
                          ("changed", "unchanged", "failed", "canceled", "total")}
                _job["state"] = "refreshing"
            write_log(log_path, "-" * 72)
            write_log(log_path,
                      f"Run {'CANCELED' if canceled else 'complete'}: "
                      f"{counts['changed']} changed, {counts['unchanged']} "
                      f"unchanged, {counts['failed']} failed, "
                      f"{counts['canceled']} canceled, of {counts['total']}.")
            try:
                refresh_inventory("v3")
                write_log(log_path, "Profile inventory re-read after run.")
            except Exception as exc:  # noqa: BLE001
                write_log(log_path, f"WARNING could not re-read inventory: {exc}")
            write_log(log_path, "=" * 72)
            with _job_lock:
                _job["state"] = "canceled" if canceled else "done"
                _job["finished_at"] = time.time()
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            write_log(log_path, f"ERROR run aborted: {type(exc).__name__}: {exc}")
            with _job_lock:
                _job["state"] = "error"
                _job["error"] = str(exc)
                _job["finished_at"] = time.time()

    threading.Thread(target=run, daemon=True).start()
    with _job_lock:
        return {"job_id": _job["id"], "total": len(rows),
                "log_name": log_path.name, "threads": threads}


def _attrs_json(p):
    return json.dumps({"type": p["type"], **p["settings"]}, sort_keys=True)


def _push_worker(v3, specs):
    """Per-router body for create/copy pushes."""

    def worker(row, label, log_path):
        rid, acct = row["router_id"], row["account_id"]
        if row["orphan"]:
            write_log(log_path, f"SKIPPED {label}: router not found in v2")
            return "unchanged", "Skipped — router not found in v2"

        notes = []
        changed_any = False

        lm_changed, lm_msg = set_lan_manager(v3, rid, acct, True)
        changed_any |= lm_changed
        if lm_changed:
            notes.append(lm_msg)
        write_log(log_path, f"{label}: {lm_msg}")

        existing = get_router_profiles(v3, rid)
        for spec in specs:
            if _cancel_requested():
                notes.append("canceled mid-router")
                break
            name = spec["settings"]["name"]
            plan = pl.plan_push(spec, existing)
            for act in plan["actions"]:
                if act[0] == "create":
                    new_id = create_profile(v3, rid, acct, spec)
                    write_log(log_path, f"{label}: created '{name}' (id {new_id}) "
                                        f"{json.dumps(spec['settings'], sort_keys=True)}")
                elif act[0] == "update":
                    old = next(p for p in existing if p["id"] == act[1])
                    update_profile(v3, act[1], rid, acct, spec)
                    write_log(log_path, f"{label}: updated '{name}' (id {act[1]}). "
                                        f"Previous: {_attrs_json(old)}")
                elif act[0] == "delete":
                    old = next(p for p in existing if p["id"] == act[1])
                    gone = delete_profile(v3, act[1])
                    write_log(log_path,
                              f"{label}: deleted duplicate/replaced '{old['name']}' "
                              f"(id {act[1]}){'' if gone else ' — already gone'}. "
                              f"Was: {_attrs_json(old)}")
            if plan["actions"]:
                changed_any = True
            notes.append({
                "create": f"'{name}' created",
                "unchanged": f"'{name}' already correct",
                "update": f"'{name}' updated",
                "dedupe": f"'{name}' duplicates removed",
                "replace": f"'{name}' replaced (type changed)",
            }[plan["outcome"]] + (
                f" (+{sum(1 for a in plan['actions'] if a[0] == 'delete')} "
                f"duplicate(s) removed)"
                if plan["outcome"] == "update"
                and any(a[0] == "delete" for a in plan["actions"]) else ""))
            if plan["actions"]:
                existing = get_router_profiles(v3, rid)

        # Verify from a fresh read rather than trusting status codes.
        final = get_router_profiles(v3, rid)
        bad = [s["settings"]["name"] for s in specs if not pl.verify_push(s, final)]
        if bad:
            msg = "Verify failed for: " + ", ".join(bad) + " | " + "; ".join(notes)
            write_log(log_path, f"FAILED {label}: {msg}")
            return "failed", msg
        msg = "; ".join(notes)
        write_log(log_path, f"{'SUCCESS' if changed_any else 'UNCHANGED'} "
                            f"{label}: {msg}")
        return ("changed" if changed_any else "unchanged"), msg

    return worker


def _delete_by_ids_worker(v3, inv, ids_by_router):
    def worker(row, label, log_path):
        ids = ids_by_router.get(row["router_id"], [])
        deleted, gone = 0, 0
        for pid in ids:
            if _cancel_requested():
                break
            p = inv["profiles"].get(pid)
            if delete_profile(v3, pid):
                deleted += 1
                write_log(log_path, f"{label}: deleted '{p['name'] if p else pid}' "
                                    f"(id {pid}). Was: {_attrs_json(p) if p else '?'}")
            else:
                gone += 1
                write_log(log_path, f"{label}: profile {pid} already gone")
        msg = f"{deleted} deleted" + (f", {gone} already gone" if gone else "")
        return ("changed" if deleted else "unchanged"), msg
    return worker


def _delete_by_name_worker(v3, keys, delete_all):
    def worker(row, label, log_path):
        existing = get_router_profiles(v3, row["router_id"])
        doomed = [p for p in existing if delete_all or p["name_key"] in keys]
        if not doomed:
            write_log(log_path, f"UNCHANGED {label}: no matching profiles")
            return "unchanged", "No matching profiles"
        deleted = 0
        for p in doomed:
            if _cancel_requested():
                break
            if delete_profile(v3, p["id"]):
                deleted += 1
            write_log(log_path, f"{label}: deleted '{p['name']}' (id {p['id']}). "
                                f"Was: {_attrs_json(p)}")
        left = [p for p in get_router_profiles(v3, row["router_id"])
                if delete_all or p["name_key"] in keys]
        if left:
            msg = f"{deleted} deleted, but {len(left)} still present on re-read"
            write_log(log_path, f"FAILED {label}: {msg}")
            return "failed", msg
        msg = f"{deleted} deleted: " + ", ".join(sorted({p['name'] for p in doomed}))
        write_log(log_path, f"SUCCESS {label}: {msg}")
        return "changed", msg
    return worker


def _disable_worker(v3):
    def worker(row, label, log_path):
        changed, msg = set_lan_manager(v3, row["router_id"], row["account_id"],
                                       False)
        write_log(log_path, f"{'SUCCESS' if changed else 'UNCHANGED'} {label}: {msg}")
        return ("changed" if changed else "unchanged"), msg
    return worker


# ---------------------------------------------------------------------------
# Previews (read-only, from the cached inventory)
# ---------------------------------------------------------------------------

def _parse_specs(body):
    """Specs from a request: {"specs": [form...]} or {"source_profile_ids": []}."""
    inv = _snapshot()
    specs = []
    if body.get("source_profile_ids"):
        for pid in body["source_profile_ids"]:
            p = inv["profiles"].get(str(pid))
            if not p:
                raise ValueError(f"Source profile {pid} not found — refresh and retry")
            specs.append(pl.spec_from_profile(p))
    else:
        specs = [pl.spec_from_form(f) for f in (body.get("specs") or [])]
    if not specs:
        raise ValueError("No profile to push")
    copying = bool(body.get("source_profile_ids"))
    problems = []
    for s in specs:
        for problem in pl.validate_spec(s):
            if (copying and s["type"] == "ssh"
                    and problem.startswith("Username is required")):
                # NCM can hold SSH profiles with no username (not created via
                # the v3 API), but the API rejects them on POST and PUT.
                problem = ("this SSH profile has no username. The NCM API "
                           "requires one for SSH, so it can't be copied as-is "
                           "(it was likely created outside the API, e.g. in "
                           "the NCM UI). Use Create profile with a username "
                           "instead")
            problems.append(f"{s['settings'].get('name') or '(unnamed)'}: {problem}")
    keys = [pl.name_key(s["settings"]["name"]) for s in specs]
    if len(keys) != len(set(keys)):
        problems.append("Two selected profiles share a name (ignoring case); "
                        "a router can only end up with one of them")
    if problems:
        raise ValueError("; ".join(problems))
    return specs


def preview_push(body):
    inv = _snapshot()
    specs = _parse_specs(body)
    exclude = {str(body.get("source_router_id"))} if body.get("source_router_id") else set()
    rids = [r for r in resolve_router_ids(inv, body.get("target") or {})
            if r not in exclude]
    by_router = _profiles_by_router(inv)
    rows, totals = [], {"create": 0, "update": 0, "unchanged": 0, "dedupe": 0,
                        "replace": 0, "lm_enable": 0, "skipped": 0}
    for rid in rids:
        r = _router_view(inv, rid)
        if r["orphan"]:
            totals["skipped"] += 1
            rows.append(dict(r, lm="", outcomes=[], note="Router not found in v2 — skipped"))
            continue
        lm = inv["lmo"].get(rid)
        lm_state = "enabled" if lm and lm["enabled"] else ("disabled" if lm else "none")
        if lm_state != "enabled":
            totals["lm_enable"] += 1
        outcomes = []
        for s in specs:
            plan = pl.plan_push(s, by_router.get(rid, []))
            totals[plan["outcome"]] += 1
            outcomes.append({"name": s["settings"]["name"],
                             "outcome": plan["outcome"],
                             "deletes": sum(1 for a in plan["actions"]
                                            if a[0] == "delete")})
        rows.append(dict(r, lm=lm_state, outcomes=outcomes, note=""))
    return {"rows": rows, "totals": totals, "excluded_source": bool(exclude),
            "specs": [dict(s, summary=pl.describe_settings(s["type"], s["settings"]))
                      for s in specs]}


def preview_delete(body):
    """What a delete would remove, from the cache. Returns rows + plan."""
    inv = _snapshot()
    target = body.get("target") or {}
    by_router = _profiles_by_router(inv)
    if target.get("mode") == "profiles":
        ids = [str(i) for i in target.get("ids") or [] if str(i) in inv["profiles"]]
        plan = {}
        for pid in ids:
            plan.setdefault(inv["profiles"][pid]["router_id"], []).append(pid)
    else:
        keys = {pl.name_key(n) for n in body.get("names") or []}
        delete_all = bool(body.get("all_profiles"))
        if not keys and not delete_all:
            raise ValueError("Pick at least one profile name to delete")
        plan = {}
        for rid in resolve_router_ids(inv, target):
            hits = [p["id"] for p in by_router.get(rid, [])
                    if delete_all or p["name_key"] in keys]
            if hits:
                plan[rid] = hits
    rows = []
    for rid, pids in sorted(plan.items(), key=lambda kv: pl._id_sort_key(kv[0])):
        r = _router_view(inv, rid)
        rows.append(dict(r, profiles=[_profile_view(inv, inv["profiles"][p])
                                      for p in pids]))
    return {"rows": rows, "routers": len(rows),
            "profiles": sum(len(v) for v in plan.values()), "plan": plan}


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="LAN Manager Profile Manager")

STATIC_DIR = APP_DIR / "static"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _ssl_error(exc):
    seen = exc
    while seen:
        if isinstance(seen, ssl.SSLCertVerificationError) or \
                "CERTIFICATE_VERIFY_FAILED" in str(seen):
            return True
        seen = seen.__cause__ or seen.__context__
    return False


def _error_response(exc, status=500):
    if isinstance(exc, ValueError):
        return JSONResponse({"status": "error", "message": str(exc)},
                            status_code=400)
    traceback.print_exc()
    if _ssl_error(exc):
        return JSONResponse(
            {"status": "error", "error_type": "ssl_error",
             "message": "SSL certificate verification failed. This often "
                        "happens behind a corporate proxy. You can disable "
                        "SSL verification for this install."},
            status_code=502)
    return JSONResponse({"status": "error", "message": str(exc)},
                        status_code=status)


def _threads(body):
    try:
        t = int(body.get("threads", DEFAULT_THREADS) or DEFAULT_THREADS)
    except (TypeError, ValueError):
        t = DEFAULT_THREADS
    return max(1, min(t, MAX_THREADS))


def _busy_response():
    return JSONResponse({"status": "error",
                         "message": "A run is already in progress"},
                        status_code=409)


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((APP_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/config")
async def runtime_config():
    return JSONResponse({
        "status": "ok", "port": PORT, "max_threads": MAX_THREADS,
        "default_threads": DEFAULT_THREADS,
        "missing_credentials": _missing_keys(),
        "types": [{"id": t, "label": pl.TYPE_LABELS[t],
                   "fields": pl.TYPE_FIELDS[t],
                   "required": pl.REQUIRED_FIELDS[t],
                   "default_port": pl.DEFAULT_PORTS[t]} for t in pl.TYPE_FIELDS],
        "name_max": pl.NAME_MAX, "username_max": pl.USERNAME_MAX,
    })


@app.get("/api/inventory")
def inventory(refresh: str = ""):
    """Routers, groups and every profile. refresh = all | v3 | (empty)."""
    try:
        if refresh in ("all", "true", "1"):
            refresh_inventory("all")
        elif refresh == "v3":
            refresh_inventory("v3")
        else:
            _ensure_inventory()
        inv = _snapshot()
        by_router = _profiles_by_router(inv)
        routers = []
        for rid, r in inv["routers"].items():
            lm = inv["lmo"].get(rid)
            routers.append(dict(
                r, profile_count=len(by_router.get(rid, [])),
                lan_manager=("enabled" if lm and lm["enabled"]
                             else "disabled" if lm else "none")))
        profiles = [_profile_view(inv, p) for p in inv["profiles"].values()]
        resolutions = sorted({p["settings"].get("resolution")
                              for p in inv["profiles"].values()
                              if p["settings"].get("resolution")})
        return JSONResponse({
            "status": "ok", "v2_at": inv["v2_at"], "v3_at": inv["v3_at"],
            "routers": routers, "groups": list(inv["groups"].values()),
            "profiles": profiles, "resolutions": resolutions,
            "orphan_profiles": sum(1 for p in profiles if p["orphan"]),
        })
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)


@app.get("/api/routers/{router_id}/profiles")
def router_profiles(router_id: str):
    """Live read of one router's profiles (copy source)."""
    try:
        _, v3 = _build_clients()
        inv = _snapshot()
        profiles = get_router_profiles(v3, router_id)
        with _inv_lock:  # keep the cache in step with what we just read
            for pid in [k for k, p in _inv["profiles"].items()
                        if p["router_id"] == str(router_id)]:
                del _inv["profiles"][pid]
            for p in profiles:
                _inv["profiles"][p["id"]] = p
        return JSONResponse({"status": "ok",
                             "profiles": [_profile_view(inv, p) for p in profiles]})
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)


@app.post("/api/variants")
def variants(body: dict = Body(...)):
    """Profiles whose name matches (case-insensitive), grouped by variant."""
    key = pl.name_key(body.get("name"))
    if not key:
        return JSONResponse({"status": "error", "message": "Name required"},
                            status_code=400)
    try:
        _ensure_inventory()
        inv = _snapshot()
        matches = [p for p in inv["profiles"].values() if p["name_key"] == key]
        out = []
        for v in pl.group_variants(matches):
            rows = sorted((_profile_view(inv, p) for p in v["profiles"]),
                          key=lambda x: ((x["router_name"] or "~").lower(),
                                         pl._id_sort_key(x["router_id"])))
            out.append({"fingerprint": v["fingerprint"], "type": v["type"],
                        "settings": v["settings"], "summary": v["summary"],
                        "profiles": rows,
                        "router_count": len({r["router_id"] for r in rows})})
        return JSONResponse({"status": "ok", "name_key": key, "variants": out,
                             "total": len(matches)})
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)


@app.post("/api/preview/push")
def api_preview_push(body: dict = Body(...)):
    try:
        _ensure_inventory()
        return JSONResponse(dict(preview_push(body), status="ok"))
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)


@app.post("/api/preview/delete")
def api_preview_delete(body: dict = Body(...)):
    try:
        _ensure_inventory()
        result = preview_delete(body)
        result.pop("plan", None)
        return JSONResponse(dict(result, status="ok"))
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)


@app.post("/api/jobs/push")
def job_push(body: dict = Body(...)):
    """Create/copy: push one or more profiles to the target routers."""
    if _job_busy():
        return _busy_response()
    try:
        _ensure_inventory()
        inv = _snapshot()
        specs = _parse_specs(body)
        exclude = {str(body.get("source_router_id"))} if body.get("source_router_id") else set()
        rids = [r for r in resolve_router_ids(inv, body.get("target") or {})
                if r not in exclude]
        if not rids:
            raise ValueError("The destination resolved to no routers")
        _, v3 = _build_clients()
        kind = "copy" if body.get("source_profile_ids") else "create"
        header = [f"Action: {kind} — push {len(specs)} profile(s); enable LAN "
                  f"Manager where needed; replace same-name profiles "
                  f"(case-insensitive), never duplicate"]
        if body.get("source_router_id"):
            src = _router_view(inv, str(body["source_router_id"]))
            header.append(f"Source router: {src['name']} [{src['id']}]")
        for s in specs:
            header.append(f"Profile: '{s['settings']['name']}' "
                          f"{pl.describe_settings(s['type'], s['settings'])}")
        result = _start_job(kind, f"{kind.capitalize()} {len(specs)} profile(s)",
                            inv, rids, _push_worker(v3, specs), _threads(body),
                            header)
        return JSONResponse(dict(result, status="ok"))
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)


@app.post("/api/jobs/delete")
def job_delete(body: dict = Body(...)):
    """Delete profiles. Never touches LAN Manager."""
    if _job_busy():
        return _busy_response()
    try:
        _ensure_inventory()
        inv = _snapshot()
        target = body.get("target") or {}
        _, v3 = _build_clients()
        if target.get("mode") == "profiles":
            plan = preview_delete(body)["plan"]
            if not plan:
                raise ValueError("No profiles selected")
            worker = _delete_by_ids_worker(v3, inv, plan)
            rids = list(plan)
            header = [f"Action: delete {sum(len(v) for v in plan.values())} "
                      f"selected profile(s) by ID"
                      + (" (orphans)" if body.get("orphans") else "")]
        else:
            keys = {pl.name_key(n) for n in body.get("names") or []}
            delete_all = bool(body.get("all_profiles"))
            if not keys and not delete_all:
                raise ValueError("Pick at least one profile name to delete")
            rids = resolve_router_ids(inv, target)
            if not rids:
                raise ValueError("The selection resolved to no routers")
            worker = _delete_by_name_worker(v3, keys, delete_all)
            header = ["Action: delete " + ("ALL profiles" if delete_all else
                      "profiles named (case-insensitive): "
                      + ", ".join(sorted(keys)))
                      + " — re-read live per router"]
        header.append("LAN Manager is NOT changed by deletes.")
        label = "Delete orphaned profiles" if body.get("orphans") else "Delete profiles"
        result = _start_job("delete", label, inv, rids, worker, _threads(body),
                            header)
        return JSONResponse(dict(result, status="ok"))
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)


@app.post("/api/jobs/lan-disable")
def job_lan_disable(body: dict = Body(...)):
    if _job_busy():
        return _busy_response()
    try:
        _ensure_inventory()
        inv = _snapshot()
        rids = resolve_router_ids(inv, body.get("target") or {})
        if not rids:
            raise ValueError("The selection resolved to no routers")
        _, v3 = _build_clients()
        result = _start_job("lan_disable", "Disable LAN Manager", inv, rids,
                            _disable_worker(v3), _threads(body),
                            ["Action: set lan_manager_options enabled=false. "
                             "Profiles are not deleted."])
        return JSONResponse(dict(result, status="ok"))
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)


@app.get("/api/jobs/status")
async def job_status():
    with _job_lock:
        if _job.get("state") in (None, "idle"):
            return JSONResponse({"status": "ok", "state": "idle"})
        snap = {k: v for k, v in _job.items() if k != "rows"}
        snap["rows"] = [dict(r) for r in _job.get("rows", [])]
    snap["status"] = "ok"
    return JSONResponse(snap)


@app.post("/api/jobs/cancel")
async def job_cancel():
    with _job_lock:
        if _job.get("state") not in ("running",):
            return JSONResponse({"status": "ok", "state": _job.get("state", "idle")})
        _job["cancel"] = True
        log_name = _job.get("log_name")
    write_log(LOG_DIR / log_name if log_name else None,
              "CANCEL requested — no further routers will be started")
    return JSONResponse({"status": "ok", "canceling": True})


@app.get("/api/logs")
async def list_logs():
    if not LOG_DIR.is_dir():
        return JSONResponse({"status": "ok", "logs": []})
    entries = [{"name": p.name, "size": p.stat().st_size,
                "modified": p.stat().st_mtime}
               for p in LOG_DIR.glob("lan_manager_*.log")]
    entries.sort(key=lambda e: e["modified"], reverse=True)
    return JSONResponse({"status": "ok", "logs": entries[:50]})


@app.get("/api/log")
async def get_log(name: str = ""):
    """Download a run log. Confined to this app's logs directory."""
    filename = os.path.basename(name or "")
    path = (LOG_DIR / filename).resolve() if filename else None
    if not path or LOG_DIR.resolve() not in path.parents or not path.is_file():
        return JSONResponse({"status": "error", "message": "Log not found"},
                            status_code=404)
    return FileResponse(str(path), media_type="text/plain", filename=filename)


@app.post("/api/ssl-noverify")
async def disable_ssl_verify():
    global _ssl_verify
    _ssl_verify = False
    settings = _read_settings()
    settings["ssl_verify"] = False
    _write_settings(settings)
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return JSONResponse({"status": "ok", "ssl_verify": False})


# --- Saved credential profiles ---

@app.get("/api/profiles")
async def list_cred_profiles():
    profiles = _load_profiles()
    return JSONResponse({
        name: {k: (v[:4] + "…" if v and len(v) > 4 else "")
               for k, v in creds.items()}
        for name, creds in profiles.items()})


@app.post("/api/profiles")
async def save_cred_profile(request: Request):
    body = await request.json()
    name = (body.get("name") or "").strip()
    creds = body.get("credentials", {})
    if not name:
        return JSONResponse({"error": "Profile name required"}, status_code=400)
    profiles = _load_profiles()
    if name in profiles and not body.get("overwrite"):
        return JSONResponse({"error": "exists",
                             "message": f"Profile '{name}' already exists"},
                            status_code=409)
    profiles[name] = {k: creds.get(k, "") for k, _ in _ALL_KEYS}
    _save_profiles(profiles)
    return JSONResponse({"status": "ok", "name": name})


@app.post("/api/profiles/load")
async def load_cred_profile(request: Request):
    body = await request.json()
    name = (body.get("name") or "").strip()
    profiles = _load_profiles()
    if name not in profiles:
        return JSONResponse({"error": f"Profile '{name}' not found"},
                            status_code=404)
    for key, val in profiles[name].items():
        if val:
            os.environ[key] = val
    _clear_inventory()
    return JSONResponse({"status": "ok", "name": name})


@app.delete("/api/profiles/{name}")
async def delete_cred_profile(name: str):
    profiles = _load_profiles()
    if name not in profiles:
        return JSONResponse({"error": f"Profile '{name}' not found"},
                            status_code=404)
    del profiles[name]
    _save_profiles(profiles)
    return JSONResponse({"status": "ok", "deleted": name})


@app.get("/api/profiles/current")
async def current_credentials():
    return JSONResponse({k: {"set": bool(os.environ.get(k, "")),
                             "value": os.environ.get(k, "")}
                         for k, _ in _ALL_KEYS})


@app.post("/api/credentials/apply")
async def apply_credentials(request: Request):
    body = await request.json()
    creds = body.get("credentials", {})
    for key, _ in _ALL_KEYS:
        val = (creds.get(key) or "").strip()
        if val:
            os.environ[key] = val
    _clear_inventory()
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    try:
        check_env()
    except SystemExit:
        print("WARNING: API credentials not set. Use the Settings panel "
              "(gear icon) to configure them.")
    print("LAN Manager Profile Manager starting…")
    print(f"Open http://localhost:{PORT} in your browser")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info")
