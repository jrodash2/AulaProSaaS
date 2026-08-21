# Matriz de vistas AulaPro

Auditoría realizada durante la fase de normalización. `—` indica que la operación no aplica o se gestiona dentro de una vista compuesta.

| Entidad | Lista | Detalle | Crear | Editar | Estado / acción | Navegación |
|---|---:|---:|---:|---:|---:|---|
| Institución | ✓ | ✓ | ✓ | ✓ | ✓ | Plataforma |
| Usuario institucional | ✓ | ✓ | ✓ | ✓ | ✓ | Sistema / Usuarios |
| Nivel educativo | ✓ | ✓ | ✓ | ✓ | ✓ | Catálogo académico |
| Tipo de carrera | ✓ | ✓ | ✓ | ✓ | ✓ | Catálogo académico |
| Área curricular | ✓ | ✓ | ✓ | ✓ | ✓ | Catálogo académico |
| Curso catálogo | ✓ | ✓ | ✓ | ✓ | ✓ | Catálogo académico |
| Carrera | ✓ | ✓ | ✓ | ✓ | ✓ | Catálogo académico |
| Pensum | desde carrera | editor | ✓ | ✓ | duplicar / estados internos | Carrera |
| Ciclo escolar | ✓ | ✓ | ✓ | ✓ | establecer actual | Académico |
| Jornada | ✓ | ✓ | ✓ | ✓ | ✓ | Académico |
| Oferta académica | ✓ | ✓ | ✓ | — | ✓ | Académico |
| Grado institucional | agrupada | ✓ | desde pensum | — | — | Grados y secciones |
| Sección | agrupada | ✓ | ✓ | ✓ | ✓ | Grado |
| Curso institucional | ✓ | ✓ | ✓ | ✓ | ✓ | Académico |
| Alumno | ✓ | ✓ | ✓ | ✓ | inscripción / retiro | Alumnos |
| Familia | ✓ | ✓ | ✓ | ✓ | activa en modelo | Alumnos |
| Encargado | ✓ | ✓ | ✓ | ✓ | activo en modelo | Alumnos |
| Inscripción | ✓ | ✓ | ✓ | ✓ | retirar | Alumnos |
| Importación | ✓ | ✓ | ✓ / vista previa | — | confirmar | Alumnos |
| Docente | ✓ | ✓ | ✓ | ✓ | acceso / estado | Docentes |
| Asignación docente | ✓ | ✓ | ✓ | ✓ | finalizar / reactivar | Docentes |
| Clase docente | Mis clases | ✓ | desde asignación | — | — | Portal docente |

## Pantallas futuras declaradas

Asistencia, calificaciones, tareas, finanzas, reportes y comunicación conservan una landing AulaPro de “Módulo próximamente”. No contienen enlaces a Django Admin ni controles que aparenten ejecutar una función inexistente.

Los templates `403.html`, `404.html` y `500.html` son puntos de entrada implícitos de los handlers de error configurados; no son templates huérfanos.
