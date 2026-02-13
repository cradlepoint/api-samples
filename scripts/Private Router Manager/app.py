"""
Private Router Manager - Flask backend
Manages Cradlepoint routers: CSV editor, file deployment (Licenses, NCOS, Configuration, SDK Apps)
"""

import csv
import io
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, request, jsonify, render_template, send_file

NCOS_DEVICE_URL = "https://www.cradlepointecm.com/api/v2/firmwares/?limit=500&version="
NCOS_FIRMWARE_BASE = "https://d251cfg5d9gyuq.cloudfront.net"
APP_ROOT = Path(__file__).parent.resolve()
API_KEYS_FILE = APP_ROOT / "api_keys.json"
CREDENTIALS_CONFIG_FILE = APP_ROOT / "credentials_config.json"

# Disable SSL warnings for isolated networks
requests.packages.urllib3.disable_warnings()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# In-memory CSV store (headers + rows)
csv_data = {"headers": [], "rows": []}

# Deployment type config: folder, endpoint, file extension
DEPLOYMENT_TYPES = {
    "licenses": {"folder": "licenses", "endpoint": "feature", "ext": ".lic"},
    "ncos": {"folder": "NCOS", "endpoint": "fw_upgrade", "ext": ".bin"},
    "configuration": {"folder": "configs", "endpoint": "config_save", "ext": ".bin"},
    "sdk_apps": {"folder": "sdk_apps", "endpoint": "app_upload", "ext": ".tar.gz"},
}


def ensure_folders():
    """Create csv, logs, and all deployment folders if they don't exist."""
    (APP_ROOT / "csv").mkdir(parents=True, exist_ok=True)
    (APP_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    for cfg in DEPLOYMENT_TYPES.values():
        (APP_ROOT / cfg["folder"]).mkdir(parents=True, exist_ok=True)


ensure_folders()


def _get_sshpass_path():
    """Return path to sshpass: bundled macOS binary if available, else 'sshpass' for system PATH."""
    if sys.platform != "darwin":
        return "sshpass"
    arch = platform.machine().lower()
    if arch not in ("arm64", "x86_64"):
        return "sshpass"
    bundled = APP_ROOT / "bin" / "macos" / arch / "sshpass"
    if bundled.exists() and os.access(bundled, os.X_OK):
        return str(bundled)
    return "sshpass"


def find_ip_column(headers):
    """Find ip address or ip_address column (case insensitive)"""
    for i, h in enumerate(headers):
        n = str(h).strip().lower().replace(" ", "_")
        if n in ("ip_address", "ipaddress", "ip") or "ip_address" in n or "ipaddress" in n:
            return i
    return None


def get_router_credentials(router, headers, same_creds, default_user, default_pass):
    """Get username/password for a router row"""
    if same_creds:
        return default_user, default_pass
    user_idx = next((i for i, h in enumerate(headers) if str(h).strip().lower() in ("username", "user")), None)
    pass_idx = next((i for i, h in enumerate(headers) if str(h).strip().lower() in ("password", "pass")), None)
    if user_idx is None or pass_idx is None:
        return None, None
    return (
        str(router[user_idx]).strip() if user_idx < len(router) else "",
        str(router[pass_idx]).strip() if pass_idx < len(router) else "",
    )


def format_uptime(seconds):
    """Format uptime in seconds: <=24h as HH:MM:SS, >24h rounded to nearest # days"""
    try:
        s = int(float(seconds))
    except (TypeError, ValueError):
        return ""
    if s < 0:
        return ""
    if s <= 86400:  # <= 24 hours
        h, r = divmod(s, 3600)
        m, sec = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(sec):02d}"
    days = round(s / 86400)
    return f"{days} day{'s' if days != 1 else ''}"


def get_router_port(router, headers, same_port, default_port):
    """Get port for a router row"""
    if same_port:
        return default_port
    port_idx = next((i for i, h in enumerate(headers) if str(h).strip().lower() == "port"), None)
    if port_idx is None or port_idx >= len(router):
        return default_port
    try:
        return int(str(router[port_idx]).strip()) if router[port_idx] else default_port
    except (ValueError, TypeError):
        return default_port


def push_sdk_app_via_scp(ip, port, username, password, file_path, result_lines):
    """Push SDK app archive to router via SCP to /app_upload. Appends result to result_lines list."""
    app_archive = str(Path(file_path).resolve())

    def log(msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} {msg}"
        result_lines.append(line)
        print(line)

    try:
        if sys.platform == "win32":
            cmd = [
                "pscp.exe",
                "-pw", password,
                "-P", str(port),
                "-batch",
                app_archive,
                f"{username}@{ip}:/app_upload",
            ]
        else:
            sshpass_cmd = _get_sshpass_path()
            cmd = [
                sshpass_cmd, "-p", password,
                "scp", "-O",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "StrictHostKeyChecking=no",
                "-P", str(port),
                app_archive,
                f"{username}@{ip}:/app_upload",
            ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        combined = (out + "\n" + err).lower()
        # Cradlepoint routers close the connection after upload; SCP reports "lost connection" - this is normal and successful
        is_success = result.returncode == 0 or "lost connection" in combined
        if is_success:
            log(f"Successfully pushed to {ip}:{port}")
            if out:
                log(out)
            if err and "lost connection" in combined:
                log("(Connection closed after transfer - normal for Cradlepoint)")
        else:
            log(f"ERROR pushing to {username}@{ip}:/app_upload: {err or out or 'scp failed'}")
    except subprocess.TimeoutExpired:
        log(f"Timeout pushing to {ip}:{port}")
    except FileNotFoundError as e:
        log(f"SCP tool not found. Install sshpass (macOS/Linux: brew install sshpass) or pscp.exe (Windows): {e}")
    except Exception as e:
        log(f"Exception: {e}")


def push_to_router(ip, port, username, password, file_path, action, result_lines):
    """Push file to a single router. Appends result to result_lines list."""
    base = f"http://{ip}:{port}" if ":" not in ip else f"http://{ip}"
    product_url = f"{base}/api/status/product_info"
    system_id_url = f"{base}/api/config/system/system_id"
    deploy_url = f"{base}/{action}"
    auth = (username, password)

    def log(msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} {msg}"
        result_lines.append(line)
        print(line)

    try:
        req = requests.get(product_url, auth=auth, verify=False, timeout=10)
        if req.status_code >= 300:
            log(f"ERROR connecting to {base}: {req.status_code} {req.text}")
            return
        data = req.json().get("data", {})
        sys_req = requests.get(system_id_url, auth=auth, verify=False, timeout=5)
        system_id = sys_req.json().get("data", "unknown") if sys_req.ok else "unknown"
        log(f"Connected to {system_id} at {base}: {data.get('product_name', 'N/A')}")

        with open(file_path, "rb") as f:
            file_data = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            resp = requests.post(deploy_url, files=file_data, auth=auth, verify=False, timeout=120)
        if resp.status_code < 300:
            log(f"Successfully pushed to {system_id}.")
        else:
            log(f"ERROR pushing to {deploy_url}: {resp.status_code} {resp.text}")
    except Exception as e:
        log(f"Exception: {e}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/readme")
def readme():
    """Serve README.md as plain text for help modal"""
    readme_path = Path(__file__).parent / "README.md"
    if not readme_path.exists():
        return "", 404
    try:
        return readme_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/plain; charset=utf-8"}
    except IOError:
        return "", 500


@app.route("/api/config/credentials", methods=["GET", "POST"])
def credentials_config():
    """Get or save username, password, port, last_file to file"""
    if request.method == "GET":
        if not CREDENTIALS_CONFIG_FILE.exists():
            return jsonify({"username": "", "password": "", "port": 8080, "last_file": ""})
        try:
            with open(CREDENTIALS_CONFIG_FILE, encoding="utf-8") as f:
                cfg = json.load(f)
            return jsonify({
                "username": cfg.get("username", ""),
                "password": cfg.get("password", ""),
                "port": int(cfg.get("port", 8080)),
                "last_file": cfg.get("last_file", ""),
            })
        except (json.JSONDecodeError, IOError):
            return jsonify({"username": "", "password": "", "port": 8080, "last_file": ""})
    data = request.get_json() or {}
    cfg = {
        "username": data.get("username", ""),
        "password": data.get("password", ""),
        "port": int(data.get("port", 8080)),
        "last_file": data.get("last_file", ""),
    }
    with open(CREDENTIALS_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    return jsonify({"ok": True})


@app.route("/api/csv/list")
def csv_list():
    """List CSV files in the csv folder"""
    ensure_folders()
    files = []
    csv_dir = APP_ROOT / "csv"
    if csv_dir.exists():
        for f in sorted(csv_dir.iterdir()):
            if f.is_file() and f.suffix.lower() == ".csv":
                files.append({"name": f.name})
    return jsonify({"files": files})


@app.route("/api/csv/open")
def csv_open():
    """Load a CSV file from the csv folder"""
    filename = request.args.get("filename", "").strip()
    if not filename or not filename.lower().endswith(".csv"):
        return jsonify({"error": "Invalid filename"}), 400
    filepath = APP_ROOT / "csv" / filename
    if not filepath.exists() or not filepath.is_file():
        return jsonify({"error": "File not found"}), 404
    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as f:
            content = f.read()
    except IOError as e:
        return jsonify({"error": str(e)}), 500
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return jsonify({"error": "Empty CSV"}), 400
    headers = rows[0]
    data_rows = rows[1:]
    if find_ip_column(headers) is None:
        return jsonify({"error": "CSV must have 'ip address' or 'ip_address' column"}), 400
    csv_data["headers"] = headers
    csv_data["rows"] = data_rows
    return jsonify({"headers": headers, "rows": data_rows})


@app.route("/api/csv/upload", methods=["POST"])
def csv_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".csv"):
        return jsonify({"error": "Invalid CSV file"}), 400
    content = f.read().decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return jsonify({"error": "Empty CSV"}), 400
    headers = rows[0]
    data_rows = rows[1:]
    if find_ip_column(headers) is None:
        return jsonify({"error": "CSV must have 'ip address' or 'ip_address' column"}), 400
    csv_data["headers"] = headers
    csv_data["rows"] = data_rows
    return jsonify({"headers": headers, "rows": data_rows})


@app.route("/api/csv/download")
def csv_download():
    """Download CSV from server state (use after save). Client-side download preferred for unsaved edits."""
    if not csv_data["headers"]:
        return jsonify({"error": "No CSV data"}), 400
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(csv_data["headers"])
    w.writerows(csv_data["rows"])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="routers.csv",
    )


@app.route("/api/csv/save", methods=["POST"])
def csv_save():
    data = request.get_json() or {}
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    filename = (data.get("filename") or "routers.csv").strip()
    if not filename.lower().endswith(".csv"):
        filename += ".csv"
    if not headers:
        return jsonify({"error": "No headers"}), 400
    if find_ip_column(headers) is None:
        return jsonify({"error": "CSV must have 'ip address' or 'ip_address' column"}), 400
    csv_data["headers"] = headers
    csv_data["rows"] = rows
    filepath = APP_ROOT / "csv" / filename
    ensure_folders()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    return jsonify({"saved": str(filepath)})


@app.route("/api/csv/update", methods=["POST"])
def csv_update():
    """Update in-memory CSV from editor (save to memory only)"""
    data = request.get_json() or {}
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    if not headers:
        return jsonify({"error": "No headers"}), 400
    if find_ip_column(headers) is None:
        return jsonify({"error": "CSV must have 'ip address' or 'ip_address' column"}), 400
    csv_data["headers"] = headers
    csv_data["rows"] = rows
    return jsonify({"ok": True})


@app.route("/api/files/<deploy_type>")
def list_files(deploy_type):
    if deploy_type not in DEPLOYMENT_TYPES:
        return jsonify({"error": "Invalid type"}), 400
    ensure_folders()
    folder = DEPLOYMENT_TYPES[deploy_type]["folder"]
    ext = DEPLOYMENT_TYPES[deploy_type]["ext"]
    files = []
    for f in (APP_ROOT / folder).iterdir():
        if not f.is_file():
            continue
        if not ext:
            files.append({"name": f.name, "path": str(f)})
        elif ext == ".tar.gz":
            if f.name.lower().endswith(".tar.gz"):
                files.append({"name": f.name, "path": str(f)})
        elif f.suffix.lower() == ext.lower():
            files.append({"name": f.name, "path": str(f)})
    return jsonify({"files": files})


@app.route("/api/files/<deploy_type>/upload", methods=["POST"])
def upload_file(deploy_type):
    if deploy_type not in DEPLOYMENT_TYPES:
        return jsonify({"error": "Invalid type"}), 400
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "No filename"}), 400
    ensure_folders()
    folder = DEPLOYMENT_TYPES[deploy_type]["folder"]
    path = APP_ROOT / folder / f.filename
    f.save(path)
    return jsonify({"name": f.filename, "path": str(path)})


def _get_ncos_headers():
    """Get NCOS ECM API headers from env vars first, then config file. Returns (headers_dict, source)."""
    env_keys = (
        os.environ.get("X_CP_API_ID"),
        os.environ.get("X_CP_API_KEY"),
        os.environ.get("X_ECM_API_ID"),
        os.environ.get("X_ECM_API_KEY"),
    )
    if all(env_keys):
        return {
            "X-CP-API-ID": env_keys[0],
            "X-CP-API-KEY": env_keys[1],
            "X-ECM-API-ID": env_keys[2],
            "X-ECM-API-KEY": env_keys[3],
        }, "env"
    if not API_KEYS_FILE.exists():
        return None, None
    try:
        with open(API_KEYS_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
        h = {
            "X-CP-API-ID": cfg.get("X-CP-API-ID", ""),
            "X-CP-API-KEY": cfg.get("X-CP-API-KEY", ""),
            "X-ECM-API-ID": cfg.get("X-ECM-API-ID", ""),
            "X-ECM-API-KEY": cfg.get("X-ECM-API-KEY", ""),
        }
        if not all(h.values()):
            return None, None
        return h, "file"
    except (json.JSONDecodeError, IOError):
        return None, None


@app.route("/api/ncos/config", methods=["GET", "POST"])
def ncos_config():
    """Get or save NCOS API keys"""
    if request.method == "GET":
        h, source = _get_ncos_headers()
        if not h:
            return jsonify({"configured": False})
        resp = {"configured": True, "source": source or "file"}
        if source != "env":
            resp.update({
                "X-CP-API-ID": h.get("X-CP-API-ID", ""),
                "X-CP-API-KEY": h.get("X-CP-API-KEY", ""),
                "X-ECM-API-ID": h.get("X-ECM-API-ID", ""),
                "X-ECM-API-KEY": h.get("X-ECM-API-KEY", ""),
            })
        return jsonify(resp)
    data = request.get_json() or {}
    cfg = {
        "X-CP-API-ID": data.get("X-CP-API-ID", ""),
        "X-CP-API-KEY": data.get("X-CP-API-KEY", ""),
        "X-ECM-API-ID": data.get("X-ECM-API-ID", ""),
        "X-ECM-API-KEY": data.get("X-ECM-API-KEY", ""),
    }
    with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    return jsonify({"ok": True})


@app.route("/api/ncos/firmwares")
def ncos_firmwares():
    """List available NCOS images for a version and model"""
    version = request.args.get("version", "").strip()
    model = request.args.get("model", "").strip()
    if not version or not model:
        return jsonify({"error": "version and model required"}), 400
    headers, _ = _get_ncos_headers()
    if not headers or not all(headers.values()):
        return jsonify({"error": "NCOS API keys not configured"}), 400
    try:
        url = NCOS_DEVICE_URL + version
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json().get("data", [])
        model_upper = model.upper()
        matches = [i for i in data if model_upper in (i.get("url") or "").upper()]
        return jsonify({"firmwares": [{"url": m["url"], "id": i} for i, m in enumerate(matches)]})
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ncos/download", methods=["POST"])
def ncos_download():
    """Download NCOS image from Cradlepoint ECM and save to NCOS folder"""
    data = request.get_json() or {}
    version = data.get("version", "").strip()
    model = data.get("model", "").strip()
    url_path = data.get("url", "").strip()
    if not version or not model or not url_path:
        return jsonify({"error": "version, model, and url required"}), 400
    headers, _ = _get_ncos_headers()
    if not headers or not all(headers.values()):
        return jsonify({"error": "NCOS API keys not configured"}), 400
    try:
        firmware_url = NCOS_FIRMWARE_BASE + url_path
        r = requests.get(firmware_url, headers=headers, timeout=300)
        r.raise_for_status()
        filename = f"{model}-{version}.bin"
        ensure_folders()
        out_path = APP_ROOT / "NCOS" / filename
        with open(out_path, "wb") as f:
            f.write(r.content)
        return jsonify({"ok": True, "name": filename, "path": str(out_path)})
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/online-status", methods=["POST"])
def online_status():
    """Query each router for uptime, add column to CSV"""
    data = request.get_json() or {}
    same_creds = data.get("same_credentials", False)
    default_user = data.get("username", "")
    default_pass = data.get("password", "")
    same_port = data.get("same_port", True)
    default_port = int(data.get("port", 8080))

    headers = csv_data.get("headers", [])
    rows = csv_data.get("rows", [])
    if not headers or not rows:
        return jsonify({"error": "No router data. Load a CSV first."}), 400

    ip_col = find_ip_column(headers)
    if ip_col is None:
        return jsonify({"error": "No ip address column found"}), 400

    if same_creds and (not default_user or not default_pass):
        return jsonify({"error": "Username and password required when using same credentials"}), 400

    col_header = datetime.now().strftime("%Y-%m-%d %H:%M") + " - Online Status"
    new_headers = headers + [col_header]
    new_rows = []
    uptime_idx = len(headers)

    for row in list(rows):
        while len(row) <= ip_col:
            row.append("")
        ip_raw = str(row[ip_col]).strip()
        if not ip_raw:
            new_rows.append(row + ["Offline"])
            continue
        if ":" in ip_raw:
            ip, _, port_str = ip_raw.partition(":")
            try:
                port = int(port_str)
            except (ValueError, TypeError):
                port = get_router_port(row, headers, same_port, default_port)
        else:
            ip = ip_raw
            port = get_router_port(row, headers, same_port, default_port)
        username, password = get_router_credentials(row, headers, same_creds, default_user, default_pass)
        if not username or not password:
            new_rows.append(row + ["Offline"])
            continue
        base = f"http://{ip}:{port}"
        url = f"{base}/api/status/system/uptime"
        try:
            r = requests.get(url, auth=(username, password), verify=False, timeout=10)
            if r.status_code < 300:
                body = r.json()
                uptime_sec = body.get("data")
                if uptime_sec is None and "data" in body:
                    uptime_sec = body["data"]
                value = format_uptime(uptime_sec)
                if not value:
                    value = "Offline"
            else:
                value = "Offline"
        except Exception:
            value = "Offline"
        new_rows.append(row + [value])

    csv_data["headers"] = new_headers
    csv_data["rows"] = new_rows

    # Save CSV to file when online status completes
    filename = "routers.csv"
    if CREDENTIALS_CONFIG_FILE.exists():
        try:
            with open(CREDENTIALS_CONFIG_FILE, encoding="utf-8") as f:
                cfg = json.load(f)
            if cfg.get("last_file"):
                filename = cfg["last_file"]
        except (json.JSONDecodeError, IOError):
            pass
    if not filename.lower().endswith(".csv"):
        filename += ".csv"
    filepath = APP_ROOT / "csv" / filename
    ensure_folders()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(new_headers)
        w.writerows(new_rows)

    return jsonify({"headers": new_headers, "rows": new_rows})


@app.route("/api/deploy", methods=["POST"])
def deploy():
    data = request.get_json() or {}
    file_path = data.get("file_path")
    deploy_type = data.get("deploy_type")
    same_creds = data.get("same_credentials", False)
    default_user = data.get("username", "")
    default_pass = data.get("password", "")
    same_port = data.get("same_port", True)
    default_port = int(data.get("port", 8080))
    ssh_port = int(data.get("ssh_port", 22))

    if not file_path or deploy_type not in DEPLOYMENT_TYPES:
        return jsonify({"error": "Invalid deploy request"}), 400
    path = Path(file_path) if Path(file_path).is_absolute() else APP_ROOT / file_path
    if not path.exists() or not path.is_file():
        return jsonify({"error": "File not found"}), 400
    action = DEPLOYMENT_TYPES[deploy_type]["endpoint"]
    use_scp = deploy_type == "sdk_apps"

    headers = csv_data.get("headers", [])
    rows = csv_data.get("rows", [])
    if not headers or not rows:
        return jsonify({"error": "No router data. Load a CSV first."}), 400

    ip_col = find_ip_column(headers)
    if ip_col is None:
        return jsonify({"error": "No ip address column found"}), 400

    if same_creds and (not default_user or not default_pass):
        return jsonify({"error": "Username and password required when using same credentials"}), 400

    deploy_type_labels = {
        "licenses": "License",
        "ncos": "NCOS",
        "configuration": "Configuration",
        "sdk_apps": "SDK App Deployment",
    }
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    col_header = f"{timestamp_str} - {deploy_type_labels.get(deploy_type, deploy_type)} - {path.name}"
    new_headers = headers + [col_header]
    new_rows = []

    for row in list(rows):
        row = list(row)
        while len(row) <= ip_col:
            row.append("")
        ip_raw = str(row[ip_col]).strip()
        if not ip_raw:
            new_rows.append(row + ["Skipped: no IP"])
            continue
        if ":" in ip_raw:
            ip, _, port_str = ip_raw.partition(":")
            try:
                port = int(port_str)
            except (ValueError, TypeError):
                port = get_router_port(row, headers, same_port, default_port)
        else:
            ip = ip_raw
            port = get_router_port(row, headers, same_port, default_port)
        username, password = get_router_credentials(row, headers, same_creds, default_user, default_pass)
        if not username or not password:
            new_rows.append(row + ["Skipped: missing credentials"])
            continue
        result_lines = []
        if use_scp:
            push_sdk_app_via_scp(ip, ssh_port, username, password, str(path), result_lines)
        else:
            push_to_router(ip, port, username, password, str(path), action, result_lines)
        new_rows.append(row + ["\n".join(result_lines) if result_lines else ""])

    csv_data["headers"] = new_headers
    csv_data["rows"] = new_rows

    # Save CSV
    filename = "routers.csv"
    if CREDENTIALS_CONFIG_FILE.exists():
        try:
            with open(CREDENTIALS_CONFIG_FILE, encoding="utf-8") as f:
                cfg = json.load(f)
            if cfg.get("last_file"):
                filename = cfg["last_file"]
        except (json.JSONDecodeError, IOError):
            pass
    if not filename.lower().endswith(".csv"):
        filename += ".csv"
    filepath = APP_ROOT / "csv" / filename
    ensure_folders()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(new_headers)
        w.writerows(new_rows)

    return jsonify({"ok": True, "headers": new_headers, "rows": new_rows})


if __name__ == "__main__":
    print("Private Router Manager: http://localhost:9000")
    app.run(host="127.0.0.1", port=9000, debug=True)
