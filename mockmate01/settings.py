"""
Django settings for mockmate01 project.
"""

from pathlib import Path
import os
import environ

# --------------------------------
# Base Paths
# --------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------
# Environment Variables
# --------------------------------
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# --------------------------------
# Auth Redirects
# --------------------------------
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL = '/dashboard-redirect/'

# --------------------------------
# Security
# --------------------------------
SECRET_KEY = env("SECRET_KEY", default="django-insecure-placeholder")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# --------------------------------
# AI Provider Settings
# --------------------------------
AI_PROVIDER = env("AI_PROVIDER", default="gemini").lower()
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")

if not GEMINI_API_KEY and AI_PROVIDER == "gemini":
    print("⚠ Warning: GEMINI_API_KEY is missing — Gemini features will not work.")

if not OPENAI_API_KEY and AI_PROVIDER == "openai":
    print("⚠ Warning: OPENAI_API_KEY is missing — OpenAI features will not work.")

# --------------------------------
# Installed Apps
# --------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'django.contrib.humanize',
    'courses',
    'quizzes',
    'practice',
    'articles',
    'mock_interview',
    'users', 
    'tutor',
    'posts',
    'crispy_forms',
    'crispy_bootstrap5',
    'aptitude',
]

# --------------------------------
# Middleware
# --------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.NoCacheMiddleware',
]

# --------------------------------
# URL & WSGI
# --------------------------------
ROOT_URLCONF = 'mockmate01.urls'
WSGI_APPLICATION = 'mockmate01.wsgi.application'

# --------------------------------
# Templates
# --------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'core/templates'),
        ],
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

# --------------------------------
# Database
# --------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --------------------------------
# Password Validation
# --------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --------------------------------
# Internationalization
# --------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --------------------------------
# Static & Media Files
# --------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'core/static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --------------------------------
# Crispy Forms
# --------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# --------------------------------
# Default Primary Key
# --------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --------------------------------
# JDoodle API (optional)
# --------------------------------
JDOODLE_CLIENT_ID = env("JDOODLE_CLIENT_ID", default="")
JDOODLE_CLIENT_SECRET = env("JDOODLE_CLIENT_SECRET", default="")

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')


# Domain for email links
DOMAIN_NAME = "localhost:8000"


# Session Configuration
SESSION_COOKIE_AGE = 1800  # 30 minutes default
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Password Reset Configuration
PASSWORD_RESET_TIMEOUT = 10800  # 3 hours

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
