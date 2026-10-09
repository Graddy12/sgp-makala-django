"""
WSGI config for SGP Makala.
Compatible with local gunicorn and Vercel serverless.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
app = application
