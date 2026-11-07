"""Vercel WSGI entrypoint for Curato AI."""
from backend.app import create_app


app = create_app()
