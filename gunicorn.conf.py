"""Bind Gunicorn to the port Render assigns to this service."""

import os


bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
