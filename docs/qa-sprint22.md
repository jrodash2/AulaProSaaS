# Sprint 22 — QA integral y estabilización

Fecha de auditoría: 3 de septiembre de 2026.

## Estado inicial

La validación inicial encontró 414 pruebas verdes (`Ran 414 tests in 35.132s`, `OK`), migraciones aplicadas y ningún cambio de esquema pendiente. El inventario del resolver contiene 866 patrones, incluidos 533 del administrador de Django y 333 patrones de la aplicación.

## Hallazgos y prioridad

| Prioridad | Hallazgo | Corrección / estado |
|---|---|---|
| P0 | No se detectaron fugas tenant ni pérdida de datos reproducible. | Los tests IDOR existentes continúan verdes; los querysets sensibles revisados parten de `request.institucion` o de helpers ya acotados. |
| P1 | Crear seguimiento producía `FieldError` al consultar `Docente.activo`, campo inexistente. | Corregido con `estado=Docente.Estado.ACTIVO`, conservando el docente histórico en edición. |
| P1 | `crear_demo_aulapro` fallaba con `NameError: secretaria is not defined`. | Corregida la asignación explícita desde el diccionario de usuarios; dos ejecuciones consecutivas conservaron conteos 12/3/4/10/5. |
| P2 | Formularios de Seguimiento duplicaban el sistema de estilos. | Migrados a `AulaProFormMixin`, imports explícitos y querysets tenant-safe. |
| P2 | Código reciente contiene archivos muy comprimidos y algunos imports comodín. | Se refactorizó el formulario intervenido; el resto queda como deuda controlada para evitar cambios masivos de riesgo. |
| P3 | No existe navegador gráfico en el contenedor para matriz visual completa. | Mantener la verificación manual de responsive, dark mode y consola en staging. |

## Matriz de cobertura

| Módulo | Flujo probado | Roles | Resultado | Correcciones | Pendiente manual |
|---|---|---|---|---|---|
| Core / onboarding | Dashboard, contexto institucional, health y health/db | superadmin y roles institucionales | OK automatizado | Sin cambios | Recorrido visual en staging |
| Académico | Ciclos, oferta, cierre, resultados y ciclo cerrado | propietario, director, administración | OK automatizado | Sin cambios | Validar impresión con datos reales |
| Alumnos / expediente | CRUD, inscripción, reinscripción, archivos e IDOR | administración, secretaría, portal | OK automatizado | Sin cambios | Cámara móvil para cargas |
| Docentes | CRUD, asignaciones, guía y estado | dirección, docente | OK automatizado | Enum verificado | Recorrido visual |
| Asistencia | Sesiones, registros y permisos | dirección, docente | OK automatizado | Sin cambios | Prueba concurrencia piloto |
| Calificaciones / tareas | Edición, estados, portal y ciclo cerrado | dirección, docente, portal | OK automatizado | Sin cambios | Validar autosave con red lenta |
| Finanzas | Cargos, pagos, saldos, Decimal y permisos | propietario, contabilidad | OK automatizado | Sin cambios | Conciliación piloto |
| Portal | Relación padre/alumno e IDOR | padre, alumno | OK automatizado | Sin cambios | 375/768 px en dispositivos |
| Horarios | Conflictos, aulas, docente y sección | administración, docente | OK automatizado | Sin cambios | Impresión Carta |
| Seguimiento | Casos, confidencialidad, formularios y archivos | dirección, docente, portal | OK automatizado | Filtro Docente y mixin | Revisión de lenguaje institucional |
| Admisiones | Público, token, evaluación y conversión | secretaría, dirección | OK automatizado | Demo reparada | Prueba de enlace en correo real |
| RRHH | Empleados, contratos, documentos, permisos y datos sensibles | dirección, secretaría, docente | OK automatizado | Enums auditados | Revisión legal de políticas |
| Suscripciones / reportes | Gates SaaS, límites y XLSX | propietario y roles autorizados | OK automatizado | Sin cambios | Abrir XLSX en Office/LibreOffice |

## Seguridad y archivos

- Las búsquedas IDOR revisadas usan filtros institucionales o querysets previamente autorizados.
- Los endpoints mutables cubiertos mantienen POST y CSRF; la auditoría estática no encontró formularios POST sin `{% csrf_token %}`.
- Los adjuntos sensibles siguen descargándose mediante vistas con autorización. `MEDIA_URL` solo se sirve desde Django con `DEBUG=True`.
- Producción exige secreto, hosts y base de datos configurados; activa SSL, cookies seguras y HSTS por defecto.

## Rendimiento

Se verificó el uso existente de `select_related`, `prefetch_related`, agregaciones y paginación en listados/reportes críticos. No se añadió una migración especulativa: los índices actuales cubren filtros tenant/estado principales y la suite conserva compatibilidad SQLite/PostgreSQL.

## Resultado final

No quedan P0 ni P1 conocidos. Los P2/P3 restantes son revisión visual, pruebas sobre infraestructura real y refactor incremental; no bloquean la prueba piloto técnica, pero deben completarse antes del despliegue productivo definitivo.
