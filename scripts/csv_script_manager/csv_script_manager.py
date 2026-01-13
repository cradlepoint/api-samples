#!/usr/bin/env python3
"""
CSV Editor - A web-based CSV file editor.
Allows users to load, edit, and save CSV files through a modern web interface.
Works on Windows, macOS, and Linux.
"""

import json
import os
import subprocess
import threading
import requests
from http.server import HTTPServer, SimpleHTTPRequestHandler
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

# Port for the web interface
PORT = 8000

# Directory for storing CSV files (relative to app directory)
CSV_DIR_NAME = 'csv_files'
SCRIPTS_DIR_NAME = 'scripts'

class CSVEditorHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for serving the CSV editor interface."""
    
    def __init__(self, *args, **kwargs):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_dir = os.path.join(script_dir, CSV_DIR_NAME)
        self.scripts_dir = os.path.join(script_dir, SCRIPTS_DIR_NAME)
        self.last_file_path = os.path.join(script_dir, '.last_file.txt')
        super().__init__(*args, directory=script_dir, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for API endpoints and static files."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/list':
            self.handle_list_files()
        elif parsed_path.path == '/api/load':
            self.handle_load_file(parsed_path.query)
        elif parsed_path.path == '/api/download':
            self.handle_download_file(parsed_path.query)
        elif parsed_path.path == '/api/scripts':
            self.handle_list_scripts()
        elif parsed_path.path == '/api/example-script':
            self.handle_get_example_script()
        elif parsed_path.path == '/api/load-script':
            self.handle_load_script(parsed_path.query)
        elif parsed_path.path == '/api/last-file':
            self.handle_get_last_file()
        elif parsed_path.path == '/api/environment-info':
            self.handle_get_environment_info()
        elif parsed_path.path == '/api/api-keys-status':
            self.handle_get_api_keys_status()
        elif parsed_path.path == '/' or parsed_path.path == '/index.html':
            # Serve index.html for root path
            self.path = '/static/index.html'
            super().do_GET()
        else:
            # Serve static files (HTML, CSS, JS)
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests for file operations."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/upload':
            self.handle_upload_file()
        elif parsed_path.path == '/api/save':
            self.handle_save_file()
        elif parsed_path.path == '/api/run-script':
            self.handle_run_script()
        elif parsed_path.path == '/api/create-script':
            self.handle_create_script()
        elif parsed_path.path == '/api/download-script-url':
            self.handle_download_script_url()
        elif parsed_path.path == '/api/delete-script':
            self.handle_delete_script()
        elif parsed_path.path == '/api/set-api-keys':
            self.handle_set_api_keys()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
    
    def handle_list_files(self):
        """List all CSV files in the storage directory."""
        try:
            if not os.path.exists(self.csv_dir):
                os.makedirs(self.csv_dir)
            
            files = []
            for filename in os.listdir(self.csv_dir):
                if filename.endswith('.csv'):
                    filepath = os.path.join(self.csv_dir, filename)
                    file_size = os.path.getsize(filepath)
                    files.append({
                        'name': filename,
                        'size': file_size
                    })
            
            self.send_json_response({'files': files})
        except Exception as e:
            print(f'Error listing files: {str(e)}')
            self.send_error_response(f'Error listing files: {str(e)}')
    
    def handle_load_file(self, query):
        """Load a CSV file and return its contents."""
        try:
            params = parse_qs(query)
            filename = params.get('filename', [''])[0]
            
            if not filename:
                self.send_error_response('Filename parameter required')
                return
            
            # Security: prevent directory traversal
            filename = os.path.basename(filename)
            filepath = os.path.join(self.csv_dir, filename)
            
            if not os.path.exists(filepath):
                self.send_error_response(f'File not found: {filename}')
                return
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse CSV into rows
            rows = []
            for line in content.split('\n'):
                if line.strip():
                    # Simple CSV parsing (handles quoted fields)
                    row = self.parse_csv_line(line)
                    rows.append(row)
            
            # Save as last opened file
            self.save_last_file(filename)
            
            self.send_json_response({
                'filename': filename,
                'rows': rows,
                'content': content
            })
        except Exception as e:
            print(f'Error loading file: {str(e)}')
            self.send_error_response(f'Error loading file: {str(e)}')
    
    def handle_upload_file(self):
        """Handle file upload from client."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            data = json.loads(post_data.decode('utf-8'))
            filename = data.get('filename', '')
            content = data.get('content', '')
            
            if not filename:
                self.send_error_response('Filename required')
                return
            
            # Security: prevent directory traversal
            filename = os.path.basename(filename)
            if not filename.endswith('.csv'):
                filename += '.csv'
            
            if not os.path.exists(self.csv_dir):
                os.makedirs(self.csv_dir)
            
            filepath = os.path.join(self.csv_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Save as last opened file
            self.save_last_file(filename)
            
            print(f'File uploaded: {filename}')
            self.send_json_response({
                'success': True,
                'filename': filename,
                'message': 'File uploaded successfully'
            })
        except Exception as e:
            print(f'Error uploading file: {str(e)}')
            self.send_error_response(f'Error uploading file: {str(e)}')
    
    def handle_save_file(self):
        """Save CSV file with new content."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            data = json.loads(post_data.decode('utf-8'))
            filename = data.get('filename', '')
            rows = data.get('rows', [])
            
            if not filename:
                self.send_error_response('Filename required')
                return
            
            # Security: prevent directory traversal
            filename = os.path.basename(filename)
            if not filename.endswith('.csv'):
                filename += '.csv'
            
            if not os.path.exists(self.csv_dir):
                os.makedirs(self.csv_dir)
            
            filepath = os.path.join(self.csv_dir, filename)
            
            # Convert rows back to CSV format
            csv_content = self.rows_to_csv(rows)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            # Save as last opened file
            self.save_last_file(filename)
            
            print(f'File saved: {filename}')
            self.send_json_response({
                'success': True,
                'filename': filename,
                'message': 'File saved successfully'
            })
        except Exception as e:
            print(f'Error saving file: {str(e)}')
            self.send_error_response(f'Error saving file: {str(e)}')
    
    def handle_download_file(self, query):
        """Download a CSV file."""
        try:
            params = parse_qs(query)
            filename = params.get('filename', [''])[0]
            
            if not filename:
                self.send_error_response('Filename parameter required')
                return
            
            # Security: prevent directory traversal
            filename = os.path.basename(filename)
            filepath = os.path.join(self.csv_dir, filename)
            
            if not os.path.exists(filepath):
                self.send_error_response(f'File not found: {filename}')
                return
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'text/csv')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(len(content.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except Exception as e:
            print(f'Error downloading file: {str(e)}')
            self.send_error_response(f'Error downloading file: {str(e)}')
    
    def parse_csv_line(self, line):
        """Parse a CSV line into fields, handling quoted values."""
        fields = []
        current_field = ''
        in_quotes = False
        
        i = 0
        while i < len(line):
            char = line[i]
            
            if char == '"':
                if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                    # Escaped quote
                    current_field += '"'
                    i += 2
                    continue
                else:
                    # Toggle quote state
                    in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                # Field separator
                fields.append(current_field)
                current_field = ''
            else:
                current_field += char
            
            i += 1
        
        # Add the last field
        fields.append(current_field)
        
        return fields
    
    def rows_to_csv(self, rows):
        """Convert rows back to CSV format."""
        csv_lines = []
        for row in rows:
            # Escape fields that contain commas, quotes, or newlines
            escaped_fields = []
            for field in row:
                field_str = str(field) if field is not None else ''
                if ',' in field_str or '"' in field_str or '\n' in field_str:
                    # Escape quotes by doubling them
                    field_str = field_str.replace('"', '""')
                    escaped_fields.append('"' + field_str + '"')
                else:
                    escaped_fields.append(field_str)
            csv_lines.append(','.join(escaped_fields))
        
        return '\n'.join(csv_lines)
    
    def send_json_response(self, data):
        """Send JSON response."""
        response = json.dumps(data).encode('utf-8')
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)
    
    def send_error_response(self, message):
        """Send error response as JSON."""
        response = json.dumps({'error': message}).encode('utf-8')
        self.send_response(HTTPStatus.BAD_REQUEST)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)
    
    def handle_list_scripts(self):
        """List all available Python scripts in the scripts directory."""
        try:
            if not os.path.exists(self.scripts_dir):
                os.makedirs(self.scripts_dir)
            
            scripts = []
            if os.path.exists(self.scripts_dir):
                for filename in os.listdir(self.scripts_dir):
                    if filename.endswith('.py'):
                        filepath = os.path.join(self.scripts_dir, filename)
                        if os.path.isfile(filepath):
                            scripts.append({
                                'name': filename,
                                'path': filepath
                            })
            
            self.send_json_response({'scripts': scripts})
        except Exception as e:
            print(f'Error listing scripts: {str(e)}')
            self.send_error_response(f'Error listing scripts: {str(e)}')
    
    def handle_run_script(self):
        """Execute a script with the CSV filename as an argument."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            data = json.loads(post_data.decode('utf-8'))
            script_name = data.get('script', '')
            csv_filename = data.get('csv_file', '')
            
            if not script_name:
                self.send_error_response('Script name required')
                return
            
            if not csv_filename:
                self.send_error_response('CSV filename required')
                return
            
            # Security: prevent directory traversal
            script_name = os.path.basename(script_name)
            csv_filename = os.path.basename(csv_filename)
            
            # Build script path
            script_path = os.path.join(self.scripts_dir, script_name)
            
            # Verify script exists and is in scripts directory
            if not os.path.exists(script_path):
                self.send_error_response(f'Script not found: {script_name}')
                return
            
            # Verify it's actually in the scripts directory (prevent path traversal)
            if not os.path.abspath(script_path).startswith(os.path.abspath(self.scripts_dir)):
                self.send_error_response('Invalid script path')
                return
            
            # Build CSV file path
            csv_filepath = os.path.join(self.csv_dir, csv_filename)
            if not os.path.exists(csv_filepath):
                self.send_error_response(f'CSV file not found: {csv_filename}')
                return
            
            # Execute Python script with CSV filename as argument
            # Working directory is the app directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            print(f'Executing Python script: {script_name} with CSV file: {csv_filename}')
            
            try:
                # Run Python script with timeout (30 seconds)
                # Detect Python command (python3 or python) for cross-platform compatibility
                python_cmd = self._detect_python_command()
                
                # Create a wrapper script that adds the app directory to sys.path
                # This allows scripts to import modules from the parent directory
                # The wrapper preserves sys.argv so scripts can access command-line arguments
                wrapper_script = f'''import sys
import os
# Add app directory to Python path so scripts can import from parent folder
sys.path.insert(0, r'{script_dir}')
# Execute the actual script with proper sys.argv
sys.argv = [r'{script_path}', r'{csv_filepath}']
exec(compile(open(r'{script_path}').read(), r'{script_path}', 'exec'))
'''
                
                # Write wrapper to a temporary file
                wrapper_path = os.path.join(script_dir, '.script_wrapper.py')
                with open(wrapper_path, 'w') as f:
                    f.write(wrapper_script)
                
                try:
                    result = subprocess.run(
                        [python_cmd, wrapper_path],
                        cwd=script_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                finally:
                    # Clean up wrapper script
                    if os.path.exists(wrapper_path):
                        try:
                            os.remove(wrapper_path)
                        except:
                            pass
                
                response_data = {
                    'success': result.returncode == 0,
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'script': script_name,
                    'csv_file': csv_filename
                }
                
                print(f'Script execution completed with exit code: {result.returncode}')
                self.send_json_response(response_data)
                
            except subprocess.TimeoutExpired:
                print(f'Script execution timed out: {script_name}')
                self.send_error_response('Script execution timed out (30 seconds)')
            except Exception as e:
                print(f'Error executing script: {str(e)}')
                self.send_error_response(f'Error executing script: {str(e)}')
                
        except Exception as e:
            print(f'Error in handle_run_script: {str(e)}')
            self.send_error_response(f'Error running script: {str(e)}')
    
    def handle_create_script(self):
        """Create or update a Python script."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            data = json.loads(post_data.decode('utf-8'))
            script_name = data.get('script_name', '')
            script_content = data.get('script_content', '')
            
            if not script_name:
                self.send_error_response('Script name required')
                return
            
            if not script_content:
                self.send_error_response('Script content required')
                return
            
            # Security: prevent directory traversal
            script_name = os.path.basename(script_name)
            
            # Ensure .py extension
            if not script_name.endswith('.py'):
                script_name += '.py'
            
            # Ensure scripts directory exists
            if not os.path.exists(self.scripts_dir):
                os.makedirs(self.scripts_dir)
            
            script_path = os.path.join(self.scripts_dir, script_name)
            
            # Verify it's in the scripts directory (prevent path traversal)
            if not os.path.abspath(script_path).startswith(os.path.abspath(self.scripts_dir)):
                self.send_error_response('Invalid script path')
                return
            
            # Write script file
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Make script executable (Unix/Linux/macOS only, fails silently on Windows)
            try:
                os.chmod(script_path, 0o755)
            except (OSError, AttributeError):
                # Windows doesn't support chmod, which is fine
                pass
            
            print(f'Script created/updated: {script_name}')
            self.send_json_response({
                'success': True,
                'script_name': script_name,
                'message': 'Script created successfully'
            })
        except Exception as e:
            print(f'Error creating script: {str(e)}')
            self.send_error_response(f'Error creating script: {str(e)}')
    
    def handle_delete_script(self):
        """Delete a Python script."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            data = json.loads(post_data.decode('utf-8'))
            script_name = data.get('script_name', '')
            
            if not script_name:
                self.send_error_response('Script name required')
                return
            
            # Security: prevent directory traversal
            script_name = os.path.basename(script_name)
            
            # Ensure .py extension
            if not script_name.endswith('.py'):
                script_name += '.py'
            
            script_path = os.path.join(self.scripts_dir, script_name)
            
            # Verify script exists and is in scripts directory
            if not os.path.exists(script_path):
                self.send_error_response(f'Script not found: {script_name}')
                return
            
            # Verify it's actually in the scripts directory (prevent path traversal)
            if not os.path.abspath(script_path).startswith(os.path.abspath(self.scripts_dir)):
                self.send_error_response('Invalid script path')
                return
            
            # Delete the script file
            os.remove(script_path)
            
            print(f'Script deleted: {script_name}')
            self.send_json_response({
                'success': True,
                'script_name': script_name,
                'message': 'Script deleted successfully'
            })
        except Exception as e:
            print(f'Error deleting script: {str(e)}')
            self.send_error_response(f'Error deleting script: {str(e)}')
    
    def handle_get_example_script(self):
        """Get the content of the example.py script."""
        try:
            example_script_path = os.path.join(self.scripts_dir, 'example.py')
            
            if os.path.exists(example_script_path):
                with open(example_script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.send_json_response({
                    'content': content,
                    'filename': 'example.py'
                })
            else:
                # Return a default template if example.py doesn't exist
                default_template = '''#!/usr/bin/env python3
"""
Python script to process CSV files.
The CSV file path is passed as the first command-line argument.
"""

import sys
import os

def main():
    # Get CSV file path from command line argument
    if len(sys.argv) < 2:
        print("Error: No CSV file provided")
        print("Usage: python3 script.py <csv_file_path>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found: {csv_file}")
        sys.exit(1)
    
    # Your script logic here
    print(f"Processing CSV file: {csv_file}")
    print("Script execution completed successfully!")

if __name__ == '__main__':
    main()'''
                self.send_json_response({
                    'content': default_template,
                    'filename': 'example.py'
                })
        except Exception as e:
            print(f'Error getting example script: {str(e)}')
            self.send_error_response(f'Error getting example script: {str(e)}')
    
    def handle_load_script(self, query):
        """Load the content of a specific script."""
        try:
            params = parse_qs(query)
            script_name = params.get('script', [''])[0]
            
            if not script_name:
                self.send_error_response('Script name required')
                return
            
            # Security: prevent directory traversal
            script_name = os.path.basename(script_name)
            
            # Ensure .py extension
            if not script_name.endswith('.py'):
                script_name += '.py'
            
            script_path = os.path.join(self.scripts_dir, script_name)
            
            # Verify script exists and is in scripts directory
            if not os.path.exists(script_path):
                self.send_error_response(f'Script not found: {script_name}')
                return
            
            # Verify it's actually in the scripts directory (prevent path traversal)
            if not os.path.abspath(script_path).startswith(os.path.abspath(self.scripts_dir)):
                self.send_error_response('Invalid script path')
                return
            
            # Read script content
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_json_response({
                'content': content,
                'filename': script_name
            })
        except Exception as e:
            print(f'Error loading script: {str(e)}')
            self.send_error_response(f'Error loading script: {str(e)}')
    
    def save_last_file(self, filename):
        """Save the filename of the last opened/saved file."""
        try:
            with open(self.last_file_path, 'w', encoding='utf-8') as f:
                f.write(filename)
        except Exception as e:
            print(f'Error saving last file: {str(e)}')
    
    def handle_get_last_file(self):
        """Get the filename of the last opened/saved file."""
        try:
            if os.path.exists(self.last_file_path):
                with open(self.last_file_path, 'r', encoding='utf-8') as f:
                    filename = f.read().strip()
                
                # Verify the file still exists
                if filename:
                    filepath = os.path.join(self.csv_dir, filename)
                    if os.path.exists(filepath):
                        self.send_json_response({'filename': filename})
                        return
            
            self.send_json_response({'filename': None})
        except Exception as e:
            print(f'Error getting last file: {str(e)}')
            self.send_json_response({'filename': None})
    
    def handle_download_script_url(self):
        """Download a Python script from a URL and return its content."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            data = json.loads(post_data.decode('utf-8'))
            url = data.get('url', '').strip()
            
            if not url:
                self.send_error_response('URL required')
                return
            
            # Validate URL
            try:
                parsed_url = urlparse(url)
                if not parsed_url.scheme or not parsed_url.netloc:
                    self.send_error_response('Invalid URL format')
                    return
            except Exception:
                self.send_error_response('Invalid URL format')
                return
            
            # Handle GitHub folder URLs (tree URLs)
            if 'github.com' in parsed_url.netloc and '/tree/' in parsed_url.path:
                # Convert: https://github.com/user/repo/tree/branch/path
                # Use GitHub API to list files
                path_parts = parsed_url.path.split('/tree/', 1)
                if len(path_parts) == 2:
                    repo_path = path_parts[0]  # /user/repo
                    branch_and_path = path_parts[1]  # branch/path
                    
                    # Extract repo owner and name
                    repo_parts = repo_path.strip('/').split('/')
                    if len(repo_parts) >= 2:
                        owner = repo_parts[0]
                        repo = repo_parts[1]
                        
                        # Extract branch and path
                        branch_path_parts = branch_and_path.split('/', 1)
                        branch = branch_path_parts[0] if branch_path_parts else 'master'
                        folder_path = branch_path_parts[1] if len(branch_path_parts) > 1 else ''
                        
                        # Use GitHub API to get directory contents
                        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{folder_path}"
                        if branch and branch != 'master':
                            api_url += f"?ref={branch}"
                        
                        print(f'Fetching GitHub folder contents from: {api_url}')
                        try:
                            api_response = requests.get(api_url, timeout=30, headers={'User-Agent': 'CSV-Editor/1.0', 'Accept': 'application/vnd.github.v3+json'})
                            api_response.raise_for_status()
                            contents = api_response.json()
                            
                            # Filter for .py files and download them
                            scripts = []
                            if isinstance(contents, list):
                                for item in contents:
                                    if item.get('type') == 'file' and item.get('name', '').endswith('.py'):
                                        # Download the file content
                                        download_url = item.get('download_url') or item.get('url')
                                        if download_url:
                                            file_response = requests.get(download_url, timeout=30, headers={'User-Agent': 'CSV-Editor/1.0'})
                                            file_response.raise_for_status()
                                            scripts.append({
                                                'filename': item.get('name', 'downloaded_script.py'),
                                                'content': file_response.text
                                            })
                            
                            if scripts:
                                self.send_json_response({
                                    'success': True,
                                    'multiple': True,
                                    'scripts': scripts
                                })
                                return
                            else:
                                self.send_error_response('No Python (.py) files found in the GitHub folder')
                                return
                        except requests.exceptions.RequestException as e:
                            self.send_error_response(f'Error accessing GitHub folder: {str(e)}')
                            return
            
            # Convert GitHub blob URLs to raw URLs
            if 'github.com' in parsed_url.netloc and '/blob/' in parsed_url.path and 'raw.githubusercontent.com' not in parsed_url.netloc:
                # Convert: https://github.com/user/repo/blob/branch/path/file.py
                # To: https://raw.githubusercontent.com/user/repo/refs/heads/branch/path/file.py
                path_parts = parsed_url.path.split('/blob/', 1)
                if len(path_parts) == 2:
                    repo_path = path_parts[0]  # /user/repo
                    file_path = path_parts[1]  # branch/path/file.py
                    # Reconstruct as raw URL
                    url = f"{parsed_url.scheme}://raw.githubusercontent.com{repo_path}/refs/heads/{file_path}"
                    parsed_url = urlparse(url)
                    print(f'Converted GitHub blob URL to raw URL: {url}')
            
            # Download the script
            print(f'Downloading script from URL: {url}')
            try:
                response = requests.get(url, timeout=30, headers={'User-Agent': 'CSV-Editor/1.0'})
                response.raise_for_status()  # Raise an exception for bad status codes
                content = response.text
                    
                # Extract filename from URL or use default
                filename = os.path.basename(parsed_url.path)
                if not filename or not filename.endswith('.py'):
                    filename = 'downloaded_script.py'
                
                self.send_json_response({
                    'success': True,
                    'filename': filename,
                    'content': content
                })
            except requests.exceptions.HTTPError as e:
                self.send_error_response(f'HTTP error downloading script: {e.response.status_code} {e.response.reason}')
            except requests.exceptions.RequestException as e:
                self.send_error_response(f'Error downloading script: {str(e)}')
            except Exception as e:
                self.send_error_response(f'Error downloading script: {str(e)}')
        except Exception as e:
            print(f'Error handling script URL download: {str(e)}')
            self.send_error_response(f'Error downloading script: {str(e)}')
    
    def log_message(self, format, *args):
        """Override to use print instead of stderr."""
        print(f'{self.address_string()} - {format % args}')
    
    def _detect_python_command(self):
        """Detect the appropriate Python command for the current platform."""
        import shutil
        
        # Try python3 first (preferred on Unix-like systems)
        if shutil.which('python3'):
            return 'python3'
        # Fall back to python (common on Windows, also works on Unix)
        elif shutil.which('python'):
            return 'python'
        else:
            # Default fallback
            return 'python3'
    
    def handle_get_environment_info(self):
        """Get information about the current environment."""
        try:
            # Get environment name (e.g., from CONDA_DEFAULT_ENV, VIRTUAL_ENV, or system)
            env_name = os.environ.get('CONDA_DEFAULT_ENV') or os.environ.get('VIRTUAL_ENV')
            if env_name:
                # Extract just the name from virtual env path
                if os.path.sep in env_name:
                    env_name = os.path.basename(env_name)
            else:
                env_name = 'System'
            
            self.send_json_response({
                'environment': env_name
            })
        except Exception as e:
            print(f'Error getting environment info: {str(e)}')
            self.send_error_response(f'Error getting environment info: {str(e)}')
    
    def handle_get_api_keys_status(self):
        """Check which API keys are set (without showing values). 
        Security: Only returns boolean status, never actual key values."""
        try:
            # Security: Only return boolean values indicating presence, never actual values
            env_vars = {
                'X_CP_API_ID': bool(os.environ.get('X_CP_API_ID')),
                'X_CP_API_KEY': bool(os.environ.get('X_CP_API_KEY')),
                'X_ECM_API_ID': bool(os.environ.get('X_ECM_API_ID')),
                'X_ECM_API_KEY': bool(os.environ.get('X_ECM_API_KEY')),
                'TOKEN': bool(os.environ.get('TOKEN') or os.environ.get('NCM_API_TOKEN'))
            }
            
            # Security: Verify we're only sending booleans, never actual values
            for key, value in env_vars.items():
                if not isinstance(value, bool):
                    # This should never happen, but if it does, don't send it
                    env_vars[key] = False
            
            self.send_json_response(env_vars)
        except Exception as e:
            # Security: Don't expose any key information in error messages
            print(f'Error getting API keys status: {str(e)}')
            self.send_error_response('Error getting API keys status')
    
    def handle_set_api_keys(self):
        """Set API keys as environment variables. Never returns or logs actual key values."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            data = json.loads(post_data.decode('utf-8'))
            
            if not data:
                self.send_error_response('No API keys provided')
                return
            
            # Set environment variables (only if values are provided)
            set_count = 0
            set_keys = []
            for key, value in data.items():
                if value and value.strip():
                    # Only set if value is provided
                    # Security: Never log the actual value, only the key name
                    env_key = key.strip()
                    env_value = value.strip()
                    
                    try:
                        # Set environment variable (use the key as provided)
                        os.environ[env_key] = env_value
                        print(f'Set environment variable: {env_key} (value hidden)')
                        # Verify it was set
                        if env_key not in os.environ:
                            print(f'ERROR: {env_key} was not set in environment after assignment')
                        
                        set_count += 1
                        set_keys.append(env_key)
                    except Exception as e:
                        print(f'Error setting environment variable {env_key}: {str(e)}')
                        import traceback
                        traceback.print_exc()
            
            # Security: Return only success status and count, never the actual values
            self.send_json_response({
                'success': True,
                'message': f'Successfully set {set_count} API key(s)',
                'set_count': set_count
                # Intentionally not returning set_keys to avoid any potential exposure
            })
        except Exception as e:
            # Security: Don't expose any key information in error messages
            print(f'Error setting API keys: {str(e)}')
            import traceback
            traceback.print_exc()
            self.send_error_response('Error setting API keys')

def ensure_ncm_library():
    """
    Ensure the latest ncm.py library is available in the same folder as this script.
    Downloads from GitHub if missing or updates if needed.
    """
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ncm_path = os.path.join(script_dir, 'ncm.py')
    
    ncm_url = 'https://raw.githubusercontent.com/cradlepoint/api-samples/refs/heads/master/ncm/ncm/ncm.py'
    
    try:
        print('Checking for ncm.py library...')
        
        # Try to download the latest version
        response = requests.get(ncm_url, timeout=10, headers={'User-Agent': 'CSV-Editor/1.0'})
        response.raise_for_status()
        
        # Write to file
        with open(ncm_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f'ncm.py library updated successfully at: {ncm_path}')
        return True
        
    except requests.exceptions.RequestException as e:
        print(f'Warning: Could not download ncm.py from GitHub: {str(e)}')
        
        # If file doesn't exist, this is a problem
        if not os.path.exists(ncm_path):
            print('Error: ncm.py not found and could not be downloaded. Some scripts may not work.')
            return False
        else:
            print(f'Using existing ncm.py at: {ncm_path}')
            return True
    except Exception as e:
        print(f'Error ensuring ncm.py library: {str(e)}')
        if not os.path.exists(ncm_path):
            print('Warning: ncm.py not found. Some scripts may not work.')
        return False

# App starts here
print('Starting CSV Editor...')

# Ensure ncm.py library is available before starting server
ensure_ncm_library()

server = HTTPServer(('', PORT), CSVEditorHandler)
print(f'CSV Editor web server started on port {PORT}')
server.serve_forever()
