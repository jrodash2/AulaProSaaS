# Backup y restauración

## PostgreSQL

Backup cifrado fuera del servidor de aplicación:

```bash
pg_dump --format=custom --no-owner --file=aulapro-$(date +%F).dump "$DATABASE_URL"
```

Restauración sobre una base vacía de prueba:

```bash
createdb aulapro_restore_test
pg_restore --clean --if-exists --no-owner --dbname=aulapro_restore_test aulapro-AAAA-MM-DD.dump
python manage.py check
```

## Media

Copie `MEDIA_ROOT` conservando rutas y permisos. Excluya temporales, pero incluya logos, fotografías y documentos privados. Use almacenamiento cifrado y controle el acceso a los backups.

## Frecuencia y retención

- Base de datos: diaria; más frecuente si el volumen de pagos/notas lo requiere.
- Media: diaria e incremental, además de copia completa semanal.
- Retención sugerida inicial: 7 diarias, 4 semanales y 6 mensuales, ajustada a la política institucional.

## Prueba de restauración

Pruebe mensualmente una restauración conjunta de DB y media en un entorno aislado. Verifique login, conteos, un recibo, una tarea con adjunto y un boletín. Un archivo que nunca fue restaurado no se considera un backup validado.
