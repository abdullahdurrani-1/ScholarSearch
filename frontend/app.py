"""Simple HTTP server to serve ScholarSearch dashboard (dashboard.html)."""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import sys

class DashboardHandler(SimpleHTTPRequestHandler):
    """Serve dashboard.html as default index file."""
    
    def do_GET(self):
        # Redirect root to dashboard.html
        if self.path == '/' or self.path == '':
            self.path = '/dashboard.html'
        return super().do_GET()
    
    def end_headers(self):
        # Disable caching for development
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        super().end_headers()

if __name__ == "__main__":
    # Change to frontend directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Start server on port 5000
    server = HTTPServer(("0.0.0.0", 5000), DashboardHandler)
    print("🚀 Frontend server running at http://localhost:5000")
    print("📄 Dashboard: http://localhost:5000/dashboard.html")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped")
        sys.exit(0)
