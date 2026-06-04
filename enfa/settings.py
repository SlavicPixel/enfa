from pathlib import Path
import os
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = 'django-insecure-d+x+uko*s_&1c$5r+a+1kyo$4(he10o%12nkydm$ml)*9zmw0h'
DEBUG      = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "crispy_forms",
    "crispy_bootstrap5",
    "dashboard",
    "users",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'enfa.urls'

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = 'enfa.wsgi.application'

# PostgreSQL for users/auth
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME":     env("POSTGRES_DB",       default="finance_users"),
        "USER":     env("POSTGRES_USER",     default="finance_user"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="changeme"),
        "HOST":     env("POSTGRES_HOST",     default="localhost"),
        "PORT":     env("POSTGRES_PORT",     default="5432"),
    }
}

# MongoDB (accessed directly via pymongo, not Django ORM)
MONGO_URI = env("MONGO_URI",
    default="mongodb://admin:changeme@localhost:27017/finance?authSource=admin")
MONGO_DB  = env("MONGO_DB", default="finance")

# Model bundle path
MODEL_PATH = BASE_DIR / "model" / "volatility_model.pkl"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK          = "bootstrap5"

LOGIN_URL           = "/users/login/"
LOGIN_REDIRECT_URL  = "/"
LOGOUT_REDIRECT_URL = "/users/login/"