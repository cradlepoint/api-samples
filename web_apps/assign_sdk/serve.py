#!/usr/bin/env python3
"""
Assign SDK App to Groups - Web Application Server

Provides a web UI for selecting an SDK app version and assigning it
to one or more router groups via the NCM API v2 device_app_bindings endpoint.
Logs all assignment results to a datetime-stamped log file.
"""
import os
import sys
import json
import http.server
import socketserver
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from time import sleep
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    import subprocess
    print("\nThe 'requests' package is required but not installed.")
    answer = input("Install it now? [Y/n] ").strip().lower()
    if answer in ('', 'y', 'yes'):
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests'])
        import requests
    else:
        print("Cannot continue without 'requests'. Install with: pip install requests")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Credential Management
# ---------------------------------------------------------------------------

REQUIRED_VARS = [
    ("X_CP_API_ID", "Cradlepoint API ID"),
    ("X_CP_API_KEY", "Cradlepoint API Key"),
    ("X_ECM_API_ID", "ECM API ID"),
    ("X_ECM_API_KEY", "ECM API Key"),
]

_ENV_FILE = Path(__file__).parent / '.env'


def _load_env_file():
    """Load variables from .env file into os.environ (won't overwrite existing)."""
    if not _ENV_FILE.exists():
        return
    with open(_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and not os.environ.get(key):
                os.environ[key] = value


def _save_env_file():
    """Write all required vars from os.environ to .env file."""
    lines = ['# NCM API Credentials (auto-generated)\n']
    for var, _ in REQUIRED_VARS:
        value = os.environ.get(var, '')
        lines.append(f'{var}={value}\n')
    base_url = os.environ.get('CP_BASE_URL')
    if base_url:
        lines.append(f'CP_BASE_URL={base_url}\n')
    with open(_ENV_FILE, 'w') as f:
        f.writelines(lines)


def check_env():
    """Load .env, check required vars, prompt if missing, save to .env."""
    _load_env_file()

    missing = []
    for var, desc in REQUIRED_VARS:
        if not os.environ.get(var):
            missing.append((var, desc))

    if not missing:
        return

    print("\nMissing required API credentials:")
    for var, desc in missing:
        print(f"  {var}  ({desc})")
    print()

    answer = input("Enter them now? [Y/n] ").strip().lower()
    if answer not in ('', 'y', 'yes'):
        print("\nCannot continue without API credentials.")
        print("Set them as environment variables or in .env and try again.")
        sys.exit(1)

    print()
    for var, desc in missing:
        value = input(f"  {desc} ({var}): ").strip()
        if not value:
            print(f"\n  {var} cannot be empty. Exiting.")
            sys.exit(1)
        os.environ[var] = value

    _save_env_file()
    print(f"\n  Credentials saved to .env for next time.\n")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PORT = 9000
BASE_URL = os.environ.get('CP_BASE_URL', 'https://www.cradlepointecm.com/api/v2')
SCRIPT_DIR = Path(__file__).parent.absolute()
LOG_DIR = SCRIPT_DIR / 'logs'

# Placeholders for API keys — if populated here, they take priority over env vars.
# Leave as empty strings to use environment variables instead.
X_CP_API_ID = ""
X_CP_API_KEY = ""
X_ECM_API_ID = ""
X_ECM_API_KEY = ""


def get_headers():
    """Build API headers from placeholders or environment variables."""
    cp_api_id = X_CP_API_ID or os.environ.get('X_CP_API_ID', '')
    cp_api_key = X_CP_API_KEY or os.environ.get('X_CP_API_KEY', '')
    ecm_api_id = X_ECM_API_ID or os.environ.get('X_ECM_API_ID', '')
    ecm_api_key = X_ECM_API_KEY or os.environ.get('X_ECM_API_KEY', '')

    return {
        'X-CP-API-ID': cp_api_id,
        'X-CP-API-KEY': cp_api_key,
        'X-ECM-API-ID': ecm_api_id,
        'X-ECM-API-KEY': ecm_api_key,
        'Content-Type': 'application/json',
    }


# ---------------------------------------------------------------------------
# API Helpers
# ---------------------------------------------------------------------------

def api_get_all(endpoint, params=None):
    """GET all records from a paginated v2 endpoint with retry logic."""
    url = f'{BASE_URL}/{endpoint}/'
    headers = get_headers()
    results = []
    if params is None:
        params = {}
    params.setdefault('limit', 500)
    # Preserve expand param for all pages since next URL may not include it
    expand_value = params.get('expand')
    while url:
        resp = _request_with_retry('GET', url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get('data', []))
        url = data.get('meta', {}).get('next')
        if url:
            # next URL has limit/offset baked in, but may lack expand
            if expand_value and 'expand=' not in url:
                separator = '&' if '?' in url else '?'
                url = f'{url}{separator}expand={expand_value}'
            params = None  # Don't double-add params
    return results


def api_post(endpoint, payload):
    """POST to a v2 endpoint with retry logic."""
    url = f'{BASE_URL}/{endpoint}/'
    headers = get_headers()
    resp = _request_with_retry('POST', url, headers=headers, json=payload)
    return resp


def _request_with_retry(method, url, max_retries=5, backoff=2, **kwargs):
    """Execute an HTTP request with exponential backoff on transient errors."""
    for attempt in range(max_retries):
        resp = requests.request(method, url, **kwargs)
        if resp.status_code in (408, 429, 500, 502, 503, 504):
            wait = backoff ** attempt
            if resp.status_code == 429:
                wait = float(resp.headers.get('Retry-After', wait))
            sleep(wait)
            continue
        return resp
    return resp  # Return last response even if retries exhausted


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def create_log_file():
    """Create a new datetime-stamped log file and return its path."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = LOG_DIR / f'assign_sdk_{timestamp}.log'
    return log_path


def write_log(log_path, message):
    """Append a timestamped message to the log file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_path, 'a') as f:
        f.write(f'[{timestamp}] {message}\n')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_id_from_url(url):
    """Extract the trailing ID from a v2 resource URL like .../accounts/123/."""
    if not url:
        return None
    parts = url.rstrip('/').split('/')
    return parts[-1] if parts else None


# ---------------------------------------------------------------------------
# Request Handler
# ---------------------------------------------------------------------------

class AssignSDKHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for the Assign SDK App web UI."""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/' or path == '/index.html':
            self._serve_file('index.html', 'text/html')
        elif path == '/api/device_apps':
            self._handle_get_device_apps()
        elif path == '/api/groups':
            self._handle_get_groups(parsed)
        elif path == '/api/accounts':
            self._handle_get_accounts()
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/assign':
            self._handle_assign()
        else:
            self.send_error(404)

    def _serve_file(self, filename, content_type):
        """Serve a static file from the script directory."""
        filepath = SCRIPT_DIR / filename
        if not filepath.exists():
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(filepath.read_bytes())

    def _send_json(self, data, status=200):
        """Send a JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _handle_get_device_apps(self):
        """Fetch all device apps and their versions, return combined list."""
        try:
            # Fetch apps, versions, and accounts in parallel
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_apps = executor.submit(api_get_all, 'device_apps')
                future_versions = executor.submit(api_get_all, 'device_app_versions')
                future_accounts = executor.submit(api_get_all, 'accounts')

                apps = future_apps.result()
                versions = future_versions.result()
                accounts = future_accounts.result()

            # Build account lookup: account id (from URL) -> name
            account_lookup = {}
            for acct in accounts:
                acct_id = _extract_id_from_url(acct.get('resource_url', ''))
                if acct_id:
                    account_lookup[acct_id] = acct.get('name', f'Account {acct_id}')

            # Build lookup of app id (string) -> {name, description, account_id}
            app_lookup = {}
            for app in apps:
                app_id = str(app.get('id', ''))
                app_lookup[app_id] = {
                    'name': app.get('name', ''),
                    'description': app.get('description', ''),
                    'account_id': _extract_id_from_url(app.get('account', '')),
                }

            # Build response: each version with its app name, description, and account
            result = []
            for ver in versions:
                app_url = ver.get('app', '')
                # Extract app ID from URL like .../device_apps/83/
                app_id = _extract_id_from_url(app_url)

                app_info = app_lookup.get(app_id, {})
                acct_id = app_info.get('account_id')
                acct_name = account_lookup.get(acct_id, 'Unknown Account') if acct_id else 'Unknown Account'
                result.append({
                    'id': ver.get('id'),
                    'app_name': app_info.get('name', 'Unknown'),
                    'app_description': app_info.get('description', ''),
                    'account_name': acct_name,
                    'app_id': app_id,
                    'version': ver.get('version', 'Unknown'),
                    'resource_url': ver.get('resource_url', ''),
                })

            # Sort hierarchically: account > app name/description > version
            result.sort(key=lambda x: (
                x['account_name'].lower(),
                (x['app_description'] or x['app_name']).lower(),
                x['version'].lower(),
            ))

            self._send_json({'data': result})
        except Exception as e:
            self._send_json({'error': str(e)}, status=500)

    def _handle_get_groups(self, parsed):
        """Fetch all groups with account names, sorted by account > group name."""
        try:
            # expand=account inlines the account object in each group
            groups = api_get_all('groups', params={'expand': 'account'})

            # Debug: print first group's account field type
            if groups:
                print(f"DEBUG: First group account type: {type(groups[0].get('account'))}")
                print(f"DEBUG: First group account value: {str(groups[0].get('account', ''))[:200]}")

            result = []
            for g in groups:
                acct = g.get('account', '')
                if isinstance(acct, dict):
                    acct_name = acct.get('name', f'Account {acct.get("id", "?")}')
                elif isinstance(acct, str):
                    acct_id = _extract_id_from_url(acct)
                    acct_name = f'Account {acct_id}' if acct_id else 'Unknown Account'
                else:
                    acct_name = 'Unknown Account'

                result.append({
                    'id': g.get('id'),
                    'name': g.get('name', f'Group {g.get("id")}'),
                    'account_name': acct_name,
                    'resource_url': g.get('resource_url', ''),
                })

            # Sort hierarchically: account name > group name
            result.sort(key=lambda x: (x['account_name'].lower(), x['name'].lower()))

            self._send_json({'data': result})
        except Exception as e:
            self._send_json({'error': str(e)}, status=500)

    def _handle_get_accounts(self):
        """Fetch account info to get the account URL for bindings."""
        try:
            accounts = api_get_all('accounts')
            result = []
            for a in accounts:
                result.append({
                    'id': a.get('id'),
                    'name': a.get('name', ''),
                    'resource_url': a.get('resource_url', ''),
                })
            self._send_json({'data': result})
        except Exception as e:
            self._send_json({'error': str(e)}, status=500)

    def _handle_assign(self):
        """Assign the selected app version to selected groups."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({'error': 'Invalid JSON'}, status=400)
            return

        app_version_url = payload.get('app_version_url')
        account_url = payload.get('account_url')
        group_ids = payload.get('group_ids', [])

        if not app_version_url or not account_url or not group_ids:
            self._send_json({'error': 'Missing required fields: app_version_url, account_url, group_ids'}, status=400)
            return

        # Create log file for this run
        log_path = create_log_file()
        write_log(log_path, f'Starting assignment run')
        write_log(log_path, f'App Version URL: {app_version_url}')
        write_log(log_path, f'Account URL: {account_url}')
        write_log(log_path, f'Groups to assign: {len(group_ids)}')

        results = []
        for group_id in group_ids:
            group_url = f'{BASE_URL}/groups/{group_id}/'
            binding_payload = {
                'account': account_url,
                'app_version': app_version_url,
                'group': group_url,
            }

            resp = api_post('device_app_bindings', binding_payload)
            if resp.status_code in (200, 201):
                msg = f'SUCCESS: Assigned to group {group_id}'
                results.append({'group_id': group_id, 'status': 'success', 'message': msg})
            else:
                error_detail = resp.text[:200]
                msg = f'FAILED: Group {group_id} - HTTP {resp.status_code}: {error_detail}'
                results.append({'group_id': group_id, 'status': 'error', 'message': msg})

            write_log(log_path, msg)
            print(msg)

        write_log(log_path, f'Assignment run complete. {sum(1 for r in results if r["status"] == "success")}/{len(results)} succeeded.')
        print(f'\nLog file: {log_path}')

        self._send_json({
            'results': results,
            'log_file': str(log_path),
        })

    def log_message(self, format, *args):
        """Suppress default access logs for cleaner output."""
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Main entry point."""
    # Check for API keys - either in placeholders or environment
    if not (X_CP_API_ID and X_CP_API_KEY and X_ECM_API_ID and X_ECM_API_KEY):
        # Placeholders not set, check environment
        check_env()

    os.chdir(SCRIPT_DIR)

    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), AssignSDKHandler) as httpd:
            print("=" * 60)
            print("  Assign SDK App to Groups")
            print("=" * 60)
            print(f"  Server running at: http://localhost:{PORT}")
            print(f"  Log directory:     {LOG_DIR}")
            print(f"\n  Press Ctrl+C to stop the server")
            print("=" * 60)
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        sys.exit(0)
    except OSError as e:
        if e.errno == 48:
            print(f"\nError: Port {PORT} is already in use.")
        else:
            print(f"\nError starting server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
