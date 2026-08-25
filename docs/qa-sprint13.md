# QA Sprint 13

## Problemas encontrados y corregidos

1. **Permisos demasiado amplios:** padres y alumnos podían abrir directamente vistas administrativas de asistencia, calificaciones y tareas porque solo se excluía a Contabilidad. Se reemplazó por una matriz académica explícita.
2. **Acciones mutables respondían a GET:** cambios de estado académicos, reaperturas/anulaciones de asistencia, estados docentes/institucionales y publicaciones podían redirigir silenciosamente. Ahora usan `require_POST` y devuelven 405.
3. **Comando demo disponible en producción:** ahora se bloquea con `DEBUG=False`, salvo confirmación explícita.
4. **Configuración incompleta de producción:** se validan `ALLOWED_HOSTS`, comodines y variables PostgreSQL; HSTS tiene defaults seguros en producción.
5. **Sin health check/versionado:** se añadieron `/health/`, `/health/db/` y `APP_VERSION`.
6. **Doble submit:** formularios bloquean reenvíos y conservan el nombre/valor del botón accionado; el modal global limpia su acción al cerrar.
7. **Observabilidad insuficiente:** logging separado para `django` y `aulapro`, dirigido a stdout y controlado por nivel.
8. **Móvil:** acciones envuelven correctamente, tablas conservan scroll horizontal y botones críticos ocupan ancho útil en pantallas pequeñas.

## Rutas y permisos revisados

Se revisaron los namespaces de core, instituciones, catálogos, académico, alumnos, docentes, asistencia, calificaciones, tareas, finanzas, portal, comunicaciones y reportes. El inventario mantenible está en `docs/routes-permissions.md`.

## Multi-tenant e IDOR

Se auditaron `get_object_or_404`, `.get()` y `.filter()` de vistas institucionales. Los detalles de alumnos, familias, encargados, docentes, sesiones, notas, tareas, cargos, pagos, comunicaciones y portal parten de un queryset limitado al tenant o a relaciones autorizadas. Se agregaron pruebas transversales para roles, health y métodos HTTP.

## Rendimiento

Se conservaron `select_related`, `prefetch_related`, agregaciones y paginación del módulo de reportes. Permanecen algunos listados históricos con límites fijos (`[:200]`/`[:300]`); migrarlos a paginación uniforme es deuda técnica antes de instituciones de gran volumen.

## UI y archivos

No se encontraron referencias activas `href="#"`, `javascript:void(0)` ni restos de Inter. Los adjuntos académicos se descargan mediante vistas autorizadas. En producción el servidor web no debe exponer directamente las rutas privadas documentadas.

## Validación

- Suite inicial: 251 tests, correcta.
- Suite final: 259 tests ejecutados en 864.266 s, todos correctos.
- `check`: correcto.
- `makemigrations --check --dry-run`: sin cambios.
- `check --deploy` local: seis advertencias esperadas por `DEBUG=True`, clave de desarrollo y HTTPS desactivado.
- `check --deploy` con variables equivalentes a producción: sin incidencias.
- `collectstatic --noinput`: 129 archivos recopilados correctamente.

## Pendientes reales

- No existe almacenamiento privado separado físicamente; la separación depende de configuración del servidor y vistas autorizadas. Debe evaluarse S3 privado o storage dedicado al escalar.
- Algunos templates heredados están minificados en una sola línea, lo que dificulta mantenimiento.
- Faltan pruebas visuales automatizadas con navegador porque el entorno actual no incluye Chromium/Playwright.
- Antes del piloto deben probarse restauración, proxy HTTPS, permisos del filesystem y carga concurrente con PostgreSQL real.
