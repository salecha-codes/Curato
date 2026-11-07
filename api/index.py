import sys
from pathlib import Path

# Add project root to sys.path so backend imports work reliably on Vercel
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from backend.app import create_app

flask_app = create_app(root)

def app(environ, start_response):
    # If Vercel rewrites forwarded the original path via headers, restore it:
    matched = environ.get('HTTP_X_MATCHED_PATH') or environ.get('HTTP_X_FORWARDED_URI')
    if matched:
        environ['PATH_INFO'] = matched.split('?')[0]
    elif environ.get('PATH_INFO') in ('/api/index', '/api/index.py'):
        environ['PATH_INFO'] = '/'
    return flask_app(environ, start_response)
