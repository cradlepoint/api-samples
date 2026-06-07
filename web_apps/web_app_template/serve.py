#!/usr/bin/env python3
"""
Web App Template - Development Server
Serves the style guide and template files using Python's built-in HTTP server.
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

PORT = 8000


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler with cache-busting headers."""

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def log_message(self, format, *args):
        sys.stderr.write("%s - - [%s] %s\n" %
                        (self.address_string(),
                         self.log_date_time_string(),
                         format % args))


def main():
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)

    if not (script_dir / 'index.html').exists():
        print(f"Error: index.html not found in {script_dir}")
        sys.exit(1)

    try:
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            print("=" * 60)
            print("Web App Template Server")
            print("=" * 60)
            print(f"Server running at: http://localhost:{PORT}")
            print(f"Serving directory: {script_dir}")
            print(f"\nPress Ctrl+C to stop the server")
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


if __name__ == "__main__":
    main()
