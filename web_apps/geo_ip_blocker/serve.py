#!/usr/bin/env python3
"""
Geo IP Blocker — Select regions to block, convert IP ranges to Cradlepoint
zone firewall filter policy rules, and push to NCM groups.

Usage:
    .venv/bin/python web_apps/geo_ip_blocker/serve.py

Then open http://localhost:8065 in your browser.
"""

import os
import sys
import json
import uuid
import asyncio
import ipaddress
from pathlib import Path
from typing import Dict, List, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
    # Also try loading from project root
    load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import httpx

# Add project root to path for ncm import
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'ncm'))

import ncm

# --- Constants ---
IPDENY_BASE_URL = "https://www.ipdeny.com/ipblocks/data/aggregated"
PORT = 8065

# Country list organized by region
COUNTRIES_BY_REGION = {
    "Africa": {
        "DZ": "Algeria", "AO": "Angola", "BJ": "Benin", "BW": "Botswana",
        "BF": "Burkina Faso", "BI": "Burundi", "CM": "Cameroon", "CV": "Cape Verde",
        "CF": "Central African Republic", "TD": "Chad", "KM": "Comoros",
        "CG": "Congo", "CD": "Congo (DRC)", "CI": "Cote d'Ivoire", "DJ": "Djibouti",
        "EG": "Egypt", "GQ": "Equatorial Guinea", "ER": "Eritrea", "ET": "Ethiopia",
        "GA": "Gabon", "GM": "Gambia", "GH": "Ghana", "GN": "Guinea",
        "GW": "Guinea-Bissau", "KE": "Kenya", "LS": "Lesotho", "LR": "Liberia",
        "LY": "Libya", "MG": "Madagascar", "MW": "Malawi", "ML": "Mali",
        "MR": "Mauritania", "MU": "Mauritius", "MA": "Morocco", "MZ": "Mozambique",
        "NA": "Namibia", "NE": "Niger", "NG": "Nigeria", "RW": "Rwanda",
        "ST": "Sao Tome and Principe", "SN": "Senegal", "SC": "Seychelles",
        "SL": "Sierra Leone", "SO": "Somalia", "ZA": "South Africa", "SS": "South Sudan",
        "SD": "Sudan", "SZ": "Eswatini", "TZ": "Tanzania", "TG": "Togo",
        "TN": "Tunisia", "UG": "Uganda", "ZM": "Zambia", "ZW": "Zimbabwe"
    },
    "Asia": {
        "AF": "Afghanistan", "AM": "Armenia", "AZ": "Azerbaijan", "BH": "Bahrain",
        "BD": "Bangladesh", "BT": "Bhutan", "BN": "Brunei", "KH": "Cambodia",
        "CN": "China", "GE": "Georgia", "HK": "Hong Kong", "IN": "India",
        "ID": "Indonesia", "IR": "Iran", "IQ": "Iraq", "IL": "Israel",
        "JP": "Japan", "JO": "Jordan", "KZ": "Kazakhstan", "KW": "Kuwait",
        "KG": "Kyrgyzstan", "LA": "Laos", "LB": "Lebanon", "MO": "Macau",
        "MY": "Malaysia", "MV": "Maldives", "MN": "Mongolia", "MM": "Myanmar",
        "NP": "Nepal", "KP": "North Korea", "OM": "Oman", "PK": "Pakistan",
        "PS": "Palestine", "PH": "Philippines", "QA": "Qatar", "SA": "Saudi Arabia",
        "SG": "Singapore", "KR": "South Korea", "LK": "Sri Lanka", "SY": "Syria",
        "TW": "Taiwan", "TJ": "Tajikistan", "TH": "Thailand", "TL": "Timor-Leste",
        "TR": "Turkey", "TM": "Turkmenistan", "AE": "United Arab Emirates",
        "UZ": "Uzbekistan", "VN": "Vietnam", "YE": "Yemen"
    },
    "Europe": {
        "AL": "Albania", "AD": "Andorra", "AT": "Austria", "BY": "Belarus",
        "BE": "Belgium", "BA": "Bosnia and Herzegovina", "BG": "Bulgaria",
        "HR": "Croatia", "CY": "Cyprus", "CZ": "Czech Republic", "DK": "Denmark",
        "EE": "Estonia", "FI": "Finland", "FR": "France", "DE": "Germany",
        "GR": "Greece", "HU": "Hungary", "IS": "Iceland", "IE": "Ireland",
        "IT": "Italy", "XK": "Kosovo", "LV": "Latvia", "LI": "Liechtenstein",
        "LT": "Lithuania", "LU": "Luxembourg", "MK": "North Macedonia",
        "MT": "Malta", "MD": "Moldova", "MC": "Monaco", "ME": "Montenegro",
        "NL": "Netherlands", "NO": "Norway", "PL": "Poland", "PT": "Portugal",
        "RO": "Romania", "RU": "Russia", "SM": "San Marino", "RS": "Serbia",
        "SK": "Slovakia", "SI": "Slovenia", "ES": "Spain", "SE": "Sweden",
        "CH": "Switzerland", "UA": "Ukraine", "GB": "United Kingdom",
        "VA": "Vatican City"
    },
    "North America": {
        "AG": "Antigua and Barbuda", "BS": "Bahamas", "BB": "Barbados",
        "BZ": "Belize", "CA": "Canada", "CR": "Costa Rica", "CU": "Cuba",
        "DM": "Dominica", "DO": "Dominican Republic", "SV": "El Salvador",
        "GD": "Grenada", "GT": "Guatemala", "HT": "Haiti", "HN": "Honduras",
        "JM": "Jamaica", "MX": "Mexico", "NI": "Nicaragua", "PA": "Panama",
        "KN": "Saint Kitts and Nevis", "LC": "Saint Lucia",
        "VC": "Saint Vincent and the Grenadines", "TT": "Trinidad and Tobago",
        "US": "United States"
    },
    "South America": {
        "AR": "Argentina", "BO": "Bolivia", "BR": "Brazil", "CL": "Chile",
        "CO": "Colombia", "EC": "Ecuador", "GY": "Guyana", "PY": "Paraguay",
        "PE": "Peru", "SR": "Suriname", "UY": "Uruguay", "VE": "Venezuela"
    },
    "Oceania": {
        "AU": "Australia", "FJ": "Fiji", "KI": "Kiribati", "MH": "Marshall Islands",
        "FM": "Micronesia", "NR": "Nauru", "NZ": "New Zealand", "PW": "Palau",
        "PG": "Papua New Guinea", "WS": "Samoa", "SB": "Solomon Islands",
        "TO": "Tonga", "TV": "Tuvalu", "VU": "Vanuatu"
    }
}


# --- Credential helpers ---

def get_api_keys_from_env() -> dict:
    """Build an API keys dict from environment variables (NCM SDK format)."""
    keys = {
        'X-CP-API-ID': os.environ.get('X_CP_API_ID', ''),
        'X-CP-API-KEY': os.environ.get('X_CP_API_KEY', ''),
        'X-ECM-API-ID': os.environ.get('X_ECM_API_ID', ''),
        'X-ECM-API-KEY': os.environ.get('X_ECM_API_KEY', ''),
    }
    token = os.environ.get('NCM_API_TOKEN')
    if token:
        keys['token'] = token
    return keys


def _build_client():
    """Create an NCM SDK client from environment variables."""
    api_keys = get_api_keys_from_env()
    missing = []
    if not api_keys.get('X-CP-API-ID'):
        missing.append('X_CP_API_ID')
    if not api_keys.get('X-CP-API-KEY'):
        missing.append('X_CP_API_KEY')
    if not api_keys.get('X-ECM-API-ID'):
        missing.append('X_ECM_API_ID')
    if not api_keys.get('X-ECM-API-KEY'):
        missing.append('X_ECM_API_KEY')
    if missing:
        raise RuntimeError(
            f"Missing required API credentials: {', '.join(missing)}. "
            "Use the Settings panel to configure credentials, or set "
            "X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY "
            "environment variables."
        )
    client = ncm.NcmClient(api_keys=api_keys)
    return client


# --- ZFW Rule Generation ---

def generate_zfw_filter_policy(country_codes: List[str], ip_blocks: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Generate a Cradlepoint ZFW filter policy configuration from IP blocks.

    Creates:
    - IP identities for each country's IP blocks
    - A filter policy with deny rules for each country
    - The configuration diff ready for PATCH

    Returns the full configuration dict.
    """
    identities_ip = {}
    filter_policy_rules = {}
    rule_index = 0

    for code in country_codes:
        blocks = ip_blocks.get(code, [])
        if not blocks:
            continue

        country_name = _get_country_name(code)

        # Create an IP identity for this country's IP blocks
        identity_id = str(uuid.uuid4())
        # Members is a list of address objects
        members = [{'address': cidr} for cidr in blocks]

        identities_ip[identity_id] = {
            '_id_': identity_id,
            'name': f"GeoBlock-{code}-{country_name}",
            'members': members
        }

        # Create a deny rule referencing this identity
        # Rules within a filter policy use numeric string keys
        filter_policy_rules[str(rule_index)] = {
            'action': 'deny',
            'ip_version': 'ip4',
            'name': f"Block {country_name} ({code})",
            'priority': (rule_index + 1) * 10,
            'dst': {
                'ip': [],
                'port': [],
                'mac': []
            },
            'src': {
                'ip': {
                    '0': {'identity': identity_id}
                },
                'port': [],
                'mac': []
            },
            'protocols': [],
            'app_sets': []
        }
        rule_index += 1

    # Build the filter policy
    policy_id = str(uuid.uuid4())
    filter_policy = {
        policy_id: {
            '_id_': policy_id,
            'name': 'GeoBlock-Policy',
            'default_action': 'allow',
            'rules': filter_policy_rules
        }
    }

    # Build the full configuration diff
    config = {
        'configuration': [
            {
                'security': {
                    'zfw': {
                        'filter_policies': filter_policy
                    }
                },
                'identities': {
                    'ip': identities_ip
                }
            },
            []
        ]
    }

    return config


def _get_country_name(code: str) -> str:
    """Look up country name from code."""
    for region_countries in COUNTRIES_BY_REGION.values():
        if code in region_countries:
            return region_countries[code]
    return code


# --- FastAPI App ---

app = FastAPI(title="Geo IP Blocker")

# Serve logos from the shared static folder
STATIC_DIR = Path(__file__).resolve().parent.parent / "script_manager" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Profiles storage
PROFILES_PATH = Path(__file__).parent / "profiles.json"


def _load_profiles():
    if PROFILES_PATH.exists():
        return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    return {}


def _save_profiles(profiles):
    PROFILES_PATH.write_text(json.dumps(profiles, indent=2), encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main page."""
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/countries")
async def get_countries():
    """Return the list of countries organized by region."""
    return JSONResponse(COUNTRIES_BY_REGION)


@app.post("/api/fetch-ip-blocks")
async def fetch_ip_blocks(request: Request):
    """
    Fetch IP blocks from ipdeny.com for selected country codes.
    Body: {"countries": ["CN", "RU", ...]}
    """
    body = await request.json()
    country_codes = body.get('countries', [])

    if not country_codes:
        raise HTTPException(status_code=400, detail="No countries selected")

    ip_blocks = {}
    errors = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for code in country_codes:
            code_lower = code.lower()
            url = f"{IPDENY_BASE_URL}/{code_lower}-aggregated.zone"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    lines = resp.text.strip().split('\n')
                    # Filter valid CIDR blocks
                    blocks = []
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            try:
                                ipaddress.ip_network(line, strict=False)
                                blocks.append(line)
                            except ValueError:
                                continue
                    ip_blocks[code] = blocks
                else:
                    errors.append(f"{code}: HTTP {resp.status_code}")
            except Exception as e:
                errors.append(f"{code}: {str(e)}")

    return JSONResponse({
        "ip_blocks": ip_blocks,
        "errors": errors,
        "total_blocks": sum(len(v) for v in ip_blocks.values())
    })


@app.post("/api/generate-rules")
async def generate_rules(request: Request):
    """
    Generate ZFW filter policy rules from IP blocks.
    Body: {"countries": ["CN", "RU"], "ip_blocks": {"CN": [...], "RU": [...]}}
    """
    body = await request.json()
    country_codes = body.get('countries', [])
    ip_blocks = body.get('ip_blocks', {})

    if not country_codes or not ip_blocks:
        raise HTTPException(status_code=400, detail="No countries or IP blocks provided")

    config = generate_zfw_filter_policy(country_codes, ip_blocks)

    # Build a summary for display
    summary = {
        'policy_name': 'GeoBlock-Policy',
        'total_rules': len(country_codes),
        'total_ip_blocks': sum(len(ip_blocks.get(c, [])) for c in country_codes),
        'countries': [
            {
                'code': c,
                'name': _get_country_name(c),
                'block_count': len(ip_blocks.get(c, []))
            }
            for c in country_codes
        ]
    }

    return JSONResponse({
        "config": config,
        "summary": summary
    })


@app.get("/api/groups")
async def get_groups():
    """Fetch all groups from NCM across all accounts."""
    def _fetch():
        client = _build_client()
        # Get all groups visible to this API key (no account filter = all)
        all_groups = client.get_groups(limit='all')
        # Get accounts for name lookup
        accounts = client.get_accounts(limit='all')
        return all_groups, accounts

    loop = asyncio.get_event_loop()
    try:
        groups, accounts = await loop.run_in_executor(None, _fetch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Build account name lookup
    account_map = {}
    for a in accounts:
        account_map[str(a['id'])] = a.get('name', '')
        # Also map by resource_url
        res_url = a.get('resource_url', '')
        if res_url:
            account_map[res_url] = a.get('name', '')

    # Return simplified group list with account info
    result = []
    for g in groups:
        # Extract account ID from account URL
        account_url = g.get('account', '')
        account_id = ''
        account_name = ''
        if account_url:
            # Try direct lookup first
            account_name = account_map.get(account_url, '')
            # Fall back to ID extraction
            parts = str(account_url).rstrip('/').split('/')
            account_id = parts[-1] if parts else ''
            if not account_name:
                account_name = account_map.get(account_id, '')

        result.append({
            'id': g.get('id'),
            'name': g.get('name', 'Unknown'),
            'product': g.get('product_name', g.get('product', '')),
            'device_count': g.get('device_count', 0),
            'account_name': account_name,
            'account_id': account_id
        })

    return JSONResponse(result)


@app.post("/api/push-config")
async def push_config(request: Request):
    """
    Push ZFW configuration to selected groups.
    Body: {"group_ids": [123, 456], "config": {...}}
    """
    body = await request.json()
    group_ids = body.get('group_ids', [])
    config = body.get('config', {})

    if not group_ids:
        raise HTTPException(status_code=400, detail="No groups selected")
    if not config:
        raise HTTPException(status_code=400, detail="No configuration provided")

    def _push():
        client = _build_client()
        results = []
        for group_id in group_ids:
            try:
                result = client.patch_group_configuration(group_id, config)
                results.append({
                    'group_id': group_id,
                    'status': 'success',
                    'detail': str(result) if result else 'OK'
                })
            except Exception as e:
                results.append({
                    'group_id': group_id,
                    'status': 'error',
                    'detail': str(e)
                })
        return results

    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(None, _push)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse({"results": results})


# --- Profile Management ---

@app.get("/api/profiles")
async def list_profiles():
    """List saved credential profiles."""
    profiles = _load_profiles()
    return JSONResponse(list(profiles.keys()))


@app.post("/api/profiles")
async def save_profile(request: Request):
    """Save a credential profile."""
    body = await request.json()
    name = body.get('name', '').strip()
    if not name:
        raise HTTPException(status_code=400, detail="Profile name required")
    profiles = _load_profiles()
    profiles[name] = {
        'X_CP_API_ID': body.get('X_CP_API_ID', ''),
        'X_CP_API_KEY': body.get('X_CP_API_KEY', ''),
        'X_ECM_API_ID': body.get('X_ECM_API_ID', ''),
        'X_ECM_API_KEY': body.get('X_ECM_API_KEY', ''),
    }
    _save_profiles(profiles)
    return JSONResponse({"status": "saved"})


@app.post("/api/profiles/load")
async def load_profile(request: Request):
    """Load a credential profile into environment."""
    body = await request.json()
    name = body.get('name', '').strip()
    profiles = _load_profiles()
    if name not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = profiles[name]
    for key, value in profile.items():
        if value:
            os.environ[key] = value
    return JSONResponse({"status": "loaded"})


@app.delete("/api/profiles/{name}")
async def delete_profile(name: str):
    """Delete a credential profile."""
    profiles = _load_profiles()
    if name in profiles:
        del profiles[name]
        _save_profiles(profiles)
    return JSONResponse({"status": "deleted"})


@app.get("/api/profiles/current")
async def current_credentials():
    """Return current environment credentials (masked)."""
    return JSONResponse({
        'X_CP_API_ID': os.environ.get('X_CP_API_ID', ''),
        'X_CP_API_KEY': '***' if os.environ.get('X_CP_API_KEY') else '',
        'X_ECM_API_ID': os.environ.get('X_ECM_API_ID', ''),
        'X_ECM_API_KEY': '***' if os.environ.get('X_ECM_API_KEY') else '',
    })


@app.post("/api/credentials/apply")
async def apply_credentials(request: Request):
    """Apply credentials to environment without saving."""
    body = await request.json()
    for key in ['X_CP_API_ID', 'X_CP_API_KEY', 'X_ECM_API_ID', 'X_ECM_API_KEY']:
        value = body.get(key, '')
        if value:
            os.environ[key] = value
    return JSONResponse({"status": "applied"})


if __name__ == "__main__":
    print("=" * 60)
    print("Geo IP Blocker")
    print("=" * 60)
    print(f"Server running at: http://localhost:{PORT}")
    # Report credential status
    creds = get_api_keys_from_env()
    has_creds = all([creds.get('X-CP-API-ID'), creds.get('X-CP-API-KEY'),
                     creds.get('X-ECM-API-ID'), creds.get('X-ECM-API-KEY')])
    if has_creds:
        print(f"API credentials: loaded from environment")
    else:
        missing = [k.replace('X-', 'X_').replace('-', '_') for k, v in creds.items() if not v and k != 'token']
        print(f"API credentials: MISSING — {', '.join(missing)}")
        print("  Set env vars or use the Settings panel (gear icon) in the UI")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=PORT)
