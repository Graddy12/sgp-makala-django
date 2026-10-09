"""
SGP Makala — Django settings (SQLite).
"""
from pathlib import Path
import os
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
)
environ.Env.read_env(BASE_DIR / '.env')

IS_VERCEL = bool(os.environ.get('VERCEL'))
RENDER_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
IS_RENDER = bool(RENDER_HOSTNAME)
IS_DEPLOYED = IS_VERCEL or IS_RENDER

SECRET_KEY = env('SECRET_KEY', default='dev-sgp-makala-insecure-change-me')
DEBUG = env.bool('DEBUG', default=not IS_DEPLOYED)
_default_allowed_hosts = ['localhost', '127.0.0.1', 'testserver']
if IS_VERCEL:
    _default_allowed_hosts.append('.vercel.app')
if RENDER_HOSTNAME:
    _default_allowed_hosts.append(RENDER_HOSTNAME)
ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS',
    default=_default_allowed_hosts,
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'prison',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.ActiveUserMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.sgp_globals',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'db.sqlite3'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Kinshasa'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG
            else 'whitenoise.storage.CompressedStaticFilesStorage'
        )
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {
    message_constants.DEBUG: 'secondary',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'danger',
}

APP_NAME = 'SGP Makala'
PRISON_NAME = 'Prison Centrale de Makala'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=(
        (['https://*.vercel.app'] if IS_VERCEL else [])
        + ([f'https://{RENDER_HOSTNAME}'] if RENDER_HOSTNAME else [])
    ),
)
if IS_DEPLOYED:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Bootstrap admin from env
SGP_ADMIN_EMAIL = env('SGP_ADMIN_EMAIL', default='admin@makala.cd')
SGP_ADMIN_PASSWORD = env('SGP_ADMIN_PASSWORD', default='Admin@Makala2026')
SGP_ADMIN_NOM = env('SGP_ADMIN_NOM', default='Admin')
SGP_ADMIN_PRENOM = env('SGP_ADMIN_PRENOM', default='Systeme')
SGP_ADMIN_TELEPHONE = env('SGP_ADMIN_TELEPHONE', default='')
