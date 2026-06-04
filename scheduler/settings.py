"""
Minimal Django settings for the scheduler container.
Only includes what the pipeline actually needs — no web apps, no auth.
"""
import os
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = "scheduler-secret-key"
DEBUG = False

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "dashboard",
]

# PostgreSQL not needed by scheduler but Django requires DATABASES
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME":   BASE_DIR / "db.sqlite3",
    }
}

MONGO_URI = env("MONGO_URI",
    default="mongodb://admin:changeme@mongodb:27017/finance?authSource=admin")
MONGO_DB  = env("MONGO_DB", default="finance")