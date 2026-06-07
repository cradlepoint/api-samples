---
inclusion: auto
description: Web UI standards — use the web_app_template at scripts/script_manager/static/ as the style foundation, with required light/dark mode support, CSS custom properties, and responsive breakpoints.
---

# Web UI Standards

## Style Template

When creating any web UI or web application in this project, always use the `web_app_template` as the style foundation. The template lives at:

- HTML structure: `web_apps/web_app_template/index.html`
- CSS styles: `web_apps/script_manager/static/css/style.css`
- JS patterns: `web_apps/script_manager/static/js/app.js`
- Logo (light): `web_apps/script_manager/static/logo.png`
- Logo (dark): `web_apps/script_manager/static/logo_dark.png`

This template contains everything needed for a consistent, polished web interface:
- App shell layout (header, sidebar, content area)
- Navigation with collapsible sidebar
- Panel and card components
- Button styles (primary, secondary, danger, sm variants)
- Form inputs, labels, and validation indicators
- Modal dialogs (standard and large)
- Table styling with sticky headers
- File upload areas
- Notification toasts
- Empty states
- Responsive breakpoints (1024px, 768px)
- CSS custom properties for all colors, shadows, radii, and transitions

## Light Mode / Dark Mode

Every web app must include light mode and dark mode support. The template implements this via:

1. A `body.dark-mode` CSS class toggle
2. A dark mode toggle button in the header with id `darkModeToggle`
3. CSS custom properties in `:root` for light theme defaults
4. `body.dark-mode` overrides for all surfaces, text, borders, inputs, tables, modals, buttons, and notifications
5. Logo swap using `body.dark-mode .app-logo { content: url('/static/logo_dark.png'); }`
6. Persist the user's preference in `localStorage`

When building a new web app:
- Copy the CSS variables and dark mode overrides from the template CSS
- Include the dark mode toggle button in the header
- Wire up the toggle with JS that adds/removes `body.dark-mode` and saves to `localStorage`
- On page load, check `localStorage` and apply the saved preference
- Ensure all new components respect both themes by using `var(--*)` custom properties rather than hardcoded colors

## Key CSS Variables (from template)

```css
--primary-color: #4f46e5;
--primary-dark: #3730a3;
--secondary-color: #6b7280;
--success-color: #059669;
--warning-color: #d97706;
--danger-color: #dc2626;
--info-color: #0284c7;
--dark-bg: #111827;
--dark-surface: #1f2937;
--light-bg: #f9fafb;
--light-surface: #ffffff;
--text-primary: #111827;
--text-secondary: #6b7280;
--text-light: #9ca3af;
--border-color: #d1d5db;
```

## Checklist for New Web Apps

1. Use the template HTML structure (app-container → app-header → app-main → sidebar + content-area)
2. Include the template CSS or copy the relevant portions
3. Implement dark mode toggle with localStorage persistence
4. Use CSS custom properties for all colors — never hardcode
5. Include both `logo.png` and `logo_dark.png` with the swap rule
6. Ensure responsive behavior at 1024px and 768px breakpoints

## Dashboard Template

When a user asks for a "dashboard" (any data-driven web app that displays NCM API data
in a table/card layout), use `dashboards/cellular_health/` as the reference
implementation. It demonstrates the standard dashboard pattern for this project.

**Reference files:**
- `dashboards/cellular_health/serve.py` — FastAPI backend with API endpoints
- `dashboards/cellular_health/index.html` — Single-page frontend

### Required Dashboard Features

Every dashboard must include:

1. **Settings modal** (gear icon in header)
   - API key inputs: `X_CP_API_ID`, `X_CP_API_KEY`, `X_ECM_API_ID`, `X_ECM_API_KEY`
   - Include `NCM_API_TOKEN` field if the dashboard uses v3 endpoints
   - ID fields shown in clear text; KEY fields shown as password with eye toggle
   - Named profiles: Save, Save As (with overwrite confirmation), Load, Delete
   - Profiles stored in `profiles.json` on disk
   - "Apply & Refresh" button to set credentials and reload data
   - Display options section (e.g. grouping toggles)
   - On open, populate fields with current environment values so they can be saved

2. **Sortable columns**
   - Click column header to sort ascending, click again for descending
   - Show ↑/↓ arrow indicator on sorted column
   - Use document-level event delegation for click handling
   - If grouping is enabled, sort groups by representative value while keeping
     group members together; sort within groups as secondary

3. **Search box**
   - Full-text search across key text columns
   - Clicking a text cell (device name, carrier, model) auto-populates the search
   - Clear button (✕) appears when text is present
   - Clickable cells show pointer cursor and underline on hover

4. **Stat cards as filters**
   - Top-level summary cards (Total, Online, Offline, signal categories, etc.)
   - Clicking a card filters the table to that subset
   - Active card gets highlighted border; clicking again clears the filter

5. **Export buttons**
   - **CSV**: Export filtered/sorted data as downloadable `.csv` file
   - **PDF**: Use jsPDF + AutoTable for a polished PDF with:
     - Branded header with title and account name
     - Summary stats line
     - Color-coded columns (health, status)
     - Alternating row shading
     - Page numbers in footer

6. **Grouping** (where applicable)
   - Group related rows (e.g. multiple interfaces per device) with alternating shading
   - Toggle via Display Options in Settings
   - Default on; persisted in localStorage

### Backend Pattern

```python
# FastAPI app with:
# - GET / → serve index.html
# - GET /api/data → main data endpoint (fetch, join, return JSON)
# - GET /api/profiles → list profiles
# - POST /api/profiles → save profile
# - POST /api/profiles/load → load profile into env
# - DELETE /api/profiles/{name} → delete profile
# - GET /api/profiles/current → return current env credentials
# - POST /api/credentials/apply → apply credentials without saving
# - /static mount for shared logos

# IMPORTANT: All @app route definitions must come BEFORE the
# `if __name__ == "__main__"` block. uvicorn.run() blocks forever,
# so any routes defined after it will never be registered.
```

### Frontend Libraries (CDN)

- jsPDF: `https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js`
- jsPDF-AutoTable: `https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js`
- Google Fonts Inter: `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap`
