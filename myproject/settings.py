"""
Django settings for myproject project.
"""

from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


# -----------------------
# SECURITY
# -----------------------
SECRET_KEY = 'django-insecure-!cofqfh9#v9d_bpck*g98stlug(r6v)p+e+tu!%!dg(o*i=!@2'
DEBUG = True
ALLOWED_HOSTS = ['*']

# CSRF Settings
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000']
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SECURE = False


# -----------------------
# CUSTOM USER
# -----------------------
AUTH_USER_MODEL = 'myapp.CustomUser'


# -----------------------
# APPLICATIONS
# -----------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'myapp',
]


# -----------------------
# MIDDLEWARE
# -----------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# -----------------------
# URLS & WSGI
# -----------------------
ROOT_URLCONF = 'myproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],   # centralized templates folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.csrf',
                'myapp.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'myproject.wsgi.application'


# -----------------------
# DATABASE
# -----------------------
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL')
    )
}


# -----------------------
# PASSWORD VALIDATION
# -----------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# -----------------------
# LANGUAGE & TIMEZONE
# -----------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'   # para PH time
USE_I18N = True
USE_TZ = True


# -----------------------
# STATIC FILES
# -----------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# -----------------------
# MEDIA FILES
# -----------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Default backend
]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = "YOUR_CLIENT_ID"
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = "YOUR_CLIENT_SECRET"

# Login/Logout URLs
LOGIN_URL = '/'  # Redirect to home page (index) for login
LOGIN_REDIRECT_URL = '/dashboard/'  # After successful login
LOGOUT_REDIRECT_URL = '/'  # After logout
