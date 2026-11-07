import sys
import os
import traceback
from pathlib import Path

# Add project root to sys.path so backend imports work on Vercel
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

# Set VERCEL env hint for store.py runtime directory selection
if not os.environ.get('VERCEL'):
    os.environ['VERCEL'] = '1'

try:
    from backend.app import create_app
    app = create_app(root)
except Exception as e:
    # If the app fails to start (e.g. scipy import timeout),
    # return a diagnostic Flask app so we can see what went wrong
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
