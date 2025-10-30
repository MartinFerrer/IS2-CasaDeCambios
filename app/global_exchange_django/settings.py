"""Django settings for global_exchange_django project.MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]ed by 'django-admin startproject' using Django 5.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
from decimal import Decimal
from pathlib import Path

import dj_database_url
from environ import Env

env = Env()

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = env.str("SECRET_KEY")

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.operaciones",
    "apps.panel_admin",
    "apps.presentacion",
    "apps.reportes",
    "apps.seguridad",
    "apps.stock",
    "apps.tauser",
    "apps.transacciones",
    "apps.usuarios",
    "django_q",
]
###########################################
## Django Q2 Configuration
###########################################

Q_CLUSTER = {
    "name": "GlobalExchange",
    "workers": 2,  # Número de procesos worker
    "timeout": 60,  # Timeout por tarea (segundos)
    "retry": 120,  # Reintentar después de (segundos)
    "queue_limit": 100,  # Límite de tareas en cola
    "bulk": 10,  # Procesar tareas en lotes
    "orm": "default",  # Usar base de datos Django
    "sync": False,  # Modo asíncrono
    "catch_up": False,  # No ejecutar tareas perdidas
    "poll": 1,  # Intervalo de verificación (segundos)
    "max_attempts": 3,  # Máximo de intentos por tarea
    "attempt_count": 1,  # Contador de intentos inicial
    "save_limit": 100,  # Guardar últimas 100 tareas completadas
    "success_ttl": 3600,  # Tiempo de vida registros exitosos (segundos)
    "recycle": 500,  # Reciclar workers después de N tareas
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.seguridad.middleware.ClienteMiddleware",
]

ROOT_URLCONF = "global_exchange_django.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "apps" / "operaciones" / "templates",
            BASE_DIR / "apps" / "panel_admin" / "templates",
            BASE_DIR / "apps" / "presentacion" / "templates",
            BASE_DIR / "apps" / "reportes" / "templates",
            BASE_DIR / "apps" / "seguridad" / "templates",
            BASE_DIR / "apps" / "stock" / "templates",
            BASE_DIR / "apps" / "tauser" / "templates",
            BASE_DIR / "apps" / "transacciones" / "templates",
            BASE_DIR / "apps" / "usuarios" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.seguridad.context_processors.user_context",
            ],
        },
    },
]

WSGI_APPLICATION = "global_exchange_django.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": env.str("SQL_ENGINE", default="django.db.backends.sqlite3"),
        "NAME": env.str("SQL_DATABASE", default=BASE_DIR / "db.sqlite3"),
        "USER": env.str("SQL_USER", default="user"),
        "PASSWORD": env.str("SQL_PASSWORD", default="password"),
        "HOST": env.str("SQL_HOST", default="localhost"),
        "PORT": env.str("SQL_PORT", default="5432"),
    },
}

# Override database config with DATABASE_URL if present (for Heroku)
database_url = os.environ.get("DATABASE_URL")
if database_url:
    DATABASES["default"] = dj_database_url.parse(database_url)

# Custom user model
# https://docs.djangoproject.com/en/3.0/topics/auth/customizing/#using-a-custom-user-model-when-starting-a-project

AUTH_USER_MODEL = "usuarios.Usuario"

# Validaciones comentadas para facilitar testing y desarrollo
AUTH_PASSWORD_VALIDATORS = [
    # {
    #     "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    # },
    # {
    #     "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    # },
    # {
    #     "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    # },
    # {
    #     "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    # },
]

LANGUAGE_CODE = "es-PY"  # Español de Paraguay

TIME_ZONE = "America/Asuncion"  # Zona horaria de Paraguay

USE_I18N = True
USE_L10N = True  # Habilitar localización de formatos de número, fecha, etc.
USE_TZ = True  # Habilitar soporte de zonas horarias

# Configurar zona horaria por defecto para templates
os.environ.setdefault('TZ', 'America/Asuncion')

USE_THOUSAND_SEPARATOR = True

# Forzar localización incluso en DEBUG=True
FORMAT_MODULE_PATH = [
    "global_exchange_django.locale",
]

# Directorio de locales personalizados
LOCALE_PATHS = [
    BASE_DIR / "global_exchange_django" / "locale",
]

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # For production collectstatic

# Whitenoise configuration for serving static files in production
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "usuarios.Usuario"


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"  # Cambiar si se usa otro proveedor
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = env.str("EMAIL_USER", default="NO_CONFIGURADO")
EMAIL_HOST_PASSWORD = env.str("EMAIL_PASSWORD", default="NO_CONFIGURADO")
DEFAULT_FROM_EMAIL = env.str("EMAIL_USER", default="NO_CONFIGURADO")

# CSRF trusted origins for reverse proxy
CSRF_TRUSTED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "https://localhost",
    "https://127.0.0.1",
    "http://localhost:8000",  # Dev environment
    "http://localhost:8080",  # Prod environment (nginx)
    "https://localhost:4443",  # Prod environment (nginx HTTPS)
    "https://global-exchange-2000226d6e82.herokuapp.com",
]

# Use X-Forwarded-Proto header to detect HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Use forwarded headers for correct URL generation behind proxy
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Custom error views for CSRF failures
CSRF_FAILURE_VIEW = "global_exchange_django.views.csrf_failure"

# Configuration for session cookie name (customizable via .env)
_session_cookie_from_env = env.str("SESSION_COOKIE_NAME", default=None)
if _session_cookie_from_env:
    SESSION_COOKIE_NAME = _session_cookie_from_env
else:
    if DEBUG:
        # Prevent the browser from overwriting the session cookie used in production
        SESSION_COOKIE_NAME = "sessionid_dev"
    else:
        SESSION_COOKIE_NAME = "sessionid"

if not DEBUG:
    # HTTPS settings
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False").lower() == "true"

    # Cookie security
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"
    CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() == "true"

    # Additional security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"


# =============================================================================
# STRIPE CONFIGURATION
# =============================================================================

# Stripe API Keys (con valores por defecto para CI/documentación)
STRIPE_PUBLISHABLE_KEY = env.str("STRIPE_PUBLISHABLE_KEY", default="pk_test_fake_key_for_ci")
STRIPE_SECRET_KEY = env.str("STRIPE_SECRET_KEY", default="sk_test_fake_key_for_ci")
STRIPE_WEBHOOK_SECRET = env.str("STRIPE_WEBHOOK_SECRET", default="")

# Configuración de comisiones Stripe
STRIPE_COMMISSION_RATE = Decimal("2.9")  # 2.9% comisión variable para pagos internacionales
STRIPE_FIXED_FEE_USD = Decimal("0.30")  # 0.30 USD comisión fija por transacción exitosa

# Configuración adicional de Stripe
STRIPE_CURRENCY_DEFAULT = "USD"  # Moneda por defecto para pagos internacionales
