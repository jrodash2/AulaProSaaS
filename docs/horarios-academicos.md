# Horarios académicos

El módulo `HORARIOS` organiza bloques por jornada, aulas y clases semanales. Cada clase usa una `AsignacionDocente` como fuente del curso y docente, y queda asociada a institución, ciclo, jornada y sección.

## Reglas de integridad

- Solo se editan ciclos en planificación o activos; los horarios cerrados son históricos y de solo lectura.
- Los bloques deben tener fin posterior al inicio y no pueden traslaparse dentro de una jornada.
- El backend bloquea simultaneidad de sección, docente o aula, incluso cuando los bloques tienen horas superpuestas.
- La institución de aula, bloque, sección y asignación debe coincidir con la del horario.
- La completitud compara las clases activas con `periodos_semanales` de cada curso activo.

## Uso

Desde **Académico → Horarios** se configuran bloques y aulas, se selecciona una sección y se asignan clases desde las celdas disponibles. El horario se puede imprimir con el navegador o exportar a XLSX. Docentes consultan **Mi horario**; padres y alumnos acceden únicamente al horario de su estudiante autorizado.
