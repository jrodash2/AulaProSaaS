# Inventario de rutas y permisos

Todas las rutas institucionales requieren autenticación, institución resuelta en servidor y filtrado por `request.institucion`. Los IDs de URL nunca seleccionan el tenant.

| Prefijo / namespace | Operación | Roles | Tenant |
|---|---|---|---|
| `/plataforma/`, `core` global | instituciones, usuarios, auditoría | superadmin | no aplica |
| `/institucion/` | configuración y usuarios | propietario/director/administrador; plataforma solo superadmin | sí |
| `/catalogos/` | catálogo global | superadmin | no aplica |
| `/academico/` | lectura y configuración académica | gestión: propietario/director/administrador | sí |
| `/alumnos/` | expedientes, familias, encargados, inscripciones | propietario/director/administrador/secretaría | sí |
| `/docentes/` | personal y asignaciones | propietario/director/administrador; lectura secretaría | sí |
| `/docentes/mis-clases/` | clases propias | docente | sí + asignación |
| `/asistencia/` | sesiones y registros | directivos, secretaría y docente limitado | sí + asignación |
| `/calificaciones/` | períodos, actividades y planillas | directivos; secretaría lectura; docente limitado | sí + asignación |
| `/tareas/` | tareas y adjuntos | directivos; secretaría lectura; docente limitado | sí + asignación |
| `/finanzas/` | cargos, pagos y recibos | directivos, contabilidad y secretaría según operación | sí |
| `/comunicacion/` | comunicaciones y avisos | gestión directivos/secretaría; docente solo clases; lectura destinatario | sí + notificación |
| `/reportes/` | reportes consolidados | matriz específica por reporte; docente limitado | sí + asignación |
| `/portal/` | información individual | padre/alumno | sí + relación personal |
| `/admin/` | administración técnica | staff/superuser Django | según política operativa |
| `/health/`, `/health/db/` | salud | público, sin datos sensibles | no expone tenant |

Las acciones de estado, publicación, anulación, cierre y marcado masivo usan POST. Las descargas de tareas, entregas y comunicaciones validan usuario, tenant y relación antes de abrir el storage.
