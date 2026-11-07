import sys
from pathlib import Path

# Add project root to sys.path so backend imports work reliably on Vercel
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from backend.app import create_app

app = create_app(root)
