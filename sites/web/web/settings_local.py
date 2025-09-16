# -*- coding: utf-8 -*-
# Local development settings for YATS
# This file overrides production settings for local development

import os
from .settings import *

# Override database settings for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'db', 'yats_dev.sqlite'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

# Override file paths for local development
FILE_UPLOAD_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'files')
STATIC_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'static')
TEMP_ROOT = '/tmp/'

# Override logging for local development
LOGGING['handlers']['request_handler']['filename'] = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
    'data', 'logs', 'django_request.log'
)

# Ensure log directory exists
log_dir = os.path.dirname(LOGGING['handlers']['request_handler']['filename'])
os.makedirs(log_dir, exist_ok=True)

# Override search index path for local development (disabled)
HAYSTACK_CONNECTIONS = {}

# Disable virus scanning for local development (optional)
FILE_UPLOAD_VIRUS_SCAN = False

# Disable memcache for local development (use dummy cache)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Project name for development
PROJECT_NAME = 'YATS-DEV'

# Disable email notifications for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Allow all hosts for development
ALLOWED_HOSTS = ['*']

# Disable SSL redirect for development
SECURE_PROXY_SSL_HEADER = None

# Override INSTALLED_APPS to disable CalDAV functionality temporarily
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
    # 'djradicale',  # Temporarily disabled due to Django 5.x compatibility issues
    'markdownx',
    # 'haystack',  # Temporarily disabled due to xapian dependency issues
    'background_task',
]

# Use local URLs without CalDAV functionality
ROOT_URLCONF = 'web.urls_local'
