---
inclusion: fileMatch
fileMatchPattern: "{**/*.html,**/*.css,**/web_apps/**}"
description: Web UI standards — template references, dark mode, dashboard requirements.
---

# Web UI Standards

## Apps are self-contained (required)

**No app may read files from another app at runtime.** Every app serves only from its
own directory. An app folder must be copyable on its own — zip it, send it, and it
runs with nothing but `requirements.txt` installed.

This means each app owns its own `static/` directory with its own `logo.png` and
`logo_dark.png`:

```python
STATIC_DIR = Path(__file__).resolve().parent / "static"      # own folder, never a sibling's
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
```

Never write `.parent.parent / "<other_app>" / "static"`. Duplicating a 6 KB logo into
each app is the correct trade; a shared folder silently breaks every standalone copy.

Each app also needs its own `requirements.txt` listing only what that app imports —
not a copy of the root file, which is the union across all apps.

## Style Foundation

Use the project template as the style base. These are **copy-from** references, read
at authoring time and copied into the new app — not paths to depend on at runtime:

- HTML: `web_apps/web_app_template/index.html`
- CSS: `web_apps/script_manager/static/css/style.css`
- JS: `web_apps/script_manager/static/js/app.js`
- Logos: `web_apps/script_manager/static/logo.png` / `logo_dark.png`

Read these files for the full set of CSS custom properties, layout patterns, and component styles.

## Layout Structure

Use: `app-container → app-header → app-main → sidebar + content-area`

Components available in template CSS: panels, cards, buttons (primary/secondary/danger/sm), form inputs, modals (standard/large), tables with sticky headers, file upload areas, toasts, empty states.

## Dark Mode (Required)

Every web app must support light/dark mode:
- Toggle via `body.dark-mode` class
- Button with id `darkModeToggle` in header
- CSS vars in `:root` (light) overridden in `body.dark-mode`
- Logo swap: `body.dark-mode .app-logo { content: url('/static/logo_dark.png'); }`
- Persist preference in `localStorage`
- Use `var(--*)` properties for all colors — never hardcode

## Responsive

Breakpoints at 1024px and 768px. Sidebar collapses on smaller screens.

## Dashboard Pattern

For data-driven dashboards, use `web_apps/cellular_health_dashboard/` as reference:
- Backend: `web_apps/cellular_health_dashboard/serve.py` (FastAPI)
- Frontend: `web_apps/cellular_health_dashboard/index.html`

### Required Dashboard Features

1. **Settings modal** (gear icon) — API key inputs (`X_CP_API_ID`, `X_CP_API_KEY`, `X_ECM_API_ID`, `X_ECM_API_KEY`, optionally `NCM_API_TOKEN`), named profiles (save/load/delete via `profiles.json`), "Apply & Refresh" button, display options
2. **Sortable columns** — click toggles asc/desc with arrow indicator; document-level event delegation; respects grouping
3. **Search box** — full-text across key columns, clicking text cells auto-populates, clear button
4. **Stat cards as filters** — summary cards filter table on click, highlighted when active, click again to clear
5. **Export CSV** — filtered/sorted data as downloadable `.csv`
6. **Export PDF** — jsPDF + AutoTable: branded header, summary stats, color-coded columns, alternating rows, page numbers
7. **Grouping** (where applicable) — alternating shading, toggle in Display Options, default on, persisted in localStorage

### Backend Routes

```
GET /           → serve index.html
GET /api/data   → main data endpoint
GET|POST|DELETE /api/profiles → profile CRUD
POST /api/profiles/load → load profile into env
GET /api/profiles/current → current env credentials
POST /api/credentials/apply → apply without saving
/static         → mount the app's OWN static folder (logos)
```

**All @app routes must be defined BEFORE `uvicorn.run()` (which blocks forever).**

These dashboards bind a local port with **no authentication**. That is fine for
localhost use, but say so if a user asks about exposing one on a network — the
credentials in the Settings panel would be reachable by anyone who can hit the port.
Apps that can push firmware or config changes to a fleet should bind `127.0.0.1`
rather than `0.0.0.0`.

### Frontend CDN Libraries

- jsPDF: `cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js`
- AutoTable: `cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js`
- Inter font: `fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap`
