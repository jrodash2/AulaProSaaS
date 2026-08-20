from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from cuentas.models import Usuario
from instituciones.models import Institucion, UsuarioInstitucion

from .decorators import institucion_required, superusuario_required


@login_required
def inicio(request):
    if request.user.is_superuser:
        return redirect("core:global_dashboard")
    return redirect("core:institucion_dashboard")


@superusuario_required
def global_dashboard(request):
    context = {
        "total_instituciones": Institucion.objects.count(),
        "instituciones_activas": Institucion.objects.filter(activa=True).count(),
        "total_usuarios": Usuario.objects.count(),
        "ultimas_instituciones": Institucion.objects.order_by("-fecha_creacion")[:5],
    }
    return render(request, "core/global_dashboard.html", context)


@institucion_required
def institucion_dashboard(request):
    institucion = request.institucion
    datos_completos = bool(
        institucion.nombre
        and institucion.direccion
        and (institucion.email or institucion.telefono)
    )
    usuarios_configurados = (
        institucion.asignaciones_usuario.filter(activo=True).count() > 1
    )
    pasos = [datos_completos, usuarios_configurados, False, False, False]
    progreso = round(sum(pasos) / len(pasos) * 100)
    hora = timezone.localtime().hour
    saludo = (
        "Buenos días"
        if hora < 12
        else "Buenas tardes"
        if hora < 19
        else "Buenas noches"
    )
    return render(
        request,
        "core/institucion_dashboard.html",
        {
            "datos_completos": datos_completos,
            "usuarios_configurados": usuarios_configurados,
            "progreso_configuracion": progreso,
            "saludo": saludo,
        },
    )


@login_required
def sin_institucion(request):
    return render(request, "core/sin_institucion.html")


@require_POST
@login_required
def cambiar_institucion(request):
    if request.user.is_superuser:
        return redirect("core:global_dashboard")
    asignacion = UsuarioInstitucion.objects.filter(
        pk=request.POST.get("asignacion"),
        usuario=request.user,
        activo=True,
        institucion__activa=True,
    ).first()
    if not asignacion:
        messages.error(request, "No tienes acceso a la institución seleccionada.")
        return redirect("core:institucion_dashboard")
    request.session["asignacion_institucion_id"] = asignacion.pk
    messages.success(
        request, f"Ahora estás trabajando en {asignacion.institucion.nombre}."
    )
    return redirect("core:institucion_dashboard")


PROXIMAMENTE = {
    "academico": (
        "Gestión académica",
        "mortarboard",
        "carreras, ciclos, grados y cursos",
    ),
    "alumnos": ("Alumnos", "people", "expedientes e inscripciones"),
    "docentes": ("Docentes", "person-workspace", "personal docente y asignaciones"),
    "encargados": ("Encargados", "person-hearts", "familias y responsables"),
    "asistencia": ("Asistencia", "calendar-check", "seguimiento de asistencia"),
    "calificaciones": ("Calificaciones", "journal-check", "evaluaciones y resultados"),
    "tareas": ("Tareas", "clipboard-check", "actividades académicas"),
    "finanzas": ("Finanzas", "wallet2", "cuotas, pagos y estados de cuenta"),
    "reportes": ("Reportes", "bar-chart", "indicadores y reportes institucionales"),
    "comunicacion": ("Comunicación", "chat-dots", "avisos y comunicación escolar"),
    "usuarios": ("Usuarios", "person-gear", "usuarios y accesos institucionales"),
}


@institucion_required
def proximamente(request, modulo):
    configuracion = PROXIMAMENTE.get(modulo)
    if not configuracion:
        return redirect("core:institucion_dashboard")
    titulo, icono, descripcion = configuracion
    return render(
        request,
        "core/proximamente.html",
        {"titulo": titulo, "icono": icono, "descripcion": descripcion},
    )
