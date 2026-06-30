---
inclusion: fileMatch
fileMatchPattern: "{**/*.html,**/*.css,**/web_apps/**,**/dashboards/**}"
description: Web UI standards — template references, dark mode, dashboard requirements.
---

# Web UI Standards

## Style Foundation

All web UIs must use the project template as the style base:
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

For data-driven dashboards, use `dashboards/cellular_health/` as reference:
- Backend: `dashboards/cellular_health/serve.py` (FastAPI)
- Frontend: `dashboards/cellular_health/index.html`

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
/static         → mount for shared logos
```

**All @app routes must be defined BEFORE `uvicorn.run()` (which blocks forever).**

### Frontend CDN Libraries

- jsPDF: `cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js`
- AutoTable: `cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js`
- Inter font: `fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap`
