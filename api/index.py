import sys
import os
import traceback
from pathlib import Path
from urllib.parse import parse_qs

# Add project root to sys.path so backend imports work on Vercel
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Set VERCEL env hint for store.py runtime directory selection
if not os.environ.get('VERCEL'):
    os.environ['VERCEL'] = '1'

class VercelPathMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        
        # Check __route__ query parameter if rewritten by vercel.json
        qs = parse_qs(environ.get('QUERY_STRING', ''))
        if '__route__' in qs and qs['__route__'][0]:
            r = qs['__route__'][0]
            environ['PATH_INFO'] = r if r.startswith('/') else '/' + r
        elif path in ('/api/index', '/api/index.py', '/api', '/api/'):
            matched = environ.get('HTTP_X_MATCHED_PATH') or environ.get('HTTP_X_FORWARDED_URI')
            if matched and matched not in ('/api/index', '/api/index.py', '/api', '/api/'):
                environ['PATH_INFO'] = matched.split('?')[0]
            else:
                environ['PATH_INFO'] = '/'
        return self.wsgi_app(environ, start_response)

try:
    from backend.app import create_app
    app = create_app(root)
    app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
except Exception as e:
    from flask import Flask, jsonify
    app = Flask(__name__)
    _boot_error = traceback.format_exc()

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def error_handler(path):
        return jsonify(
            error='Application failed to start',
            details=_boot_error,
            python_version=sys.version,
            cwd=os.getcwd(),
            files=os.listdir(str(root)) if root.exists() else 'root not found'
        ), 500
