#!/usr/bin/env python3
"""
Cisco to Cradlepoint Converter Web Interface

A Flask web application that provides a user-friendly interface for converting
Cisco router configurations to Cradlepoint zone firewall configurations.

Author: AI Assistant
Date: 2024
"""

import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from cisco_to_cradlepoint_converter_v3 import CiscoToCradlepointConverter
import tempfile
import shutil

app = Flask(__name__)
app.secret_key = 'cisco-cradlepoint-converter-2024'

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'txt', 'conf', 'cfg'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main page with upload form."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and conversion."""
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_{filename}")
        file.save(input_path)
        
        try:
            print(f"Starting conversion for file: {input_path}")
            
            # Get options from form
            add_internet_zone = request.form.get('add_internet_zone') == 'on'
            internet_zone_name = request.form.get('internet_zone_name', 'EXT-Internet')
            
            # Convert the configuration
            converter = CiscoToCradlepointConverter(
                input_path, 
                add_internet_zone=add_internet_zone,
                internet_zone_name=internet_zone_name
            )
            config = converter.generate_cradlepoint_config()
            
            print(f"Conversion completed. Config keys: {list(config.keys())}")
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
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            # Clean up input file
            os.remove(input_path)
            
            return jsonify({
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
            import traceback
            traceback.print_exc()
            # Clean up input file on error
            if os.path.exists(input_path):
                os.remove(input_path)
            
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    
    else:
        return jsonify({
            'success': False,
            'error': 'Invalid file type. Please upload .txt, .conf, or .cfg files.'
        }), 400

@app.route('/download/<session_id>')
def download_file(session_id):
    """Download the converted configuration file."""
    output_filename = f"cradlepoint_config_{session_id}.json"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    
    if os.path.exists(output_path):
        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"cradlepoint_config_{session_id}.json",
            mimetype='application/json'
        )
    else:
        flash('File not found or expired')
        return redirect(url_for('index'))

@app.route('/api/convert', methods=['POST'])
def api_convert():
    """API endpoint for programmatic conversion."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Get options from form
        add_internet_zone = request.form.get('add_internet_zone') == 'on'
        internet_zone_name = request.form.get('internet_zone_name', 'EXT-Internet')
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp_file:
            file.save(temp_file.name)
            
            # Convert the configuration
            converter = CiscoToCradlepointConverter(
                temp_file.name,
                add_internet_zone=add_internet_zone,
                internet_zone_name=internet_zone_name
            )
            config = converter.generate_cradlepoint_config()
            
            # Clean up
            os.unlink(temp_file.name)
            
            return jsonify({
                'success': True,
                'configuration': config
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'Cisco to Cradlepoint Converter'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
