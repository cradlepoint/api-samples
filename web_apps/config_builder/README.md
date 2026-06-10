# Config Builder

A local web-based tool for building Cradlepoint .bin configuration files from templates with per-site variable substitution. No cloud or NCM API calls — everything runs on your machine.

<img width="1532" height="843" alt="image" src="https://github.com/user-attachments/assets/0efa4770-10b6-461d-b871-8f2b9e206317" />
<img width="1532" height="843" alt="image" src="https://github.com/user-attachments/assets/c48195bf-73c0-4367-af3b-70b4adc230e9" />
<img width="1532" height="843" alt="image" src="https://github.com/user-attachments/assets/cb9f3279-aeb0-4106-8e58-6d7938612ffd" />

## Features

- **Config Templates** — named pairs of Base + Full JSON configs with `{{variable_name}}` placeholders
- **Build** — select a template, fill in site-specific values, download Base and Full .bin configs
- **Saved Sites** — store site data in CSV files for reuse
- Supports `.bin` file import (auto-decompresses Cradlepoint zlib/gzip exports)
- Variable type validation: `string`, `integer`, `float`, `boolean`, `ipv4`, `ipv6`, `cidr`, `mac`
- Light and dark mode

## Requirements

- **Python 3.7+** (no external packages — uses only the standard library)

## Quick Start

```bash
cd config_builder
python3 config_builder.py    # macOS/Linux
python config_builder.py     # Windows
```

Open http://localhost:8100 in your browser.

## Workflow

1. **Create a Config Template** — give it a name, upload/paste a Base config (connectivity on install), then a Full config (applied by remote admin). Replace site-specific values with `{{Variable Name}}` placeholders.

2. **Build** — select your template. Fill in the form (RDL, Store Name, Site Address, City, EWP ID, Router Model, plus any template variables). Save the site, then download Base and/or Full configs as .bin files.

3. **Reuse** — switch to "Load Saved Site" to pick a previously saved site, edit if needed, and re-download.

## Variable Syntax

```json
{
  "name": "Vlan2",
  "ip_address": "{{Vlan2 IP Address}}"
}
```

- `{{variable_name}}` — defaults to string type
- `{{variable_name|type}}` — with explicit type (e.g. `{{vlan|integer}}`)

## Output Filenames

Downloaded .bin files are named:

```
RDL{RDL} - {Router Model} - {Base/Full} Config.bin
```

Example: `RDL999222 - E3000 - Full Config.bin`

## File Structure

```
config_builder/
├── config_builder.py      # Python server (run this)
├── router_models.csv      # Router model list (add models here)
├── requirements.txt       # Dependencies (none)
├── README.md              # This file
├── static/
│   ├── index.html         # Web UI
│   ├── css/style.css      # Styles
│   ├── js/app.js          # Client logic
│   ├── logo.png           # Light mode logo
│   └── logo_dark.png      # Dark mode logo
├── templates/             # Saved config templates (auto-created)
└── sites/                 # Saved site CSV files (auto-created)
```

## Notes

- Port defaults to **8100**. Edit `PORT` in `config_builder.py` to change.
- Add router models by editing `router_models.csv`.
- All data is stored locally in `templates/` and `sites/`.
- Works on macOS, Linux, and Windows.
