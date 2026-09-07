"""Catálogo editorial, derivado de las opciones visibles en el sidebar de AulaPro.

El texto detallado vive en templates controlados; aquí solo se declara navegación,
búsqueda y disponibilidad por módulo SaaS.
"""

def s(slug, titulo, resumen, *, modulo=None, acciones="Ver, filtrar y consultar"):
    return {"slug": slug, "titulo": titulo, "resumen": resumen,
            "keywords": f"{titulo} {resumen} {acciones}", "modulo": modulo,
            "acciones": [a.strip() for a in acciones.split(",")]}

PRIMEROS = [
    s("primeros-pasos", "Primeros pasos", "Inicia sesión, reconoce el menú, cambia el tema, identifica tu institución, abre tu perfil y cierra sesión.", acciones="Iniciar sesión, Cambiar tema, Perfil, Cerrar sesión"),
    s("dashboard", "Dashboard", "Interpreta las tarjetas, indicadores y accesos que aparecen al iniciar."),
    s("menu-lateral", "Menú lateral", "Ubica cada módulo disponible, abre submenús y vuelve al inicio."),
]
CIERRE = [s("botones-estados", "Botones, acciones y estados", "Reconoce acciones disponibles y confirma con cuidado los cambios delicados.", acciones="Nuevo, Guardar, Cancelar, Ver, Editar, Eliminar, Confirmar"), s("buenas-practicas", "Buenas prácticas y preguntas frecuentes", "Consejos de seguridad, calidad de datos, reportes y respuestas a dudas frecuentes.")]

def build(titulo, descripcion, items):
    return {"titulo": titulo, "descripcion": descripcion, "secciones": PRIMEROS + items + CIERRE}

MANUALES = {
"superadmin": build("Manual del Superadministrador", "Administra la plataforma AulaPro y sus instituciones.", [
 s("instituciones", "Instituciones", "Crea, edita y activa o desactiva instituciones.", acciones="Nueva institución, Ver, Editar, Activar, Desactivar"), s("usuarios", "Usuarios globales", "Consulta usuarios y asigna su institución."), s("saas", "Planes, suscripciones, solicitudes y uso", "Configura módulos, límites y consulta el uso comercial.", acciones="Nuevo, Editar, Activar, Aprobar, Rechazar"), s("catalogo", "Catálogo académico", "Gestiona el catálogo académico global."), s("auditoria", "Auditoría", "Consulta eventos y filtros de trazabilidad sin modificar registros."), s("configuracion", "Configuración y Centro Demo", "Revisa el sistema y practica en el entorno de demostración."),
]),
"propietario": build("Manual del Propietario", "Guía completa de administración institucional.", [
 s("academico", "Académico y cierre de ciclo", "Gestiona oferta, ciclos, jornadas, grados, secciones y cursos; revisa y confirma resultados antes de cerrar.", modulo="ACADEMICO", acciones="Nuevo, Editar, Generar resultados, Confirmar, Cerrar ciclo"), s("alumnos", "Alumnos e inscripciones", "Gestiona estudiantes, inscripciones, reinscripciones, familias, encargados e importaciones.", modulo="ALUMNOS", acciones="Nuevo estudiante, Nueva inscripción, Ver, Editar, Importar"), s("expediente", "Expedientes", "Controla completitud y documentos pendientes, entregados, aprobados, rechazados, vencidos o no aplicables.", modulo="EXPEDIENTE", acciones="Subir, Descargar, Reemplazar, Aprobar, Rechazar, No aplica"), s("docentes", "Docentes", "Gestiona personal, asignaciones y carga académica.", modulo="DOCENTES"), s("asistencia", "Asistencia", "Toma asistencia, consulta sesiones, justificaciones y reportes.", modulo="ASISTENCIA", acciones="Tomar asistencia, Guardar, Ver historial"), s("calificaciones", "Calificaciones", "Configura períodos y actividades, completa planillas y genera boletines.", modulo="CALIFICACIONES"), s("tareas", "Tareas", "Consulta, crea y reporta tareas próximas.", modulo="TAREAS"), s("horarios", "Horarios", "Configura aulas, bloques y clases; detecta conflictos y consulta horarios.", modulo="HORARIOS", acciones="Nuevo, Editar, Imprimir, Exportar"), s("seguimiento", "Seguimiento", "Gestiona casos, categorías, notas, compromisos y cierres con confidencialidad.", modulo="SEGUIMIENTO"), s("admisiones", "Admisiones", "Procesa solicitudes, documentos, entrevistas, evaluaciones, decisiones y conversión a alumno.", modulo="ADMISIONES", acciones="Evaluar, Aprobar, Lista de espera, Rechazar, Convertir"), s("rrhh", "Recursos Humanos", "Gestiona áreas, puestos, empleados, contratos, expedientes y permisos.", modulo="RRHH"), s("finanzas", "Finanzas", "Gestiona cargos, pagos parciales, saldos, solvencias, morosidad y recibos.", modulo="FINANZAS", acciones="Generar cargos, Registrar pago, Imprimir recibo"), s("comunicaciones", "Comunicación", "Crea, programa y consulta comunicaciones y avisos.", modulo="COMUNICACIONES"), s("reportes", "Reportes", "Filtra e interpreta reportes académicos, administrativos y financieros.", modulo="REPORTES", acciones="Filtrar, Exportar, Imprimir"), s("configuracion", "Usuarios, configuración y plan", "Administra usuarios, datos institucionales, módulos y suscripción."),
]),
"director": build("Manual del Director", "Supervisa la gestión académica y los resultados institucionales.", []),
"administrador": build("Manual del Administrador", "Gestiona usuarios, personas, módulos y configuración institucional.", []),
"secretaria": build("Manual de Secretaría", "Gestiona alumnos, inscripciones, expedientes y admisiones.", []),
"contabilidad": build("Manual de Contabilidad", "Gestiona cargos, pagos, recibos, morosidad y reportes financieros.", []),
"docente": build("Manual del Docente", "Organiza clases, asistencia, calificaciones, tareas y seguimiento.", [s("mis-clases", "Mis clases y horario", "Consulta tus clases, la carga asignada y tu horario.", modulo="DOCENTES"), s("asistencia", "Asistencia", "Selecciona una clase, registra cada estado, guarda y consulta el historial.", modulo="ASISTENCIA", acciones="Tomar asistencia, Guardar, Historial"), s("seguimiento", "Seguimiento", "Registra y consulta casos autorizados respetando la confidencialidad.", modulo="SEGUIMIENTO"), s("calificaciones", "Actividades y planillas", "Crea actividades y registra calificaciones en las planillas disponibles.", modulo="CALIFICACIONES", acciones="Nueva actividad, Guardar calificaciones"), s("tareas", "Tareas", "Consulta tareas, crea una nueva y revisa las próximas.", modulo="TAREAS", acciones="Nueva tarea, Editar, Ver"), s("reportes-avisos", "Mis reportes y avisos", "Consulta reportes disponibles y comunicaciones recibidas.")]),
"padre": build("Manual para Padre o Encargado", "Consulta de forma segura la información de tus hijos.", [s("mis-hijos", "Mis hijos", "Cambia el estudiante seleccionado y revisa su resumen.", modulo="PORTAL"), s("academico", "Asistencia, calificaciones y tareas", "Consulta registros académicos visibles para el hijo seleccionado.", modulo="PORTAL"), s("finanzas", "Estado de cuenta y recibos", "Revisa cargos, deuda y recibos disponibles.", modulo="FINANZAS", acciones="Ver estado de cuenta, Descargar recibo"), s("avisos", "Avisos", "Lee comunicaciones dirigidas a la familia.", modulo="COMUNICACIONES")]),
"alumno": build("Manual del Alumno", "Consulta clases, tareas, calificaciones y asistencia.", [s("mis-clases", "Mis clases", "Consulta las clases asociadas a tu inscripción.", modulo="PORTAL"), s("tareas", "Tareas", "Revisa instrucciones, fechas y estados de tus tareas.", modulo="TAREAS"), s("calificaciones", "Calificaciones", "Consulta resultados publicados.", modulo="CALIFICACIONES"), s("asistencia", "Asistencia", "Consulta tu historial de asistencia.", modulo="ASISTENCIA"), s("avisos", "Avisos", "Lee comunicaciones disponibles.", modulo="COMUNICACIONES")]),
}
# Los roles institucionales comparten únicamente módulos que su menú real expone.
shared = MANUALES["propietario"]["secciones"][3:-2]
for role, allowed in {
 "director": {"academico","alumnos","expediente","docentes","asistencia","calificaciones","tareas","horarios","seguimiento","admisiones","rrhh","finanzas","comunicaciones","reportes","configuracion"},
 "administrador": {"academico","alumnos","expediente","docentes","asistencia","calificaciones","tareas","horarios","seguimiento","admisiones","rrhh","finanzas","comunicaciones","reportes","configuracion"},
 "secretaria": {"academico","alumnos","expediente","asistencia","horarios","admisiones","comunicaciones","reportes"},
 "contabilidad": {"finanzas","reportes"},
}.items():
    MANUALES[role]["secciones"] = PRIMEROS + [dict(x) for x in shared if x["slug"] in allowed] + CIERRE
