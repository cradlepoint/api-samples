#!/usr/bin/env python3
"""
Cisco to Cradlepoint Converter Web Interface

A FastAPI web application that provides a user-friendly interface for converting
Cisco router configurations to Cradlepoint zone firewall configurations.

Author: AI Assistant
Date: 2024
"""

import os
import json
import uuid
import tempfile
import shutil
import traceback
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn

from cisco_to_cradlepoint_converter_v3 import CiscoToCradlepointConverter

app = FastAPI(title="Cisco to Cradlepoint Converter")

# Configuration
APP_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = APP_DIR / "uploads"
OUTPUT_FOLDER = APP_DIR / "outputs"
TEMPLATES_DIR = APP_DIR / "templates"
ALLOWED_EXTENSIONS = {'txt', 'conf', 'cfg'}

# Ensure directories exist
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main page with upload form."""
    html_path = TEMPLATES_DIR / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    add_internet_zone: str = Form(default=""),
    internet_zone_name: str = Form(default="EXT-Internet"),
):
    """Handle file upload and conversion."""
    if not file.filename:
        return JSONResponse({"success": False, "error": "No file selected"}, status_code=400)

    if not allowed_file(file.filename):
        return JSONResponse(
            {"success": False, "error": "Invalid file type. Please upload .txt, .conf, or .cfg files."},
            status_code=400,
        )

    # Generate unique session ID
    session_id = str(uuid.uuid4())

    # Save uploaded file
    # Sanitize filename
    safe_filename = file.filename.replace("/", "_").replace("\\", "_")
    input_path = UPLOAD_FOLDER / f"{session_id}_{safe_filename}"

    content = await file.read()
    input_path.write_bytes(content)

    try:
        print(f"Starting conversion for file: {input_path}")

        # Convert the configuration
        converter = CiscoToCradlepointConverter(
            str(input_path),
            add_internet_zone=(add_internet_zone == "on"),
            internet_zone_name=internet_zone_name,
        )
        config = converter.generate_cradlepoint_config()

        print(f"Conversion completed. Config keys: {list(config.keys())}")
        ip_count = mac_count = port_count = 0
        if 'configuration' in config and len(config['configuration']) > 0:
            zfw = config['configuration'][0].get('security', {}).get('zfw', {})
            print(f"ZFW keys: {list(zfw.keys())}")
            print(f"Zones count: {len(zfw.get('zones', {}))}")
            print(f"Filter policies count: {len(zfw.get('filter_policies', {}))}")
            print(f"Forwardings count: {len(zfw.get('forwardings', {}))}")

            # Get identity counts
            identities = config['configuration'][0].get('identities', {})
            ip_count = len(identities.get('ip', []))
            mac_count = len(identities.get('mac', []))
            port_count = len(identities.get('port', []))
            print(f"IP identities count: {ip_count}")
            print(f"MAC identities count: {mac_count}")
            print(f"Port identities count: {port_count}")

        # Save output configuration
        output_filename = f"cradlepoint_config_{session_id}.json"
        output_path = OUTPUT_FOLDER / output_filename

        output_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

        # Clean up input file
        input_path.unlink(missing_ok=True)

        return JSONResponse({
            'success': True,
            'session_id': session_id,
            'output_filename': output_filename,
            'config_summary': {
                'zones': len(config['configuration'][0]['security']['zfw']['zones']),
                'filter_policies': len(config['configuration'][0]['security']['zfw']['filter_policies']),
                'forwardings': len(config['configuration'][0]['security']['zfw']['forwardings']),
                'ip_identities': ip_count,
                'mac_identities': mac_count,
                'port_identities': port_count
            }
        })

    except Exception as e:
        print(f"Conversion error: {e}")
        traceback.print_exc()
        # Clean up input file on error
        input_path.unlink(missing_ok=True)

        return JSONResponse(
            {'success': False, 'error': str(e)},
            status_code=400,
        )


@app.get("/download/{session_id}")
async def download_file(session_id: str):
    """Download the converted configuration file."""
    output_filename = f"cradlepoint_config_{session_id}.json"
    output_path = OUTPUT_FOLDER / output_filename

    if output_path.exists():
        return FileResponse(
            path=str(output_path),
            filename=output_filename,
            media_type="application/json",
        )
    else:
        return JSONResponse({"error": "File not found or expired"}, status_code=404)


@app.post("/api/convert")
async def api_convert(
    file: UploadFile = File(...),
    add_internet_zone: str = Form(default=""),
    internet_zone_name: str = Form(default="EXT-Internet"),
):
    """API endpoint for programmatic conversion."""
    if not file.filename or not allowed_file(file.filename):
        return JSONResponse({'error': 'Invalid file type'}, status_code=400)

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # Convert the configuration
        converter = CiscoToCradlepointConverter(
            temp_path,
            add_internet_zone=(add_internet_zone == "on"),
            internet_zone_name=internet_zone_name,
        )
        config = converter.generate_cradlepoint_config()

        # Clean up
        os.unlink(temp_path)

        return JSONResponse({'success': True, 'configuration': config})

    except Exception as e:
        return JSONResponse({'success': False, 'error': str(e)}, status_code=400)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Cisco to Cradlepoint Converter"}


if __name__ == '__main__':
    print("Cisco to Cradlepoint Converter starting...")
    print("Open http://localhost:5001 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=5001, log_level="info")
