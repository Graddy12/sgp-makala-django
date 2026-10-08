"""
WSGI config for SGP Makala.
Compatible with local gunicorn and Vercel serverless.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
app = application

# Demo bootstrap on Vercel (éphémère /tmp SQLite)
if os.environ.get('VERCEL'):
    try:
        from django.core.management import call_command
        call_command('migrate', interactive=False, verbosity=0)
        call_command('bootstrap_admin', verbosity=0)
    except Exception:
        pass
