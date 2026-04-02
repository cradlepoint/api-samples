# Web App Template

A lightweight, self-contained component library and style guide for building dashboards, admin consoles, and internal tools. No frameworks, no build steps — just vanilla HTML, CSS, and JavaScript.

## Quick Start

```bash
python3 serve.py
# Open http://localhost:8000
```

Or just open `index.html` directly in a browser.

## What's Included

| File | Purpose |
|------|---------|
| `index.html` | Interactive style guide with all component examples |
| `your_web_app.html` | Clean starter template using the same design system |
| `serve.py` | Optional Python dev server (zero dependencies) |
| `static/css/style.css` | Complete design system (colors, typography, layout, components) |
| `static/js/script.js` | Component interactivity (dark mode, navigation, builders) |
| `static/libs/` | Font Awesome icons and jQuery |

## Components

- **Buttons** — Primary, secondary, success, warning, danger, info, text variants with a Button Builder
- **Form Elements** — Text, number, checkbox, textarea, radio, slider, dropdown, toggle switch
- **Tabs** — Accessible tabbed navigation
- **Cards & Panels** — Content containers for dashboards
- **Typography** — Heading hierarchy and text styles
- **Colors** — Full semantic palette with dark mode support
- **Status Indicators** — GPS, network, modem, signal, connectivity, power, disk, CPU, memory, battery, temperature, ethernet, VPN, NTP, GPIO
- **Notifications** — Success, warning, error, info toasts
- **Loading States** — Spinners, overlays, running indicators
- **Progress Bars** — Basic, labeled, colored, animated variants
- **Search** — Input with clear button patterns
- **Charts** — Bar, line, pie, area, horizontal bar, donut (pure CSS/SVG)

## Building Your Own App

1. Copy `your_web_app.html` as your starting point
2. Browse `index.html` for component examples
3. Copy the HTML markup you need into your app
4. Customize labels, data bindings, and behavior

The starter template includes the sidebar layout, dark mode toggle, and search bar pre-wired.

## Design System

All components share CSS custom properties defined in `style.css`:

- Color tokens (`--primary-color`, `--success-color`, etc.)
- Typography (Inter font stack)
- Spacing and border radius (`--radius-sm` through `--radius-xl`)
- Shadows (`--shadow-sm` through `--shadow-xl`)
- Light/dark theme via `[data-theme="dark"]`

## Requirements

- Modern web browser
- Python 3 (optional, only for the dev server)
