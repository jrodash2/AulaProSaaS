# Entorno demo

Con `DEBUG=True` ejecute:

```bash
python manage.py crear_demo_aulapro
```

La contraseña de los perfiles demostrativos es `AulaProDemo2026!`. El comando es idempotente y crea datos académicos, asistencia, notas, tareas, finanzas, comunicaciones y reportes para los roles demo. No se ejecuta durante el arranque ni mediante migraciones.

Con `DEBUG=False` el comando falla por defecto. `--allow-production-demo` requiere una decisión explícita y solo es aceptable en un ambiente de demostración aislado.
