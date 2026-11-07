"""Vercel WSGI entrypoint for Curato AI."""
from backend.app import create_app

flask_app = create_app()

def app(environ, start_response):
    matched = environ.get('HTTP_X_MATCHED_PATH') or environ.get('HTTP_X_FORWARDED_URI')
    if matched:
        environ['PATH_INFO'] = matched.split('?')[0]
    elif environ.get('PATH_INFO') in ('/api/index', '/api/index.py'):
        environ['PATH_INFO'] = '/'
    return flask_app(environ, start_response)
