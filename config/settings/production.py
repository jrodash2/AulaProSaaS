import os
import urllib.parse

from .base import *  # noqa: F403

DEBUG = False
if not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY debe configurarse en producción.")
database_url = os.environ["DATABASE_URL"]
parsed = urllib.parse.urlparse(database_url)
DATABASES["default"] = {  # noqa: F405
    "ENGINE": "django.db.backends.postgresql",
    "NAME": parsed.path.lstrip("/"),
    "USER": parsed.username,
    "PASSWORD": parsed.password,
    "HOST": parsed.hostname,
    "PORT": parsed.port or 5432,
    "CONN_MAX_AGE": 60,
    "OPTIONS": {"sslmode": os.getenv("DB_SSLMODE", "require")},
}
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() == "true"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
CSRF_TRUSTED_ORIGINS = [url.strip() for url in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if url.strip()]
