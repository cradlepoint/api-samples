---
inclusion: auto
---

# Web UI Standards

## Style Template

When creating any web UI or web application in this project, always use the `web_app_template` as the style foundation. The template lives at:

- HTML structure: `scripts/script_manager/static/index.html`
- CSS styles: `scripts/script_manager/static/css/style.css`
- JS patterns: `scripts/script_manager/static/js/app.js`
- Logo (light): `scripts/script_manager/static/logo.png`
- Logo (dark): `scripts/script_manager/static/logo_dark.png`

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
