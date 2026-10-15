"""
NCOS Downloader — browse and download NCOS firmware images from the NCM API.

Firmware metadata comes from the v2 ``/firmwares/`` endpoint; the actual ``.bin``
images live on Cradlepoint's CDN, referenced by the ``url`` field on each
firmware record. Each record also carries a ``hash`` (SHA-1 of the image), which
this app uses to verify every download.

Usage:
    source .venv/bin/activate && python3 web_apps/ncos_downloader/serve.py

Then open http://localhost:8075 in your browser.
"""

import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

def _load_dotenv():
    """Load a .env from the app folder first, then the repo root if present.

    The app folder comes first so a standalone copy (unzipped anywhere) works
    without the surrounding repo. Real environment variables always win.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    here = Path(__file__).resolve()
    for candidate in (here.parent / ".env", *[p / ".env" for p in here.parents[1:3]]):
        if candidate.is_file():
            load_dotenv(candidate, override=False)


_load_dotenv()

import requests
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.requests import Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

APP_DIR = Path(__file__).resolve().parent
PORT = 8075

# NCM v2 firmware metadata. Trailing slash is required on all v2 URLs.
FIRMWARES_URL = "https://www.cradlepointecm.com/api/v2/firmwares/"
PRODUCTS_URL = "https://www.cradlepointecm.com/api/v2/products/"
# CDN that actually serves the .bin images (paths come from firmware['url'])
FIRMWARE_CDN = "https://d251cfg5d9gyuq.cloudfront.net"

PAGE_LIMIT = 500          # max the v2 API allows
CATALOG_WORKERS = 10      # parallel pages per round when building the catalog
RETRY_STATUS = {408, 429, 503, 504}

CATALOG_PATH = APP_DIR / "catalog_cache.json"
SETTINGS_PATH = APP_DIR / "settings.json"
PROFILES_PATH = APP_DIR / "profiles.json"

DEFAULT_SETTINGS = {
    "download_dir": str(APP_DIR / "downloads"),
    "concurrency": 3,
    "verify_sha1": True,
}


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------

_settings = dict(DEFAULT_SETTINGS)


def _load_settings():
    global _settings
    merged = dict(DEFAULT_SETTINGS)
    if SETTINGS_PATH.exists():
        try:
            merged.update(json.loads(SETTINGS_PATH.read_text(encoding="utf-8")) or {})
        except (json.JSONDecodeError, OSError):
            pass
    _settings = merged


def _save_settings():
    try:
        SETTINGS_PATH.write_text(json.dumps(_settings, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"[settings] could not save: {exc}", file=sys.stderr)


def download_dir() -> Path:
    path = Path(_settings.get("download_dir") or DEFAULT_SETTINGS["download_dir"]).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


_load_settings()


# --------------------------------------------------------------------------
# Credentials
# --------------------------------------------------------------------------

CRED_KEYS = ["X_CP_API_ID", "X_CP_API_KEY", "X_ECM_API_ID", "X_ECM_API_KEY"]


def auth_headers():
    """Build NCM v2 auth headers from the environment.

    Returns None when any of the four required keys is missing, so callers can
    surface a "configure credentials" message instead of a raw 401.
    """
    values = {key: os.environ.get(key, "").strip() for key in CRED_KEYS}
    if not all(values.values()):
        return None
    return {
        "X-CP-API-ID": values["X_CP_API_ID"],
        "X-CP-API-KEY": values["X_CP_API_KEY"],
        "X-ECM-API-ID": values["X_ECM_API_ID"],
        "X-ECM-API-KEY": values["X_ECM_API_KEY"],
    }


def _setup_script():
    """Locate the repo's setup_env.py, if this copy is running inside the repo."""
    for parent in Path(__file__).resolve().parents[1:4]:
        if (parent / "setup_env.py").is_file():
            return parent / "setup_env.py"
    return None


def _creds_message():
    """Tell the user how to set credentials, matching how this copy is deployed."""
    message = "API credentials are not configured. Enter them in Settings (gear icon)."
    if _setup_script():
        message += " Inside the repo you can also run: python3 setup_env.py --credentials-only"
    return message


def _no_creds_response():
    return JSONResponse(
        {
            "status": "error",
            "error_type": "no_credentials",
            "message": _creds_message(),
        },
        status_code=400,
    )


# --------------------------------------------------------------------------
# HTTP helper with retry/backoff
# --------------------------------------------------------------------------

def _get_with_retry(session, url, *, params=None, stream=False, timeout=60, attempts=4):
    """GET with exponential backoff on transient errors (408/429/503/504)."""
    delay = 1.0
    last_exc = None
    for attempt in range(attempts):
        try:
            resp = session.get(url, params=params, stream=stream, timeout=timeout)
            if resp.status_code in RETRY_STATUS and attempt < attempts - 1:
                resp.close()
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= attempts - 1:
                raise
            time.sleep(delay)
            delay *= 2
    raise last_exc  # pragma: no cover - loop always returns or raises


# --------------------------------------------------------------------------
# Catalog
# --------------------------------------------------------------------------

_catalog = {"built_at": None, "firmwares": [], "models": [], "versions": []}
_catalog_state = {"state": "idle", "phase": "", "rows": 0, "pages": 0, "error": None}
_catalog_lock = threading.Lock()

_MODEL_FROM_URL = re.compile(r"^/([^/]+?)-\d{4}-\d{2}-\d{2}T", re.IGNORECASE)


def _model_from_url(url: str) -> str:
    """Fall back to parsing the model out of the CDN path.

    Paths look like ``/IBR600C-2024-02-29T18%3A16%3A00.bin``, so everything
    before the build timestamp is the model name.
    """
    match = _MODEL_FROM_URL.match(url or "")
    model = match.group(1).upper() if match else ""
    # Strip a variant tag so the model name stays clean (see image_variant).
    return model.replace("-MULTIIMAGE", "")


def image_variant(url: str) -> str:
    """Return the image variant tag encoded in the CDN filename, or "".

    The only field distinguishing some otherwise-identical firmware records is
    a tag inside the ``url`` filename. ``multiimage`` is the one that occurs in
    practice (1,955 of 17,677 records), and it is why the same model, version,
    and build timestamp routinely appears twice: once as a standard image and
    once as a multiimage build.
    """
    return "multiimage" if "-multiimage-" in unquote(url or "").lower() else ""


def image_extension(url: str) -> str:
    """Extension of the actual image file, taken from the URL.

    Not always ``.bin`` — CR4250 firmware ships as ``.vmp`` (450 records). The
    extension has to come from the URL rather than being assumed, or files land
    on disk with a name that misrepresents their format.
    """
    name = unquote(url or "").split("?")[0].rstrip("/").rsplit("/", 1)[-1]
    suffix = Path(name).suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{2,5}", suffix) else ".bin"


def image_download_url(url: str) -> str:
    """Absolute URL for a firmware image.

    ``url`` is normally a path to prepend the CDN base to, but 41 records carry
    a fully-qualified URL instead — 22 of them on a *different* CloudFront host
    than the usual base. Prepending the base to those produces a doubled,
    unusable URL, so pass them through untouched.
    """
    url = (url or "").strip()
    if url.lower().startswith(("http://", "https://")):
        return url
    return FIRMWARE_CDN + url


def is_downloadable(url: str) -> bool:
    """Whether a firmware `url` is a form we can fetch."""
    url = (url or "").strip()
    return url.startswith("/") or url.lower().startswith(("http://", "https://"))


def _product_id(url: str):
    """Pull the numeric id out of a v2 resource URL like .../products/63/."""
    if not url:
        return None
    parts = str(url).rstrip("/").split("/")
    return parts[-1] if parts and parts[-1].isdigit() else None


def assign_filenames(rows):
    """Give every row a filename that is unique per distinct build.

    Naming is layered so the common case stays clean:

    1. ``MODEL-VERSION.ext`` when that is already unique.
    2. ``MODEL-VERSION-multiimage.ext`` for multiimage builds, which is what
       most collisions actually are — a standard and a multiimage image sharing
       one model, version, and build timestamp (2,166 such pairs).
    3. Build date and a short hash appended when a variant *still* has several
       distinct builds, since `built_at` alone does not separate them.

    The extension comes from the URL, not a constant: most images are ``.bin``
    but CR4250 ships ``.vmp``.
    """
    groups = {}
    for row in rows:
        key = (row["model"], row["version"], row.get("variant") or "")
        groups.setdefault(key, set()).add(row["hash"])
    for row in rows:
        variant = row.get("variant") or ""
        key = (row["model"], row["version"], variant)
        parts = [f"{row['model']}-{row['version']}"]
        if variant:
            parts.append(variant)
        if len(groups.get(key, ())) > 1:
            date = (row.get("built_at") or "")[:10].replace("-", "")
            short = (row.get("hash") or "")[:6]
            parts.extend(part for part in (date, short) if part)
        row["filename"] = safe_filename("-".join(parts) + image_extension(row["url"]))
    return rows


def version_sort_key(version: str):
    """Natural sort key so 7.26.80 sorts after 7.9.0 rather than before it."""
    parts = re.split(r"[.\-_]", version or "")
    key = []
    for part in parts:
        if part.isdigit():
            key.append((0, int(part), ""))
        else:
            head = re.match(r"^(\d*)(.*)$", part)
            num = int(head.group(1)) if head.group(1) else 0
            key.append((1, num, head.group(2).lower()))
    return key


def _fetch_products(session):
    """Return {product_id: {"name", "series", "device_type"}} for all products."""
    products = {}
    url = PRODUCTS_URL
    params = {"limit": PAGE_LIMIT}
    while url:
        resp = _get_with_retry(session, url, params=params)
        payload = resp.json()
        for item in payload.get("data", []):
            products[str(item.get("id"))] = {
                "name": item.get("name") or "",
                "series": item.get("series"),
                "device_type": item.get("device_type") or "",
            }
        url = (payload.get("meta") or {}).get("next")
        params = None  # `next` already carries the query string
    return products


def _fetch_firmwares(session, progress):
    """Fetch every firmware record using parallel offset pagination.

    The v2 `meta` block has no total count, so offsets are requested
    speculatively in rounds and the loop stops on the first empty page.
    Records are deduped by id — this endpoint repeats records across pages
    (roughly 17.7k unique records arrive as ~20k rows).
    """
    records = {}
    offset = 0
    finished = False
    pages = 0

    def fetch_page(page_offset):
        resp = _get_with_retry(
            session, FIRMWARES_URL,
            params={"limit": PAGE_LIMIT, "offset": page_offset},
        )
        return resp.json().get("data", [])

    with ThreadPoolExecutor(max_workers=CATALOG_WORKERS) as pool:
        while not finished:
            offsets = [offset + i * PAGE_LIMIT for i in range(CATALOG_WORKERS)]
            for data in pool.map(fetch_page, offsets):
                pages += 1
                if not data:
                    finished = True
                for item in data:
                    records[str(item.get("id"))] = item
            offset += PAGE_LIMIT * CATALOG_WORKERS
            progress(rows=len(records), pages=pages)
    return list(records.values())


def _build_catalog():
    """Build the firmware catalog and persist it. Runs on a worker thread."""
    headers = auth_headers()
    if not headers:
        with _catalog_lock:
            _catalog_state.update(
                state="error", phase="",
                error="API credentials are not configured.",
            )
        return

    def progress(**kwargs):
        with _catalog_lock:
            _catalog_state.update(**kwargs)

    session = requests.Session()
    session.headers.update(headers)
    try:
        progress(state="running", phase="Loading product models…", rows=0, pages=0, error=None)
        products = _fetch_products(session)

        progress(phase="Loading firmware catalog…")
        raw = _fetch_firmwares(session, progress)

        progress(phase="Building index…")
        rows = []
        for item in raw:
            url = item.get("url") or ""
            if not url:
                continue
            pid = _product_id(item.get("product"))
            product = products.get(pid or "", {})
            model = product.get("name") or _model_from_url(url)
            if not model:
                continue
            rows.append({
                "id": str(item.get("id")),
                "model": model,
                "series": product.get("series"),
                "version": item.get("version") or "",
                "url": url,
                "variant": image_variant(url),
                "hash": item.get("hash") or "",
                "built_at": item.get("built_at") or "",
                "released_at": item.get("released_at") or "",
                "expires_at": item.get("expires_at") or "",
                "deprecated": bool(item.get("is_deprecated")),
            })

        assign_filenames(rows)
        rows.sort(key=lambda r: (r["model"].lower(), version_sort_key(r["version"]),
                                 r.get("built_at") or ""))
        models = sorted({r["model"] for r in rows}, key=str.lower)
        versions = sorted({r["version"] for r in rows if r["version"]},
                          key=version_sort_key, reverse=True)
        built_at = datetime.now(timezone.utc).isoformat()

        with _catalog_lock:
            _catalog.update(built_at=built_at, firmwares=rows, models=models, versions=versions)
            _catalog_state.update(state="ready", phase="", rows=len(rows), error=None)
        _save_catalog()
        print(f"[catalog] {len(rows)} firmware images, {len(models)} models, "
              f"{len(versions)} versions")
    except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
        message = str(exc)
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            if exc.response.status_code in (401, 403):
                message = "NCM rejected the API credentials (HTTP "
                message += f"{exc.response.status_code}). Check them in Settings."
        with _catalog_lock:
            _catalog_state.update(state="error", phase="", error=message)
        print(f"[catalog] build failed: {exc}", file=sys.stderr)
    finally:
        session.close()


def _save_catalog():
    try:
        CATALOG_PATH.write_text(json.dumps(_catalog), encoding="utf-8")
    except OSError as exc:
        print(f"[catalog] could not cache to disk: {exc}", file=sys.stderr)


def _load_catalog():
    if not CATALOG_PATH.exists():
        return
    try:
        cached = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        if cached.get("firmwares"):
            _catalog.update(cached)
            _catalog_state.update(state="ready", rows=len(cached["firmwares"]))
            print(f"[catalog] loaded {len(cached['firmwares'])} cached firmware images")
    except (json.JSONDecodeError, OSError):
        pass


def start_catalog_build():
    """Kick off a catalog build unless one is already running."""
    with _catalog_lock:
        if _catalog_state["state"] == "running":
            return False
        _catalog_state.update(state="running", phase="Starting…", rows=0, pages=0, error=None)
    threading.Thread(target=_build_catalog, daemon=True).start()
    return True


_load_catalog()


# --------------------------------------------------------------------------
# Download jobs
# --------------------------------------------------------------------------

_jobs = {}
_jobs_lock = threading.Lock()
_pool = None
_pool_size = 0


def _get_pool():
    """Thread pool for downloads, rebuilt when the concurrency setting changes."""
    global _pool, _pool_size
    want = max(1, min(int(_settings.get("concurrency", 3) or 3), 8))
    if _pool is None or _pool_size != want:
        old = _pool
        _pool = ThreadPoolExecutor(max_workers=want, thread_name_prefix="ncos-dl")
        _pool_size = want
        if old is not None:
            threading.Thread(target=old.shutdown, kwargs={"wait": False}, daemon=True).start()
    return _pool


def safe_filename(name: str) -> str:
    """Reduce a name to a bare filename inside the download directory.

    Strips any directory component so a crafted model/version string cannot
    escape the download directory.
    """
    name = os.path.basename((name or "").strip().replace("\\", "/"))
    name = re.sub(r"[^A-Za-z0-9._+-]", "_", name).lstrip(".")
    return name or "firmware.bin"


def _run_download(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job or job["state"] == "canceled":
            return
        job.update(state="downloading", started_at=time.time())
        url_path, expected_hash, filename = job["url"], job["hash"], job["filename"]

    headers = auth_headers() or {}
    target = download_dir() / filename
    part = target.with_suffix(target.suffix + ".part")
    verify = bool(_settings.get("verify_sha1", True))
    session = requests.Session()
    session.headers.update(headers)

    try:
        resp = _get_with_retry(session, image_download_url(url_path),
                               stream=True, timeout=300)
        total = int(resp.headers.get("Content-Length") or 0)
        with _jobs_lock:
            _jobs[job_id]["total"] = total

        digest = hashlib.sha1()
        received = 0
        last_push = 0.0
        with open(part, "wb") as handle:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                with _jobs_lock:
                    if _jobs.get(job_id, {}).get("cancel"):
                        raise _Canceled()
                if not chunk:
                    continue
                handle.write(chunk)
                digest.update(chunk)
                received += len(chunk)
                now = time.time()
                if now - last_push > 0.2:
                    last_push = now
                    with _jobs_lock:
                        _jobs[job_id]["received"] = received
        resp.close()

        actual = digest.hexdigest()
        if verify and expected_hash and actual != expected_hash:
            part.unlink(missing_ok=True)
            raise ValueError(
                f"SHA-1 mismatch — expected {expected_hash[:12]}…, got {actual[:12]}…"
            )

        part.replace(target)
        with _jobs_lock:
            _jobs[job_id].update(
                state="done", received=received, total=total or received,
                sha1=actual,
                verified=bool(expected_hash) and actual == expected_hash,
                finished_at=time.time(), path=str(target),
            )
    except _Canceled:
        part.unlink(missing_ok=True)
        with _jobs_lock:
            _jobs[job_id].update(state="canceled", finished_at=time.time())
    except Exception as exc:  # noqa: BLE001 - report any failure in the job row
        part.unlink(missing_ok=True)
        with _jobs_lock:
            _jobs[job_id].update(state="error", error=str(exc), finished_at=time.time())
    finally:
        session.close()


class _Canceled(Exception):
    """Raised inside the download loop when the user cancels a job."""


def _job_view(job):
    total, received = job.get("total") or 0, job.get("received") or 0
    elapsed = (job.get("finished_at") or time.time()) - (job.get("started_at") or time.time())
    return {
        "id": job["id"],
        "model": job["model"],
        "version": job["version"],
        "filename": job["filename"],
        "state": job["state"],
        "total": total,
        "received": received,
        "pct": round(received / total * 100, 1) if total else 0,
        "speed": round(received / elapsed) if elapsed > 0.5 and received else 0,
        "verified": job.get("verified"),
        "sha1": job.get("sha1"),
        "error": job.get("error"),
        "queued_at": job.get("queued_at"),
    }


# --------------------------------------------------------------------------
# Profiles
# --------------------------------------------------------------------------

def _load_profiles():
    if PROFILES_PATH.exists():
        try:
            return json.loads(PROFILES_PATH.read_text(encoding="utf-8")) or {}
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_profiles(profiles):
    PROFILES_PATH.write_text(json.dumps(profiles, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------
# App + routes
# --------------------------------------------------------------------------

app = FastAPI(title="NCOS Downloader")
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Serve logos from this app's own static folder — the app is self-contained.
STATIC_DIR = APP_DIR / "static"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((APP_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/status")
async def status():
    with _catalog_lock:
        catalog_state = dict(_catalog_state)
        built_at = _catalog["built_at"]
        counts = {
            "firmwares": len(_catalog["firmwares"]),
            "models": len(_catalog["models"]),
            "versions": len(_catalog["versions"]),
        }
    return {
        "credentials": bool(auth_headers()),
        "catalog": {**catalog_state, "built_at": built_at, **counts},
        "settings": {**_settings, "download_dir": str(download_dir())},
    }


@app.get("/api/catalog")
async def get_catalog():
    """Full firmware catalog. Gzip keeps the ~18k rows to a few hundred KB."""
    with _catalog_lock:
        if not _catalog["firmwares"]:
            return JSONResponse({
                "status": "empty",
                "state": _catalog_state["state"],
                "error": _catalog_state["error"],
            })
        return JSONResponse({
            "status": "ok",
            "built_at": _catalog["built_at"],
            "models": _catalog["models"],
            "versions": _catalog["versions"],
            "firmwares": _catalog["firmwares"],
        })


@app.post("/api/catalog/refresh")
async def refresh_catalog():
    if not auth_headers():
        return _no_creds_response()
    started = start_catalog_build()
    return {"status": "ok" if started else "already_running"}


@app.get("/api/catalog/status")
async def catalog_status():
    with _catalog_lock:
        return {**_catalog_state, "built_at": _catalog["built_at"]}


@app.get("/api/firmwares")
async def firmwares_by_version(version: str = "", model: str = ""):
    """Live single-version lookup — one API call, no catalog build required."""
    version = (version or "").strip()
    if not version:
        return JSONResponse({"status": "error", "message": "version is required"}, status_code=400)
    headers = auth_headers()
    if not headers:
        return _no_creds_response()

    session = requests.Session()
    session.headers.update(headers)
    try:
        resp = _get_with_retry(
            session, FIRMWARES_URL, params={"limit": PAGE_LIMIT, "version": version}
        )
        seen, rows = set(), []
        for item in resp.json().get("data", []):
            fid = str(item.get("id"))
            if fid in seen:
                continue
            seen.add(fid)
            url = item.get("url") or ""
            name = _model_from_url(url)
            if model and model.upper() not in name.upper():
                continue
            rows.append({
                "id": fid,
                "model": name,
                "series": None,
                "version": item.get("version") or version,
                "url": url,
                "variant": image_variant(url),
                "hash": item.get("hash") or "",
                "built_at": item.get("built_at") or "",
                "released_at": item.get("released_at") or "",
                "expires_at": item.get("expires_at") or "",
                "deprecated": bool(item.get("is_deprecated")),
            })
        assign_filenames(rows)
        rows.sort(key=lambda r: (r["model"].lower(), r.get("built_at") or ""))
        return {"status": "ok", "count": len(rows), "firmwares": rows}
    except requests.RequestException as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=502)
    finally:
        session.close()


@app.post("/api/sizes")
async def firmware_sizes(request: Request):
    """HEAD the CDN for the given paths to report image sizes on demand."""
    body = await request.json()
    paths = [p for p in (body.get("urls") or [])
             if isinstance(p, str) and is_downloadable(p)][:200]
    if not paths:
        return {"sizes": {}}
    headers = auth_headers() or {}

    def head(path):
        try:
            with requests.Session() as session:
                session.headers.update(headers)
                resp = session.head(image_download_url(path), timeout=20,
                                    allow_redirects=True)
                if resp.ok:
                    return path, int(resp.headers.get("Content-Length") or 0)
        except requests.RequestException:
            pass
        return path, None

    with ThreadPoolExecutor(max_workers=16) as pool:
        sizes = dict(pool.map(head, paths))
    return {"sizes": sizes}


@app.post("/api/downloads")
async def start_downloads(request: Request):
    """Queue one or more firmware images for download."""
    if not auth_headers():
        return _no_creds_response()
    body = await request.json()
    items = body.get("items") or []
    if not items:
        return JSONResponse({"status": "error", "message": "No firmware selected"}, status_code=400)

    queued, skipped, rejected = [], [], []
    existing = {p.name for p in download_dir().iterdir() if p.is_file()}
    overwrite = bool(body.get("overwrite"))

    for item in items[:200]:
        url_path = (item.get("url") or "").strip()
        model = (item.get("model") or "UNKNOWN").strip()
        version = (item.get("version") or "").strip()
        if not is_downloadable(url_path):
            # Report rather than drop, so a bad record can't vanish silently.
            rejected.append(f"{model} {version}".strip() or "unknown image")
            continue
        default_name = f"{model}-{version}{image_extension(url_path)}"
        filename = safe_filename(item.get("filename") or default_name)
        if filename in existing and not overwrite:
            skipped.append(filename)
            continue
        job_id = uuid.uuid4().hex[:12]
        with _jobs_lock:
            _jobs[job_id] = {
                "id": job_id, "model": model, "version": version, "url": url_path,
                "hash": (item.get("hash") or "").strip(), "filename": filename,
                "state": "queued", "total": 0, "received": 0, "cancel": False,
                "queued_at": time.time(), "started_at": None, "finished_at": None,
                "error": None, "sha1": None, "verified": None, "path": None,
            }
        _get_pool().submit(_run_download, job_id)
        queued.append(job_id)

    return {"status": "ok", "queued": len(queued), "job_ids": queued,
            "skipped": skipped, "rejected": rejected}


@app.get("/api/downloads")
async def list_jobs():
    with _jobs_lock:
        jobs = [_job_view(j) for j in _jobs.values()]
    jobs.sort(key=lambda j: j["queued_at"] or 0, reverse=True)
    active = sum(1 for j in jobs if j["state"] in ("queued", "downloading"))
    return {"jobs": jobs, "active": active}


@app.post("/api/downloads/{job_id}/cancel")
async def cancel_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            return JSONResponse({"status": "error", "message": "Unknown job"}, status_code=404)
        if job["state"] in ("done", "error", "canceled"):
            return {"status": "ok", "state": job["state"]}
        job["cancel"] = True
        if job["state"] == "queued":
            job["state"] = "canceled"
            job["finished_at"] = time.time()
    return {"status": "ok"}


@app.post("/api/downloads/clear")
async def clear_finished_jobs():
    with _jobs_lock:
        for job_id in [k for k, v in _jobs.items()
                       if v["state"] in ("done", "error", "canceled")]:
            del _jobs[job_id]
    return {"status": "ok"}


@app.get("/api/files")
async def list_files():
    """Firmware images already on disk, newest first."""
    directory = download_dir()
    files = []
    for path in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file() or path.suffix == ".part":
            continue
        stat = path.stat()
        files.append({
            "name": path.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        })
    files.sort(key=lambda f: f["modified"], reverse=True)
    total, used, free = shutil.disk_usage(directory)
    return {
        "dir": str(directory),
        "files": files,
        "count": len(files),
        "bytes": sum(f["size"] for f in files),
        "free": free,
    }


def _resolve_in_download_dir(name: str):
    """Resolve a filename inside the download dir, or None if it escapes it."""
    directory = download_dir()
    candidate = (directory / safe_filename(name)).resolve()
    if candidate.parent != directory or not candidate.is_file():
        return None
    return candidate


@app.get("/api/files/{name}")
async def get_file(name: str):
    path = _resolve_in_download_dir(name)
    if not path:
        return JSONResponse({"status": "error", "message": "File not found"}, status_code=404)
    return FileResponse(str(path), filename=path.name, media_type="application/octet-stream")


@app.get("/api/files/{name}/verify")
async def verify_file(name: str):
    """Re-hash a file on disk and compare it with the catalog's SHA-1."""
    path = _resolve_in_download_dir(name)
    if not path:
        return JSONResponse({"status": "error", "message": "File not found"}, status_code=404)
    digest = hashlib.sha1()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    with _catalog_lock:
        expected = next((f["hash"] for f in _catalog["firmwares"] if f["hash"] == actual), None)
    return {
        "status": "ok", "name": path.name, "sha1": actual,
        "in_catalog": bool(expected),
    }


@app.delete("/api/files/{name}")
async def delete_file(name: str):
    path = _resolve_in_download_dir(name)
    if not path:
        return JSONResponse({"status": "error", "message": "File not found"}, status_code=404)
    path.unlink()
    return {"status": "ok", "deleted": path.name}


@app.get("/api/settings")
async def get_settings():
    return {**_settings, "download_dir": str(download_dir())}


@app.post("/api/settings")
async def update_settings(request: Request):
    body = await request.json()
    if "download_dir" in body:
        raw = (body.get("download_dir") or "").strip()
        if raw:
            candidate = Path(raw).expanduser()
            try:
                candidate.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                return JSONResponse(
                    {"status": "error", "message": f"Cannot use that folder: {exc}"},
                    status_code=400,
                )
            _settings["download_dir"] = str(candidate.resolve())
    if "concurrency" in body:
        try:
            _settings["concurrency"] = max(1, min(int(body["concurrency"]), 8))
        except (TypeError, ValueError):
            pass
    if "verify_sha1" in body:
        _settings["verify_sha1"] = bool(body["verify_sha1"])
    _save_settings()
    return {"status": "ok", **_settings, "download_dir": str(download_dir())}


@app.get("/api/profiles")
async def list_profiles():
    profiles = _load_profiles()
    return {
        name: {k: (v[:4] + "…" if v and len(v) > 4 else "") for k, v in creds.items()}
        for name, creds in profiles.items()
    }


@app.post("/api/profiles")
async def save_profile(request: Request):
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        return JSONResponse({"error": "Profile name required"}, status_code=400)
    profiles = _load_profiles()
    if name in profiles and not body.get("overwrite"):
        return JSONResponse(
            {"error": "exists", "message": f"Profile '{name}' already exists"},
            status_code=409,
        )
    creds = body.get("credentials") or {}
    profiles[name] = {key: creds.get(key, "") for key in CRED_KEYS}
    _save_profiles(profiles)
    return {"status": "ok", "name": name}


@app.post("/api/profiles/load")
async def load_profile(request: Request):
    body = await request.json()
    name = (body.get("name") or "").strip()
    profiles = _load_profiles()
    if name not in profiles:
        return JSONResponse({"error": f"Profile '{name}' not found"}, status_code=404)
    for key, value in profiles[name].items():
        if value:
            os.environ[key] = value
    return {"status": "ok", "name": name}


@app.delete("/api/profiles/{name}")
async def delete_profile(name: str):
    profiles = _load_profiles()
    if name not in profiles:
        return JSONResponse({"error": f"Profile '{name}' not found"}, status_code=404)
    del profiles[name]
    _save_profiles(profiles)
    return {"status": "ok", "deleted": name}


@app.get("/api/profiles/current")
async def current_credentials():
    return {
        key: {"set": bool(os.environ.get(key)), "value": os.environ.get(key, "")}
        for key in CRED_KEYS
    }


@app.post("/api/credentials/apply")
async def apply_credentials(request: Request):
    body = await request.json()
    creds = body.get("credentials") or {}
    for key in CRED_KEYS:
        value = (creds.get(key) or "").strip()
        if value:
            os.environ[key] = value
    return {"status": "ok", "credentials": bool(auth_headers())}


def main():
    directory = download_dir()
    print("=" * 62)
    print("  NCOS Downloader")
    print("=" * 62)
    print(f"  URL:        http://localhost:{PORT}")
    print(f"  Downloads:  {directory}")
    if auth_headers():
        print("  Credentials: found in environment")
    else:
        print("  Credentials: MISSING — enter them in Settings (gear icon)")
        if _setup_script():
            print("               or run: python3 setup_env.py --credentials-only")
    print("=" * 62)
    # Warm the catalog in the background so the first page load has data.
    if auth_headers() and not _catalog["firmwares"]:
        start_catalog_build()
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
