# Inventario del Centro de Manuales

Inventario contrastado con `templates/partials/sidebar.html`. Las acciones enumeradas son las que las vistas presentan al rol; los módulos condicionados por plan también se filtran en **Mi manual**.

| Rol | Menú / vista | Botones o acciones principales documentadas | Capítulo | Cubierto |
|---|---|---|---|---|
| Superadministrador | Inicio global, Instituciones y Usuarios | Nuevo, Ver, Editar, activar/desactivar, asignar | instituciones / usuarios | Sí |
| Superadministrador | Dashboard SaaS, Planes, Suscripciones, Solicitudes, Uso | Nuevo, Editar, activar, aprobar/rechazar, filtrar | saas | Sí |
| Superadministrador | Catálogo, Auditoría, Configuración, Centro Demo | Ver, filtrar, editar configuración | catalogo / auditoria / configuracion | Sí |
| Propietario, Director, Administrador, Secretaría | Académico: oferta, ciclos, jornadas, grados, secciones y cursos | Nuevo, Editar, Guardar, generar/confirmar/cerrar | academico | Sí |
| Propietario, Director, Administrador, Secretaría | Alumnos, inscripciones, reinscripciones, familias, encargados e importaciones | Nuevo, Ver, Editar, Guardar, Importar | alumnos | Sí |
| Propietario, Director, Administrador, Secretaría | Expedientes | Subir, Descargar, Reemplazar, Aprobar, Rechazar, No aplica | expediente | Sí |
| Propietario, Director, Administrador | Docentes, asignaciones y carga | Nuevo, Ver, Editar, asignar | docentes | Sí |
| Gestión institucional y Docente | Asistencia, sesiones, justificaciones y reportes | Tomar asistencia, Guardar, Historial | asistencia | Sí |
| Gestión institucional y Docente | Calificaciones, períodos, actividades, planillas y boletines | Nueva actividad, Guardar calificaciones, filtrar | calificaciones | Sí |
| Gestión institucional y Docente | Tareas, próximas y reportes | Nueva tarea, Ver, Editar | tareas | Sí |
| Gestión institucional y Docente | Casos, compromisos y categorías | Nuevo, Ver, Editar, cerrar | seguimiento | Sí |
| Gestión institucional | Admisiones, solicitudes y lista de espera | Evaluar, Aprobar, Espera, Rechazar, Convertir | admisiones | Sí |
| Gestión institucional | RRHH: empleados, contratos, expedientes, permisos, áreas y puestos | Nuevo, Ver, Editar | rrhh | Sí |
| Gestión institucional | Horarios | Nuevo, Editar, Imprimir, Exportar | horarios | Sí |
| Propietario, Director, Administrador, Contabilidad | Finanzas: cargos, pagos, generación, estados y reportes | Generar, Registrar pago, Imprimir recibo | finanzas | Sí |
| Gestión institucional | Comunicación: resumen, comunicaciones, nueva, programadas y reportes | Nueva, Programar, Ver | comunicaciones | Sí |
| Roles institucionales según permisos | Reportes visibles en el sidebar | Filtrar, Exportar, Imprimir | reportes | Sí |
| Docente | Inicio, Mis clases, Mi horario, información laboral | Ver | mis-clases | Sí |
| Padre / encargado | Inicio, Mis hijos, resumen académico, cuenta y recibos | Cambiar hijo, Ver, Descargar recibo | mis-hijos / academico / finanzas | Sí |
| Alumno | Inicio, Avisos, Mis clases, Tareas, Calificaciones, Asistencia, Perfil | Ver | capítulos homónimos | Sí |
| Todos | Perfil, tema, institución y sesión | Cambiar tema, Perfil, Cerrar sesión | primeros-pasos | Sí |
| Todos | Centro de manuales | Buscar, Contenido, Copiar enlace, Imprimir | todos | Sí |

## Cobertura

Las opciones visibles del sidebar tienen un capítulo para cada rol que puede verlas. Cada capítulo incluye una ilustración HTML accesible, explicación de la vista, procedimiento, resultado esperado, acciones, estados, consejos y advertencias. El contenido sensible se sustituye por ejemplos neutros.
