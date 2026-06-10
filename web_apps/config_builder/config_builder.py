#!/usr/bin/env python3
"""
Config Builder - A web-based tool for building Cradlepoint JSON configurations
from paired Base/Full templates with per-site variable substitution.

Features:
- Config Templates: named pairs of Base + Full JSON configs with {{variable|type}} placeholders
- Build: select a template, create or load a site, fill in variables, download .bin configs
- Saved Sites: manage CSV site inventories

No NCM API calls are made — this is a purely local tool.
"""

import base64
import csv
import io
import json
import os
import re
import zlib
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

PORT = 8100

# Storage directories (relative to script dir)
TEMPLATES_DIR = 'templates'
SITES_DIR = 'sites'
OUTPUT_DIR = 'output'
ROUTER_MODELS_FILE = 'router_models.csv'

# Supported variable types
VALID_TYPES = {'string', 'integer', 'float', 'boolean', 'ipv4', 'ipv6', 'cidr', 'mac'}


def parse_variables(content):
    """
    Parse {{name}} or {{name|type}} placeholders from content.
    Returns a list of dicts: [{'name': 'hostname', 'type': 'string'}, ...]
    Deduplicates by name, preserving first occurrence order.
    """
    raw_matches = re.findall(r'\{\{([^}]+)\}\}', content)
    seen = set()
    variables = []
    for raw in raw_matches:
        raw = raw.strip()
        if '|' in raw:
            parts = raw.split('|', 1)
            name = parts[0].strip()
            vtype = parts[1].strip().lower()
            if vtype not in VALID_TYPES:
                vtype = 'string'
        else:
            name = raw
            vtype = 'string'
        if name not in seen:
            seen.add(name)
            variables.append({'name': name, 'type': vtype})
    return sorted(variables, key=lambda v: v['name'])


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def load_router_models():
    """Load router models from CSV file."""
    filepath = os.path.join(get_script_dir(), ROUTER_MODELS_FILE)
    models = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'model' in row and row['model'].strip():
                    models.append(row['model'].strip())
    return models if models else ['E3000']


class ConfigBuilderHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for the Config Builder interface."""

    def __init__(self, *args, **kwargs):
        script_dir = get_script_dir()
        self.templates_dir = os.path.join(script_dir, TEMPLATES_DIR)
        self.sites_dir = os.path.join(script_dir, SITES_DIR)
        self.output_dir = os.path.join(script_dir, OUTPUT_DIR)
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.sites_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        super().__init__(*args, directory=script_dir, **kwargs)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/':
            self.path = '/static/index.html'
            super().do_GET()
        elif parsed_path.path == '/api/templates':
            self.handle_list_templates()
        elif parsed_path.path == '/api/sites':
            self.handle_list_sites()
        elif parsed_path.path == '/api/router-models':
            self.handle_get_router_models()
        else:
            super().do_GET()

    def do_POST(self):
        parsed_path = urlparse(self.path)
        routes = {
            '/api/templates/save': self.handle_save_template,
            '/api/templates/load': self.handle_load_template,
            '/api/templates/delete': self.handle_delete_template,
            '/api/templates/decode-bin': self.handle_decode_bin,
            '/api/sites/upload': self.handle_upload_sites,
            '/api/sites/load': self.handle_load_site_file,
            '/api/sites/delete': self.handle_delete_site_file,
            '/api/sites/save-row': self.handle_save_site_row,
            '/api/build/encode-bin': self.handle_encode_bin,
        }
        handler = routes.get(parsed_path.path)
        if handler:
            handler()
        else:
            self.send_error_response('Unknown endpoint')

    # --- Template Endpoints ---

    def handle_list_templates(self):
        """List all saved config templates (each is a Base+Full pair)."""
        templates = []
        if os.path.exists(self.templates_dir):
            for f in sorted(os.listdir(self.templates_dir)):
                if f.endswith('.json'):
                    filepath = os.path.join(self.templates_dir, f)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as fh:
                            manifest = json.load(fh)
                        base_vars = parse_variables(manifest.get('base_content', ''))
                        full_vars = parse_variables(manifest.get('full_content', ''))
                        templates.append({
                            'name': manifest.get('name', f.replace('.json', '')),
                            'filename': f,
                            'base_variables': base_vars,
                            'full_variables': full_vars,
                        })
                    except Exception:
                        continue
        self.send_json_response({'templates': templates})

    def handle_save_template(self):
        """Save a config template (name + base content + full content)."""
        try:
            data = self._read_json_body()
            name = data.get('name', '').strip()
            base_content = data.get('base_content', '')
            full_content = data.get('full_content', '')

            if not name:
                self.send_error_response('Template name is required')
                return
            if not base_content:
                self.send_error_response('Base config content is required')
                return
            if not full_content:
                self.send_error_response('Full config content is required')
                return

            # Validate JSON for both
            for label, content in [('Base', base_content), ('Full', full_content)]:
                test_content = re.sub(r'"\{\{[^}]+\}\}"', '"__placeholder__"', content)
                test_content = re.sub(r'\{\{[^}]+\}\}', '"__placeholder__"', test_content)
                try:
                    json.loads(test_content, strict=False)
                except json.JSONDecodeError as e:
                    self.send_error_response(f'{label} config invalid JSON: {e}')
                    return

            # Save manifest
            filename = re.sub(r'[^a-zA-Z0-9_\-\s]', '', name).strip().replace(' ', '_') + '.json'
            manifest = {
                'name': name,
                'base_content': base_content,
                'full_content': full_content,
            }
            filepath = os.path.join(self.templates_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)

            base_vars = parse_variables(base_content)
            full_vars = parse_variables(full_content)

            self.send_json_response({
                'success': True,
                'name': name,
                'filename': filename,
                'base_variables': base_vars,
                'full_variables': full_vars,
            })
        except Exception as e:
            self.send_error_response(str(e))

    def handle_load_template(self):
        """Load a config template by filename."""
        try:
            data = self._read_json_body()
            filename = data.get('filename', '')
            if not filename:
                self.send_error_response('Filename is required')
                return

            filepath = os.path.join(self.templates_dir, filename)
            if not os.path.exists(filepath):
                self.send_error_response(f'Not found: {filename}')
                return

            with open(filepath, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            base_vars = parse_variables(manifest.get('base_content', ''))
            full_vars = parse_variables(manifest.get('full_content', ''))

            self.send_json_response({
                'name': manifest.get('name', ''),
                'filename': filename,
                'base_content': manifest.get('base_content', ''),
                'full_content': manifest.get('full_content', ''),
                'base_variables': base_vars,
                'full_variables': full_vars,
            })
        except Exception as e:
            self.send_error_response(str(e))

    def handle_delete_template(self):
        """Delete a config template."""
        try:
            data = self._read_json_body()
            filename = data.get('filename', '')
            if not filename:
                self.send_error_response('Filename is required')
                return

            filepath = os.path.join(self.templates_dir, filename)
            if not os.path.exists(filepath):
                self.send_error_response(f'Not found: {filename}')
                return

            os.remove(filepath)
            self.send_json_response({'success': True})
        except Exception as e:
            self.send_error_response(str(e))

    def handle_decode_bin(self):
        """Decode a zlib/gzip-compressed .bin file to JSON."""
        try:
            data = self._read_json_body()
            bin_base64 = data.get('bin_base64', '')

            if not bin_base64:
                self.send_error_response('bin_base64 is required')
                return

            compressed = base64.b64decode(bin_base64)

            decompressed = None
            for wbits in [15, -15, 31, 47]:
                try:
                    decompressed = zlib.decompress(compressed, wbits)
                    break
                except zlib.error:
                    continue

            if decompressed is None:
                self.send_error_response(
                    'Failed to decompress .bin file: not a valid zlib or gzip compressed file'
                )
                return

            json_str = decompressed.decode('utf-8')
            parsed = json.loads(json_str, strict=False)

            # Extract config portion from Cradlepoint .bin structure
            if isinstance(parsed, list) and len(parsed) > 0:
                first = parsed[0]
                if isinstance(first, dict) and 'config' in first:
                    parsed = first['config']
                elif isinstance(first, dict):
                    first.pop('state', None)
                    parsed = first
            elif isinstance(parsed, dict):
                if 'config' in parsed:
                    parsed = parsed['config']
                else:
                    parsed.pop('state', None)

            pretty = json.dumps(parsed, indent=2)
            self.send_json_response({'content': pretty})
        except json.JSONDecodeError as e:
            self.send_error_response(f'Decompressed content is not valid JSON: {e}')
        except Exception as e:
            self.send_error_response(str(e))

    # --- Site Endpoints ---

    def handle_list_sites(self):
        """List all saved site CSV files."""
        files = []
        if os.path.exists(self.sites_dir):
            for f in sorted(os.listdir(self.sites_dir)):
                if f.endswith('.csv'):
                    filepath = os.path.join(self.sites_dir, f)
                    size = os.path.getsize(filepath)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as fh:
                            reader = csv.reader(fh)
                            headers = next(reader, [])
                            row_count = sum(1 for _ in reader)
                    except Exception:
                        headers = []
                        row_count = 0
                    files.append({
                        'name': f,
                        'size': size,
                        'headers': headers,
                        'row_count': row_count
                    })
        self.send_json_response({'files': files})

    def handle_upload_sites(self):
        """Upload a CSV site file."""
        try:
            data = self._read_json_body()
            name = data.get('name', '').strip()
            content = data.get('content', '')

            if not name:
                self.send_error_response('Name is required')
                return
            if not name.endswith('.csv'):
                name += '.csv'

            try:
                reader = csv.reader(io.StringIO(content))
                headers = next(reader, [])
                if not headers:
                    self.send_error_response('CSV has no headers')
                    return
                rows = list(reader)
            except Exception as e:
                self.send_error_response(f'Invalid CSV: {e}')
                return

            filepath = os.path.join(self.sites_dir, name)
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                f.write(content)

            self.send_json_response({
                'success': True,
                'name': name,
                'headers': headers,
                'row_count': len(rows)
            })
        except Exception as e:
            self.send_error_response(str(e))

    def handle_load_site_file(self):
        """Load a site CSV file and return all rows."""
        try:
            data = self._read_json_body()
            name = data.get('name', '')
            if not name:
                self.send_error_response('Name is required')
                return

            filepath = os.path.join(self.sites_dir, name)
            if not os.path.exists(filepath):
                self.send_error_response(f'Not found: {name}')
                return

            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                rows = list(reader)

            self.send_json_response({
                'name': name,
                'headers': headers,
                'rows': rows
            })
        except Exception as e:
            self.send_error_response(str(e))

    def handle_delete_site_file(self):
        """Delete a site CSV file."""
        try:
            data = self._read_json_body()
            name = data.get('name', '')
            if not name:
                self.send_error_response('Name is required')
                return

            filepath = os.path.join(self.sites_dir, name)
            if not os.path.exists(filepath):
                self.send_error_response(f'Not found: {name}')
                return

            os.remove(filepath)
            self.send_json_response({'success': True})
        except Exception as e:
            self.send_error_response(str(e))

    def handle_save_site_row(self):
        """Save a site row to a CSV file (append or update)."""
        try:
            data = self._read_json_body()
            filename = data.get('filename', '').strip()
            row_data = data.get('row', {})
            row_index = data.get('row_index', None)  # If updating existing row

            if not filename:
                self.send_error_response('Filename is required')
                return
            if not filename.endswith('.csv'):
                filename += '.csv'
            if not row_data:
                self.send_error_response('Row data is required')
                return

            filepath = os.path.join(self.sites_dir, filename)

            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    existing_headers = list(reader.fieldnames or [])
                    existing_rows = list(reader)

                # Merge headers
                all_headers = list(existing_headers)
                for key in row_data.keys():
                    if key not in all_headers:
                        all_headers.append(key)

                if row_index is not None and 0 <= row_index < len(existing_rows):
                    # Update existing row
                    existing_rows[row_index] = row_data
                else:
                    # Append new row
                    existing_rows.append(row_data)

                with open(filepath, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=all_headers)
                    writer.writeheader()
                    for r in existing_rows:
                        writer.writerow(r)
            else:
                # Create new file
                headers = list(row_data.keys())
                with open(filepath, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerow(row_data)

            self.send_json_response({'success': True, 'filename': filename})
        except Exception as e:
            self.send_error_response(str(e))

    # --- Router Models ---

    def handle_get_router_models(self):
        """Return list of router models."""
        models = load_router_models()
        self.send_json_response({'models': models})

    # --- Build Endpoints ---

    def handle_encode_bin(self):
        """Encode JSON config as zlib-compressed .bin (Cradlepoint format)."""
        try:
            data = self._read_json_body()
            json_content = data.get('content', '')

            parsed = json.loads(json_content, strict=False)

            # Wrap in Cradlepoint .bin structure: [{"config": <obj>}, []]
            if isinstance(parsed, list) and len(parsed) >= 1:
                first = parsed[0] if len(parsed) > 0 else {}
                if isinstance(first, dict) and 'config' in first:
                    bin_structure = parsed
                else:
                    bin_structure = [{"config": first}, parsed[1] if len(parsed) > 1 else []]
            elif isinstance(parsed, dict):
                if 'config' in parsed:
                    bin_structure = [parsed, []]
                else:
                    bin_structure = [{"config": parsed}, []]
            else:
                bin_structure = [{"config": parsed}, []]

            compressed = zlib.compress(json.dumps(bin_structure).encode())
            b64 = base64.b64encode(compressed).decode('ascii')
            self.send_json_response({'bin_base64': b64})
        except json.JSONDecodeError as e:
            self.send_error_response(f'Invalid JSON: {e}')
        except Exception as e:
            self.send_error_response(str(e))

    # --- Helpers ---

    def _read_json_body(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        return json.loads(body)

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_response(self, message):
        self.send_response(400)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode('utf-8'))

    def log_message(self, format, *args):
        pass  # Suppress default logging


def main():
    """Main entry point."""
    server = HTTPServer(('0.0.0.0', PORT), ConfigBuilderHandler)
    print(f"Config Builder running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == '__main__':
    main()
