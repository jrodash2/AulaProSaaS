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
)

MODULOS_POR_PLAN = {
    "INICIO": {"ACADEMICO", "ALUMNOS", "DOCENTES", "ASISTENCIA", "CALIFICACIONES"},
    "CRECE": {"ACADEMICO", "ALUMNOS", "DOCENTES", "ASISTENCIA", "CALIFICACIONES", "TAREAS", "PORTAL", "COMUNICACIONES"},
    "PRO": {codigo for codigo, *_ in MODULOS_OFICIALES},
    "EMPRESA": {codigo for codigo, *_ in MODULOS_OFICIALES},
}
