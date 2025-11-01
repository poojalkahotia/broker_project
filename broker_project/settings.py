import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Secret key from environment (Render) or fallback for local
SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key-for-local-dev')

DEBUG = True  # change to False after deployment

# ✅ Allow all during dev; restrict later to your Render domain
ALLOWED_HOSTS = ['*']

# ✅ Required for Render CSRF safety
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com']

# Applications
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "widget_tweaks",
    "brokerapp",
]

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ✅ serves static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "brokerapp.middleware.CurrentOrganizationMiddleware",
]

ROOT_URLCONF = "broker_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "brokerapp" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "brokerapp.context_processors.current_org",
            ],
        },
    },
]

WSGI_APPLICATION = "broker_project.wsgi.application"

# ✅ Database (PostgreSQL for both Local + Render)
# ✅ Database configuration (Local + Render)
if os.environ.get('DATABASE_URL'):
    # Render / Production
    DATABASES = {
        "default": dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    # Local PostgreSQL
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "broker_project_db",
            "USER": "postgres",
            "PASSWORD": "keshav1604",
            "HOST": "localhost",
            "PORT": "5432",
            "OPTIONS": {
                "sslmode": "disable"   # 👈 disable SSL locally
            },
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
#STATICFILES_DIRS = [BASE_DIR / "brokerapp" / "static"]
STATICFILES_DIRS = []
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Login / Logout
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
