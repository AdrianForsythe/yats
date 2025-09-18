import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-dev-key-change-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Application definition
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.humanize',
    'rpc4django',
    'bootstrap_toolkit',
    'yats',
    'web',
    'markdownx',
    'haystack',  # Add haystack back
    'background_task',
]

# Configure haystack with simple backend (no external dependencies)
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'web.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'web.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'data' / 'db' / 'yats.sqlite',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'data' / 'static'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# File uploads
FILE_UPLOAD_PATH = BASE_DIR / 'data' / 'files'

# Disable problematic features for development
# HAYSTACK_CONNECTIONS = {} # This line is now redundant as it's configured in INSTALLED_APPS

# Use dummy cache instead of memcached
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Disable virus scanning
FILE_UPLOAD_VIRUS_SCAN = False

# Console email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Project name
PROJECT_NAME = 'YATS-Development'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
}

# YATS-specific settings
TICKET_CLASS = 'yats.models.tickets'

# GitHub integration (optional - can be empty for development)
GITHUB_OWNER = 'mediafactory'
GITHUB_REPO = 'yats'
GITHUB_USER = 'hg'
GITHUB_PASS = 'hg'

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB

# Session settings
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = True

# Security settings for development
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
X_FRAME_OPTIONS = 'SAMEORIGIN'

# YATS notification settings
TICKET_NEW_MAIL_RCPT = ''
TICKET_NEW_JABBER_RCPT = ''
TICKET_NEW_SIGNAL_RCPT = ''
TICKET_NON_PUBLIC_FIELDS = ['billing_needed', 'billing_reason', 'billing_done', 'fixed_in_version', 'solution', 'assigned', 'priority']
TICKET_SEARCH_FIELDS = ['caption', 'c_user', 'priority', 'type', 'customer', 'component', 'deadline', 'billing_needed', 'billing_done', 'closed', 'assigned', 'state', 'description', 'hasAttachments', 'hasComments']
TICKET_EDITABLE_FIELDS_AFTER_CLOSE = ['billing_done']
