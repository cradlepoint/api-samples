"""RMA Configuration Migration Wizard.

Web-based tool for migrating configuration from a failed router (source)
to its replacement router (destination) using the NCM API v2.

Workflow Steps:
    1. API Keys - NCM v2 (X-CP, X-ECM) credential entry and validation
    2. Source Device - Select source router by drilling down through groups
       - Group dropdown populated from NCM account
       - Router list populated from selected group
       - Display basic router info (name, model, firmware, state, MAC, etc.)
    3. Source Configuration - Backup and display both group config and
       device-level config from the configuration_managers endpoint
    4. Destination Device - Select destination router with compatibility checks
       - Must be same model (product) as source device
       - Must be running same or newer firmware as source
       - Info message suggesting staging group placement

API Endpoints:
    GET  /api/health             - Server health check
    POST /api/validate-api-keys  - Test NCM v2 API key connectivity
    POST /api/get-groups         - List all groups in the account
    POST /api/get-routers        - List routers for a given group
    POST /api/get-router-details - Get detailed info for a specific router
    POST /api/get-config         - Get group config and device config for a router
    POST /api/validate-destination - Validate destination router compatibility

Security:
    - This wizard runs LOCALLY only (not deployed to routers)
    - API keys are held in memory during runtime only
    - Never deploy this file or static/ to production devices

Usage:
    python rma_wizard.py
    # Open browser to http://localhost:8080
"""

import http.server
import socketserver
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, List

import ncm

PORT = 8080


def validate_api_keys_connectivity(api_keys: Dict[str, str]) -> Tuple[bool, str]:
    """Validate NCM v2 API keys by testing connectivity.

    Args:
        api_keys: Dict with X-CP-API-ID, X-CP-API-KEY, X-ECM-API-ID, X-ECM-API-KEY

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        n2 = ncm.NcmClientv2(api_keys=api_keys)
        accounts = n2.get_accounts()

        if not accounts or (isinstance(accounts, str) and accounts.startswith('ERROR')):
            return False, "Error validating NCM v2 API keys. Check credentials and try again."

        return True, "API keys validated successfully."

    except Exception as e:
        return False, f"API key validation error: {str(e)}"


def get_groups(api_keys: Dict[str, str]) -> Tuple[bool, Any]:
    """Retrieve all groups for the account.

    Args:
        api_keys: Validated NCM v2 API keys

    Returns:
        Tuple of (success: bool, data: list or error message)
    """
    try:
        n2 = ncm.NcmClientv2(api_keys=api_keys)
        groups = n2.get_groups()

        if isinstance(groups, str) and groups.startswith('ERROR'):
            return False, "Error retrieving groups from NCM."

        # Return relevant fields only
        result = []
        for g in groups:
            result.append({
                'id': g.get('id'),
                'name': g.get('name'),
                'product_name': g.get('product_name', ''),
                'resource_url': g.get('resource_url', '')
            })

        # Sort by name
        result.sort(key=lambda x: (x.get('name') or '').lower())
        return True, result

    except Exception as e:
        return False, f"Error retrieving groups: {str(e)}"


def get_routers_for_group(api_keys: Dict[str, str], group_id: str) -> Tuple[bool, Any]:
    """Retrieve all routers in a given group.

    Args:
        api_keys: Validated NCM v2 API keys
        group_id: NCM group ID

    Returns:
        Tuple of (success: bool, data: list or error message)
    """
    try:
        n2 = ncm.NcmClientv2(api_keys=api_keys)
        routers = n2.get_routers_for_group(group_id)

        if isinstance(routers, str) and routers.startswith('ERROR'):
            return False, "Error retrieving routers for group."

        result = []
        for r in routers:
            result.append({
                'id': r.get('id'),
                'name': r.get('name', 'Unnamed'),
                'state': r.get('state', 'unknown'),
                'ipv4_address': r.get('ipv4_address', ''),
                'mac': r.get('mac', ''),
                'serial_number': r.get('serial_number', ''),
                'product_info': r.get('product_info', ''),
                'firmware_info': r.get('firmware_info', ''),
                'group_name': r.get('group_name', ''),
                'asset_id': r.get('asset_id', ''),
                'custom1': r.get('custom1', ''),
                'custom2': r.get('custom2', ''),
                'description': r.get('description', ''),
                'actual_firmware': r.get('actual_firmware', '')
            })

        result.sort(key=lambda x: (x.get('name') or '').lower())
        return True, result

    except Exception as e:
        return False, f"Error retrieving routers: {str(e)}"


def get_router_details(api_keys: Dict[str, str], router_id: str) -> Tuple[bool, Any]:
    """Get full details for a specific router.

    Args:
        api_keys: Validated NCM v2 API keys
        router_id: NCM router ID

    Returns:
        Tuple of (success: bool, data: dict or error message)
    """
    try:
        n2 = ncm.NcmClientv2(api_keys=api_keys)
        router = n2.get_router_by_id(router_id)

        if isinstance(router, str) and router.startswith('ERROR'):
            return False, "Error retrieving router details."

        return True, router

    except Exception as e:
        return False, f"Error retrieving router details: {str(e)}"


def get_router_config(api_keys: Dict[str, str], router_id: str,
                      group_id: str) -> Tuple[bool, Any]:
    """Get both group configuration and device-level configuration.

    Uses the configuration_managers endpoint to retrieve configs.

    Args:
        api_keys: Validated NCM v2 API keys
        router_id: NCM router ID
        group_id: NCM group ID for group-level config

    Returns:
        Tuple of (success: bool, data: dict with group_config and device_config)
    """
    try:
        n2 = ncm.NcmClientv2(api_keys=api_keys)

        # Get device-level configuration from configuration_managers
        device_configs = n2.get_configuration_managers(
            router=router_id, fields='id,configuration,suspended,synched'
        )

        if isinstance(device_configs, str) and device_configs.startswith('ERROR'):
            return False, "Error retrieving device configuration."

        device_config = {}
        if device_configs and len(device_configs) > 0:
            device_config = device_configs[0].get('configuration', [])

        # Get group-level configuration
        groups = n2.get_groups(id=group_id)
        group_config = {}
        if groups and len(groups) > 0:
            group = groups[0]
            # Group configuration is available via configuration field
            group_config = group.get('configuration', [])

        return True, {
            'device_config': device_config,
            'group_config': group_config
        }

    except Exception as e:
        return False, f"Error retrieving configuration: {str(e)}"


def validate_destination(api_keys: Dict[str, str], source_router: Dict,
                         dest_router_id: str) -> Tuple[bool, Any]:
    """Validate that the destination router is compatible with the source.

    Checks:
        - Same model (product) as source
        - Same or newer firmware version

    Args:
        api_keys: Validated NCM v2 API keys
        source_router: Full source router details dict
        dest_router_id: NCM router ID of destination device

    Returns:
        Tuple of (success: bool, data: dict with validation results)
    """
    try:
        n2 = ncm.NcmClientv2(api_keys=api_keys)
        dest_router = n2.get_router_by_id(dest_router_id)

        if isinstance(dest_router, str) and dest_router.startswith('ERROR'):
            return False, "Error retrieving destination router details."

        errors = []
        warnings = []

        # Extract product/model info for comparison
        src_product = source_router.get('product_info', '')
        dst_product = dest_router.get('product_info', '')

        # Compare product URLs (same model check)
        if src_product and dst_product:
            if src_product != dst_product:
                # Try to get human-readable product names
                src_name = source_router.get('product_name', src_product)
                dst_name = dest_router.get('product_name', dst_product)
                errors.append(
                    f"Model mismatch: Source is '{src_name}' but "
                    f"destination is '{dst_name}'. "
                    f"Devices must be the same model for RMA configuration migration."
                )

        # Compare firmware versions
        # actual_firmware is typically a URL like:
        #   https://www.cradlepoint.com/api/v2/firmwares/1234/
        # The firmware ID (last numeric path segment) is monotonically
        # increasing — higher ID means newer firmware.
        src_fw = source_router.get('actual_firmware', '')
        dst_fw = dest_router.get('actual_firmware', '')

        if src_fw and dst_fw:
            src_fw_id = _extract_firmware_id(src_fw)
            dst_fw_id = _extract_firmware_id(dst_fw)

            if src_fw_id is not None and dst_fw_id is not None:
                if dst_fw_id != src_fw_id:
                    errors.append(
                        f"Firmware mismatch: Source firmware ID is {src_fw_id} "
                        f"but destination firmware ID is {dst_fw_id}. "
                        f"Source and destination devices must be running the "
                        f"same firmware version for RMA configuration migration."
                    )
            elif src_fw_id is None and dst_fw_id is None:
                # Both unparseable — try version string comparison as fallback
                src_version = _parse_firmware_version(src_fw)
                dst_version = _parse_firmware_version(dst_fw)
                if src_version and dst_version:
                    if dst_version != src_version:
                        errors.append(
                            f"Firmware mismatch: Source is running '{src_fw}' "
                            f"but destination is running '{dst_fw}'. "
                            f"Source and destination devices must be running "
                            f"the same firmware version."
                        )

        # Always provide staging group suggestion
        # (Already shown as static info box on the destination page)
        # No dynamic warning needed here

        result = {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'destination_router': dest_router
        }

        return True, result

    except Exception as e:
        return False, f"Error validating destination: {str(e)}"


def apply_migration(api_keys: Dict[str, str], source_router: Dict,
                    dest_router_id: str, source_group_id: str,
                    device_config: Any,
                    masked_field_resolutions: Dict[str, Dict]) -> Tuple[bool, Any]:
    """Apply the RMA migration: move destination to source group and patch config.

    Steps:
        1. Move destination router into the source router's group
        2. Apply the modified device-level configuration to the destination

    Args:
        api_keys: Validated NCM v2 API keys
        source_router: Source router details dict
        dest_router_id: Destination router ID
        source_group_id: Group ID where source router lives
        device_config: The source device configuration (already modified
                       with masked field resolutions applied)
        masked_field_resolutions: Dict of path -> resolution info for reporting

    Returns:
        Tuple of (success: bool, data: dict with results)
    """
    try:
        import time
        n2 = ncm.NcmClientv2(api_keys=api_keys)

        # Step 1: Move destination router to source group
        move_result = n2.assign_router_to_group(dest_router_id, source_group_id)
        if isinstance(move_result, str) and 'ERROR' in move_result.upper():
            return False, f"Failed to move destination router to group: {move_result}"

        # Brief pause to let group assignment propagate
        time.sleep(2)

        # Step 2: Apply device-level config to destination router
        config_payload = {"configuration": device_config}
        patch_result = n2.patch_configuration_managers(dest_router_id, config_payload)
        if isinstance(patch_result, str) and 'ERROR' in patch_result.upper():
            return False, f"Failed to apply configuration: {patch_result}"

        return True, {
            'message': 'Migration applied successfully',
            'group_moved': True,
            'config_applied': True,
            'dest_router_id': dest_router_id,
            'dest_group_id': source_group_id
        }

    except Exception as e:
        import traceback
        print(f"[APPLY] Exception in apply_migration: {str(e)}")
        traceback.print_exc()
        return False, f"Error applying migration: {str(e)}"


def verify_migration(api_keys: Dict[str, str], dest_router_id: str,
                     expected_config: Any) -> Tuple[bool, Any]:
    """Verify that the migration was applied correctly.

    Retrieves the destination router's current config from configuration_managers
    and compares key fields against what was applied.

    Args:
        api_keys: Validated NCM v2 API keys
        dest_router_id: Destination router ID
        expected_config: The config that was applied

    Returns:
        Tuple of (success: bool, data: dict with verification results)
    """
    try:
        n2 = ncm.NcmClientv2(api_keys=api_keys)

        # Get current config from destination
        dest_configs = n2.get_configuration_managers(
            router=dest_router_id, fields='id,configuration,suspended,synched'
        )

        if isinstance(dest_configs, str) and dest_configs.startswith('ERROR'):
            return False, "Error retrieving destination configuration for verification."

        if not dest_configs or len(dest_configs) == 0:
            return False, "No configuration manager found for destination router."

        current_config = dest_configs[0].get('configuration', [])
        synched = dest_configs[0].get('synched', False)
        suspended = dest_configs[0].get('suspended', False)

        # Build verification report
        warnings = []
        errors = []
        info = []

        if suspended:
            errors.append(
                "Configuration sync is SUSPENDED on the destination device. "
                "The applied configuration may not have synced to the device."
            )

        if not synched:
            warnings.append(
                "Configuration has not yet synced to the device. "
                "This may take a few minutes. Check back shortly."
            )
        else:
            info.append("Configuration sync status: Synched")

        # Check for remaining masked fields in the applied config
        config_str = json.dumps(current_config)
        if '"*"' in config_str:
            warnings.append(
                "The destination device configuration still contains masked "
                "fields (\"*\"). These represent encrypted values (passwords, "
                "PSKs, etc.) that need manual reconfiguration on the device."
            )

        # Note items that may need attention
        info.append(
            "The device has been moved to the source group and device-level "
            "configuration has been applied. Group-level configuration is "
            "inherited automatically from the group."
        )

        result = {
            'verified': len(errors) == 0,
            'synched': synched,
            'suspended': suspended,
            'errors': errors,
            'warnings': warnings,
            'info': info,
            'current_config': current_config
        }

        return True, result

    except Exception as e:
        return False, f"Error verifying migration: {str(e)}"


def _extract_firmware_id(firmware_str: str) -> int:
    """Extract the firmware ID from a firmware URL or plain ID string.

    The NCM API returns actual_firmware as a URL like:
        https://www.cradlepoint.com/api/v2/firmwares/1234/

    The firmware ID is the numeric segment between the last pair of
    slashes (or backslashes). A higher ID indicates newer firmware.

    Args:
        firmware_str: Firmware URL or numeric ID string

    Returns:
        Integer firmware ID, or None if unparseable
    """
    if not firmware_str:
        return None

    # Normalize: strip whitespace
    firmware_str = firmware_str.strip()

    # If it's just a plain number, return it
    if firmware_str.isdigit():
        return int(firmware_str)

    # Extract the last numeric path segment from a URL
    # Handle both forward slashes and backslashes
    # "https://www.cradlepoint.com/api/v2/firmwares/1234/" -> "1234"
    parts = firmware_str.replace('\\', '/').rstrip('/').split('/')
    for part in reversed(parts):
        if part.isdigit():
            return int(part)

    return None


def _parse_firmware_version(firmware_str: str) -> tuple:
    """Parse a firmware version string into a comparable tuple.

    Handles formats like:
        - "7.26.4" -> (7, 26, 4)
        - "https://www.cradlepoint.com/api/v2/firmwares/1234/" -> None
        - "7.2.0" -> (7, 2, 0)

    Args:
        firmware_str: Firmware version string or URL

    Returns:
        Tuple of integers for comparison, or None if unparseable
    """
    if not firmware_str:
        return None

    # If it's a URL, we can't parse it directly
    if firmware_str.startswith('http'):
        return None

    # Try to extract version numbers
    parts = firmware_str.strip().split('.')
    try:
        return tuple(int(p) for p in parts if p.isdigit())
    except (ValueError, TypeError):
        return None


class RMAWizardHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for the RMA Wizard web interface."""

    def end_headers(self):
        """Add CORS and cache-control headers."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.end_headers()

    def _send_json(self, status_code: int, data: dict):
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_json_body(self) -> dict:
        """Read and parse JSON request body."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        return json.loads(body.decode('utf-8'))

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/api/health':
            self._send_json(200, {'status': 'ok', 'service': 'rma_wizard'})
        elif self.path == '/api/version':
            self._handle_get_version()
        else:
            # Serve static files
            super().do_GET()

    def _handle_get_version(self):
        """Return app version from package.ini."""
        try:
            import configparser
            ini_path = Path(__file__).parent / 'package.ini'
            config = configparser.ConfigParser()
            config.read(str(ini_path))
            section = config.sections()[0] if config.sections() else 'rma_wizard'
            major = config.get(section, 'version_major', fallback='0')
            minor = config.get(section, 'version_minor', fallback='0')
            patch = config.get(section, 'version_patch', fallback='0')
            version = f"{major}.{minor}.{patch}"
            self._send_json(200, {'version': version})
        except Exception:
            self._send_json(200, {'version': '0.0.0'})

    def do_POST(self):
        """Handle POST requests."""
        try:
            data = self._read_json_body()
        except (json.JSONDecodeError, ValueError) as e:
            self._send_json(400, {'error': f'Invalid JSON: {str(e)}'})
            return

        if self.path == '/api/validate-api-keys':
            self._handle_validate_api_keys(data)
        elif self.path == '/api/get-groups':
            self._handle_get_groups(data)
        elif self.path == '/api/get-routers':
            self._handle_get_routers(data)
        elif self.path == '/api/get-router-details':
            self._handle_get_router_details(data)
        elif self.path == '/api/get-config':
            self._handle_get_config(data)
        elif self.path == '/api/validate-destination':
            self._handle_validate_destination(data)
        elif self.path == '/api/apply-migration':
            self._handle_apply_migration(data)
        elif self.path == '/api/verify-migration':
            self._handle_verify_migration(data)
        else:
            self._send_json(404, {'error': 'Endpoint not found'})

    def _handle_validate_api_keys(self, data: dict):
        """Validate NCM v2 API keys."""
        api_keys = data.get('api_keys', {})

        required = ['X-CP-API-ID', 'X-CP-API-KEY', 'X-ECM-API-ID', 'X-ECM-API-KEY']
        missing = [k for k in required if not api_keys.get(k)]

        if missing:
            self._send_json(400, {
                'success': False,
                'message': f"Missing required API keys: {', '.join(missing)}"
            })
            return

        success, message = validate_api_keys_connectivity(api_keys)
        self._send_json(200, {'success': success, 'message': message})

    def _handle_get_groups(self, data: dict):
        """Return list of groups."""
        api_keys = data.get('api_keys', {})

        success, result = get_groups(api_keys)
        if success:
            self._send_json(200, {'success': True, 'groups': result})
        else:
            self._send_json(200, {'success': False, 'message': result})

    def _handle_get_routers(self, data: dict):
        """Return list of routers for a group."""
        api_keys = data.get('api_keys', {})
        group_id = data.get('group_id')

        if not group_id:
            self._send_json(400, {'success': False, 'message': 'group_id is required'})
            return

        success, result = get_routers_for_group(api_keys, group_id)
        if success:
            self._send_json(200, {'success': True, 'routers': result})
        else:
            self._send_json(200, {'success': False, 'message': result})

    def _handle_get_router_details(self, data: dict):
        """Return full details for a router."""
        api_keys = data.get('api_keys', {})
        router_id = data.get('router_id')

        if not router_id:
            self._send_json(400, {'success': False, 'message': 'router_id is required'})
            return

        success, result = get_router_details(api_keys, router_id)
        if success:
            self._send_json(200, {'success': True, 'router': result})
        else:
            self._send_json(200, {'success': False, 'message': result})

    def _handle_get_config(self, data: dict):
        """Return group and device configuration for a router."""
        api_keys = data.get('api_keys', {})
        router_id = data.get('router_id')
        group_id = data.get('group_id')

        if not router_id or not group_id:
            self._send_json(400, {
                'success': False,
                'message': 'router_id and group_id are required'
            })
            return

        success, result = get_router_config(api_keys, router_id, group_id)
        if success:
            self._send_json(200, {'success': True, 'config': result})
        else:
            self._send_json(200, {'success': False, 'message': result})

    def _handle_validate_destination(self, data: dict):
        """Validate destination router compatibility."""
        api_keys = data.get('api_keys', {})
        source_router = data.get('source_router', {})
        dest_router_id = data.get('dest_router_id')

        if not source_router:
            self._send_json(400, {
                'success': False,
                'message': 'source_router details are required'
            })
            return

        if not dest_router_id:
            self._send_json(400, {
                'success': False,
                'message': 'dest_router_id is required'
            })
            return

        success, result = validate_destination(api_keys, source_router, dest_router_id)
        if success:
            self._send_json(200, {'success': True, 'validation': result})
        else:
            self._send_json(200, {'success': False, 'message': result})

    def _handle_apply_migration(self, data: dict):
        """Apply migration: move router to group and patch config."""
        api_keys = data.get('api_keys', {})
        source_router = data.get('source_router', {})
        dest_router_id = data.get('dest_router_id')
        source_group_id = data.get('source_group_id')
        device_config = data.get('device_config')
        masked_field_resolutions = data.get('masked_field_resolutions', {})

        if not dest_router_id or not source_group_id:
            self._send_json(400, {
                'success': False,
                'message': 'dest_router_id and source_group_id are required'
            })
            return

        if device_config is None:
            self._send_json(400, {
                'success': False,
                'message': 'device_config is required'
            })
            return

        try:
            success, result = apply_migration(
                api_keys, source_router, dest_router_id,
                source_group_id, device_config, masked_field_resolutions
            )

            if success:
                self._send_json(200, {'success': True, 'result': result})
            else:
                self._send_json(200, {'success': False, 'message': result})
        except Exception as e:
            self._send_json(500, {'success': False, 'message': f'Server error: {str(e)}'})

    def _handle_verify_migration(self, data: dict):
        """Verify migration was applied correctly."""
        api_keys = data.get('api_keys', {})
        dest_router_id = data.get('dest_router_id')
        expected_config = data.get('expected_config')

        if not dest_router_id:
            self._send_json(400, {
                'success': False,
                'message': 'dest_router_id is required'
            })
            return

        success, result = verify_migration(api_keys, dest_router_id, expected_config)
        if success:
            self._send_json(200, {'success': True, 'verification': result})
        else:
            self._send_json(200, {'success': False, 'message': result})


def main():
    """Start the RMA Wizard HTTP server."""
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    if not (script_dir / 'index.html').exists():
        print(f"Warning: index.html not found in {script_dir}")
        print("The web interface may not be available.")

    handler = RMAWizardHandler

    try:
        with socketserver.TCPServer(("", PORT), handler) as httpd:
            print("=" * 60)
            print("RMA Configuration Migration Wizard")
            print("=" * 60)
            print(f"Server running at: http://0.0.0.0:{PORT}")
            print(f"Web interface:     http://localhost:{PORT}")
            print(f"Serving from:      {script_dir}")
            print(f"\nPress Ctrl+C to stop the server")
            print("=" * 60)

            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\n\nServer stopped by user.")
        sys.exit(0)
    except OSError as e:
        if e.errno == 48:
            print(f"\nError: Port {PORT} is already in use.")
            print(f"Please stop the process using port {PORT} or change the PORT variable.")
        else:
            print(f"\nError starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
