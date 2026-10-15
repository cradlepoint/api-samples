# NCOS Downloader

Browse and download NCOS firmware images from the NetCloud Manager API, with SHA-1
verification on every download.

This folder is self-contained — copy or unzip it anywhere and it runs on its own.

## Quick start (standalone)

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 serve.py                     # Windows: python serve.py
```

Then open <http://localhost:8075> and enter your API keys in the Settings panel (gear
icon). The app prompts for them on first run and can save them as a named profile.

Requires Python 3.9+ (tested on 3.12). Dependencies are `fastapi`, `uvicorn`,
`requests`, and `python-dotenv` — see `requirements.txt`.

## Quick start (inside this repo)

```bash
source .venv/bin/activate && python3 web_apps/ncos_downloader/serve.py
```

Credentials are picked up from the repo-root `.env` automatically.

## What it does

Firmware metadata comes from the v2 `/firmwares/` endpoint. The actual `.bin` images
live on Cradlepoint's CDN, referenced by the `url` field on each firmware record. Each
record also publishes a `hash` — the SHA-1 of the image — which this app checks after
every download. A mismatch deletes the partial file rather than leaving a corrupt image
on disk.

- **Browse** all firmware for your account, filtered by model, version, or free text
- **Latest per Model** — the default view: newest build of the newest version for each
  of your models, which is the usual "what should I flash?" question
- **Bulk download** with a queue, live progress, cancel, and configurable concurrency
- **File management** — list, save to browser, re-verify, and delete downloaded images
- **CSV / PDF export** of whatever the current filters show

## The catalog

`/firmwares/` has no "filter by model" parameter, so listing a model's firmware means
pulling the whole catalog. The app does that once (~10 seconds), joins it against
`/products/` to resolve model names, and caches the result in `catalog_cache.json` so
later visits load instantly. Use **Refresh Catalog** after a new NCOS release.

Two quirks of the endpoint shape the implementation:

- **Records repeat across pages.** A full pull returns roughly 20,000 rows for about
  17,700 distinct firmware images, so records are deduped by `id`.
- **`meta` carries no total count.** Pagination can't be pre-planned from a count, so
  the app requests offsets speculatively in parallel rounds and stops on the first
  empty page — about 10 seconds instead of the ~55 that sequential `meta.next`
  following takes.

## Filenames

Images are saved as `MODEL-VERSION.bin`.

NCM frequently publishes several distinct builds of the same model and version — around
two thirds of model/version pairs in a full catalog. Where that happens, the build date
and a short hash are appended so the builds stay distinguishable:

```
IBR600C-7.26.100-20260916-d53a04.bin
IBR600C-7.26.100-20260921-85b622.bin
```

A filename already on disk is skipped, so re-downloading is safe. The per-row button
offers to overwrite when the image is already present.

## Credentials

The app reads `X_CP_API_ID`, `X_CP_API_KEY`, `X_ECM_API_ID`, and `X_ECM_API_KEY` from
the environment. To set them without putting keys in a browser or a chat transcript:

```bash
python3 setup_env.py --credentials-only       # macOS / Linux
python setup_env.py --credentials-only        # Windows
```

The Settings panel also accepts them directly, and supports named profiles for working
across several accounts. Profiles are stored in `profiles.json` (gitignored).

`NCM_API_TOKEN` is not needed — this app only uses v2 endpoints.

## Settings

| Setting | Default | Notes |
|---|---|---|
| Download folder | `web_apps/ncos_downloader/downloads/` | Any writable absolute path |
| Simultaneous downloads | 3 | 1–8 |
| Verify SHA-1 | on | Turning it off skips the integrity check |

Saved to `settings.json`. Generated files (`catalog_cache.json`, `settings.json`,
`profiles.json`, and `downloads/`) are gitignored — firmware images are tens of
megabytes each.

## Files

| Path | Purpose |
|---|---|
| `serve.py` | Backend, and the entry point |
| `index.html` | Entire UI — no build step, no bundler |
| `static/` | Logos for light and dark mode |
| `requirements.txt` | Pinned dependencies |

Those five are all a recipient needs. Everything else in the folder is generated at
runtime and safe to delete.

## Sharing a copy

Zip the folder, but leave the generated files out — `profiles.json` holds API keys, and
`downloads/` holds firmware images that are tens of megabytes each:

```bash
zip -r ncos_downloader.zip ncos_downloader \
  -x '*/downloads/*' '*/catalog_cache.json' '*/settings.json' \
     '*/profiles.json' '*/.env' '*/__pycache__/*' '*/.venv/*'
```

Confirm with `unzip -l ncos_downloader.zip` before sending.

## API endpoints

| Route | Purpose |
|---|---|
| `GET /api/status` | Credentials, catalog state, settings |
| `GET /api/catalog` | Full cached catalog (gzipped) |
| `POST /api/catalog/refresh` | Start a background rebuild |
| `GET /api/catalog/status` | Build progress |
| `GET /api/firmwares?version=` | Live single-version lookup, no catalog needed |
| `POST /api/sizes` | Parallel HEAD for image sizes |
| `POST /api/downloads` | Queue downloads |
| `GET /api/downloads` | Job progress |
| `POST /api/downloads/{id}/cancel` | Cancel a job |
| `GET|DELETE /api/files/{name}` | Save or delete a downloaded image |
| `GET /api/files/{name}/verify` | Re-hash a file and check it against the catalog |
| `GET|POST /api/settings` | Read or update settings |
| `GET|POST|DELETE /api/profiles` | Credential profile CRUD |

## Security

The server binds `127.0.0.1:8075` with no authentication — fine for local use. Don't
expose the port on a shared network: anyone who can reach it could read the credentials
held in the Settings panel. File operations are confined to the configured download
folder, and download requests only accept CDN paths, not arbitrary URLs.
