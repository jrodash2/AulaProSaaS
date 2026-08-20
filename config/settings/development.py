import os

from .base import *  # noqa: F403

DEBUG = os.getenv("DEBUG", "True").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "development-only-insecure-key-change-me")
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")]

if os.getenv("DATABASE_URL"):
    import urllib.parse

    parsed = urllib.parse.urlparse(os.environ["DATABASE_URL"])
    DATABASES["default"] = {  # noqa: F405
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username,
        "PASSWORD": parsed.password,
        "HOST": parsed.hostname,
        "PORT": parsed.port or 5432,
    }
else:
    DATABASES["default"] = {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}  # noqa: F405
