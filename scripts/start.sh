#!/usr/bin/env bash
set -euo pipefail

python manage.py migrate --noinput
python manage.py bootstrap_admin
python manage.py prepare_demo
export SGP_DEMO_BOOTSTRAPPED=1
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 1 --threads 4 --timeout 120
