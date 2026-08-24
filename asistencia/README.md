# Asistencia

El módulo mantiene separadas las sesiones **generales** de las sesiones **por curso**. Una sesión genera sus registros desde las inscripciones activas de la sección y comienza en `SIN_MARCAR`; no puede cerrarse hasta completar todos los registros.

## Porcentaje general del alumno

El porcentaje general usa exclusivamente registros de sesiones `GENERAL` en estado `CERRADA` correspondientes al alumno. `PRESENTE` y `TARDE` cuentan como asistencia; `AUSENTE` no cuenta. Una ausencia justificada continúa siendo ausencia física y se presenta por separado. Las sesiones por curso y las sesiones anuladas no se mezclan en este porcentaje.

```text
(PRESENTE + TARDE) / TOTAL DE SESIONES GENERALES CERRADAS * 100
```

Toda consulta del módulo se limita a la institución activa. Los docentes solo acceden a cursos asignados y, para asistencia general, a las secciones donde son guía.
