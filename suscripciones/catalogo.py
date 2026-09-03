MODULOS_OFICIALES = (
    ("ACADEMICO", "Académico", 1, "Gestión de ciclos, grados, secciones y cursos.", "bi-mortarboard"),
    ("ALUMNOS", "Alumnos", 2, "Expedientes, inscripciones, familias y encargados.", "bi-person-vcard"),
    ("DOCENTES", "Docentes", 3, "Personal docente, asignaciones y carga académica.", "bi-person-workspace"),
    ("ASISTENCIA", "Asistencia", 4, "Control diario y reportes de asistencia.", "bi-calendar-check"),
    ("CALIFICACIONES", "Calificaciones", 5, "Períodos, evaluaciones, notas y boletines.", "bi-card-checklist"),
    ("TAREAS", "Tareas", 6, "Tareas, entregas y seguimiento.", "bi-list-task"),
    ("FINANZAS", "Finanzas", 7, "Cargos, pagos, recibos y estados de cuenta.", "bi-wallet2"),
    ("PORTAL", "Portal familiar", 8, "Acceso seguro para padres y alumnos.", "bi-people"),
    ("COMUNICACIONES", "Comunicaciones", 9, "Avisos y notificaciones institucionales.", "bi-megaphone"),
    ("REPORTES", "Reportes", 10, "Analítica y reportes consolidados.", "bi-bar-chart"),
    ("EXPEDIENTE", "Expediente digital", 11, "Gestión de documentos y requisitos de estudiantes.", "bi-folder2-open"),
    ("HORARIOS", "Horarios académicos", 12, "Planificación semanal de clases, docentes, secciones y aulas.", "bi-calendar-week"),
    ("SEGUIMIENTO", "Seguimiento estudiantil", 13, "Incidencias, reconocimientos, compromisos y seguimiento del alumno.", "bi-heart-pulse"),
    ("ADMISIONES", "Admisiones", 14, "Gestión de aspirantes, solicitudes, entrevistas y procesos de ingreso.", "bi-person-plus"),
    ("RRHH", "Recursos Humanos", 15, "Gestión de empleados, contratos, documentos y permisos del personal.", "bi-briefcase"),
)

MODULOS_POR_PLAN = {
    "INICIO": {"ACADEMICO", "ALUMNOS", "DOCENTES", "ASISTENCIA", "CALIFICACIONES"},
    "CRECE": {"ACADEMICO", "ALUMNOS", "DOCENTES", "ASISTENCIA", "CALIFICACIONES", "TAREAS", "PORTAL", "COMUNICACIONES", "HORARIOS"},
    "PRO": {codigo for codigo, *_ in MODULOS_OFICIALES},
    "EMPRESA": {codigo for codigo, *_ in MODULOS_OFICIALES},
}
