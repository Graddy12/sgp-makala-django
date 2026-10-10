"""
WSGI config for SGP Makala.
Compatible with local gunicorn and Vercel serverless.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
# Compatibility with Render services still using the previous start command.
from django.conf import settings
if settings.IS_RENDER and settings.DEMO_MODE and os.environ.get('SGP_DEMO_BOOTSTRAPPED') != '1':
    from django.core.management import call_command
    call_command('prepare_demo')
app = application
