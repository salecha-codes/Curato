"""Vercel entrypoint for Curato AI."""
import sys
from pathlib import Path
from urllib.parse import parse_qs

root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from backend.app import create_app

app = create_app(root)

class VercelPathMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
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

app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
