# Despliegue de producción

## Variables obligatorias

Use `.env.example` como inventario. En producción son obligatorias `DEBUG=False`, una `SECRET_KEY` aleatoria de al menos 50 caracteres, `ALLOWED_HOSTS` sin comodines y PostgreSQL mediante `DATABASE_URL` o todas las variables `DB_*`. Defina también `APP_VERSION` con el identificador del release.

## HTTPS

Active `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` y HSTS después de confirmar que todo el dominio funciona por HTTPS. Active `USE_X_FORWARDED_PROTO` únicamente cuando un proxy confiable establezca `X-Forwarded-Proto`; el proxy debe reemplazar, no aceptar del cliente, ese encabezado.

## Preparación de release

```bash
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check
```

Sirva `STATIC_ROOT` desde el servidor web. No publique directamente las carpetas privadas `media/tareas/` ni `media/comunicaciones/`: sus descargas pasan por vistas autorizadas. Fotografías y logos pueden servirse desde un almacenamiento público separado en un despliegue posterior.

## Aplicación

Ejecute Django mediante WSGI/ASGI detrás de un proxy HTTPS. No use `runserver`. Configure PostgreSQL con backups, conexiones cifradas cuando sea remoto y un usuario con privilegios limitados a la base de AulaPro.

## Logs y monitoreo

`LOG_LEVEL` controla los loggers `django` y `aulapro`; se escribe a stdout para que Passenger/systemd/plataforma lo capture. Nunca coloque secretos ni cargas completas de formularios en mensajes de log. Monitorice `/health/`; `/health/db/` añade una consulta `SELECT 1` y debe tener una frecuencia moderada.

## Datos demo

`crear_demo_aulapro` se bloquea con `DEBUG=False`. El flag `--allow-production-demo` existe solo para ambientes controlados y nunca debe usarse en el tenant real.
