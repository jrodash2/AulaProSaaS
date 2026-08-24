from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from auditoria.models import EventoAuditoria
from cuentas.forms import AulaProPasswordChangeForm, PerfilForm

from cuentas.models import Usuario
from instituciones.models import Institucion

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
    from academico.models import CicloEscolar, JornadaInstitucion, OfertaAcademica
    ciclo = CicloEscolar.objects.filter(institucion=request.institucion, es_actual=True).first()
    if request.asignacion_institucion.rol == "DOCENTE":
        from docentes.models import Docente
        from tareas.models import Tarea
        from django.utils import timezone
        docente = Docente.objects.filter(institucion=request.institucion, usuario=request.user).first()
        clases = docente.asignaciones.filter(ciclo=ciclo, activa=True).select_related("curso", "grado", "seccion") if docente and ciclo else []
        tareas_proximas = Tarea.objects.filter(institucion=request.institucion, asignacion_docente__docente=docente, estado=Tarea.Estado.PUBLICADA, fecha_limite__gte=timezone.now()).select_related("curso", "seccion").order_by("fecha_limite")[:5] if docente else []
        return render(request, "docentes/dashboard.html", {"docente": docente, "ciclo_actual": ciclo, "clases": clases, "tareas_proximas": tareas_proximas})
    from alumnos.models import Alumno, Inscripcion
    from docentes.models import Docente
    from asistencia.models import RegistroAsistencia, SesionAsistencia
    from finanzas.models import Cargo, Pago
    from decimal import Decimal
    from django.db.models import Sum
    from django.utils import timezone
    registros_hoy = RegistroAsistencia.objects.filter(institucion=request.institucion, sesion__fecha=timezone.localdate(), sesion__tipo=SesionAsistencia.Tipo.GENERAL).exclude(sesion__estado=SesionAsistencia.Estado.ANULADA).exclude(estado=RegistroAsistencia.Estado.SIN_MARCAR)
    total_asistencia_hoy = registros_hoy.count()
    asistieron_hoy = registros_hoy.filter(estado__in=(RegistroAsistencia.Estado.PRESENTE, RegistroAsistencia.Estado.TARDE)).count()
    hoy = timezone.localdate()
    ingresos_mes = Pago.objects.filter(institucion=request.institucion, estado=Pago.Estado.CONFIRMADO, fecha_pago__year=hoy.year, fecha_pago__month=hoy.month).aggregate(total=Sum("monto"))["total"] or Decimal("0")
    cuentas_por_cobrar = sum((cargo.saldo for cargo in Cargo.objects.filter(institucion=request.institucion).exclude(estado=Cargo.Estado.ANULADO)), Decimal("0"))
    context = {
        "ciclo_actual": ciclo,
        "total_alumnos_activos": Alumno.objects.filter(institucion=request.institucion, estado=Alumno.Estado.ACTIVO).count(),
        "inscripciones_actuales": Inscripcion.objects.filter(institucion=request.institucion, ciclo=ciclo, estado=Inscripcion.Estado.ACTIVA).count() if ciclo else 0,
        "tiene_estudiantes": Alumno.objects.filter(institucion=request.institucion).exists(),
        "total_docentes_activos": Docente.objects.filter(institucion=request.institucion, estado=Docente.Estado.ACTIVO).count(),
        "tiene_docentes": Docente.objects.filter(institucion=request.institucion, estado=Docente.Estado.ACTIVO).exists(),
        "tiene_ciclo": CicloEscolar.objects.filter(institucion=request.institucion).exists(),
        "tiene_oferta": OfertaAcademica.objects.filter(institucion=request.institucion, activa=True).exists(),
        "tiene_jornadas": JornadaInstitucion.objects.filter(institucion=request.institucion, activa=True).exists(),
        "tiene_usuarios": request.institucion.asignaciones_usuario.filter(activo=True).exists(),
        "asistencia_hoy": round(asistieron_hoy * 100 / total_asistencia_hoy, 1) if total_asistencia_hoy else None,
        "ingresos_mes": ingresos_mes,
        "cuentas_por_cobrar": cuentas_por_cobrar,
    }
    return render(request, "core/institucion_dashboard.html", context)


@login_required
def sin_institucion(request):
    return render(request, "core/sin_institucion.html")


@login_required
def perfil(request):
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil actualizado correctamente.")
        return redirect("core:perfil")
    asignaciones = request.user.asignaciones_institucion.select_related("institucion").all()
    return render(request, "core/perfil.html", {"form": form, "asignaciones": asignaciones})


@login_required
def mis_instituciones(request):
    asignaciones = request.user.asignaciones_institucion.select_related("institucion").all()
    return render(request, "core/mis_instituciones.html", {"asignaciones": asignaciones})


@login_required
def cambiar_institucion(request, asignacion_id):
    if request.method != "POST" or request.user.is_superuser:
        return redirect("core:mis_instituciones")
    asignacion = get_object_or_404(request.user.asignaciones_institucion, pk=asignacion_id, activo=True, institucion__activa=True)
    request.session["asignacion_institucion_id"] = asignacion.pk
    from auditoria.services import registrar_evento
    registrar_evento(request, "CAMBIAR_INSTITUCION", asignacion)
    messages.success(request, f"Ahora estás trabajando en {asignacion.institucion.nombre}.")
    return redirect("core:institucion_dashboard")


@superusuario_required
def auditoria(request):
    eventos = EventoAuditoria.objects.select_related("usuario", "institucion")
    if request.GET.get("q"):
        q = request.GET["q"]
        eventos = eventos.filter(Q(usuario__username__icontains=q) | Q(accion__icontains=q) | Q(modelo__icontains=q))
    if request.GET.get("institucion"):
        eventos = eventos.filter(institucion_id=request.GET["institucion"])
    if request.GET.get("accion"):
        eventos = eventos.filter(accion=request.GET["accion"])
    if request.GET.get("fecha"):
        eventos = eventos.filter(fecha__date=request.GET["fecha"])
    return render(request, "core/auditoria.html", {"eventos": eventos[:100], "instituciones": Institucion.objects.all()})


@superusuario_required
def auditoria_detalle(request, pk):
    evento = get_object_or_404(EventoAuditoria.objects.select_related("usuario", "institucion"), pk=pk)
    return render(request, "core/auditoria_detalle.html", {"evento": evento})


@superusuario_required
def usuarios_globales(request):
    usuarios = Usuario.objects.prefetch_related("asignaciones_institucion__institucion")
    q = request.GET.get("q", "").strip()
    if q:
        usuarios = usuarios.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    if request.GET.get("institucion"):
        usuarios = usuarios.filter(asignaciones_institucion__institucion_id=request.GET["institucion"])
    if request.GET.get("rol"):
        usuarios = usuarios.filter(asignaciones_institucion__rol=request.GET["rol"])
    if request.GET.get("estado") in {"activo", "inactivo"}:
        usuarios = usuarios.filter(activo=request.GET["estado"] == "activo")
    from instituciones.models import UsuarioInstitucion
    return render(request, "core/usuarios_globales.html", {"usuarios": usuarios.distinct(), "instituciones": Institucion.objects.all(), "roles": UsuarioInstitucion.Rol.choices, "q": q})


@superusuario_required
def usuario_global_detalle(request, pk):
    usuario = get_object_or_404(Usuario.objects.prefetch_related("asignaciones_institucion__institucion"), pk=pk)
    return render(request, "core/usuario_global_detalle.html", {"usuario_detalle": usuario})


@superusuario_required
def sistema(request):
    return render(request, "core/sistema.html")


@login_required
def cambiar_password(request):
    form = AulaProPasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        update_session_auth_hash(request, usuario)
        from auditoria.services import registrar_evento
        registrar_evento(request, "CAMBIAR_PASSWORD", usuario)
        messages.success(request, "Contraseña actualizada correctamente.")
        return redirect("core:perfil")
    return render(request, "core/cambiar_password.html", {"form": form})


@login_required
def modulo(request, modulo):
    permitidos = {"academico", "alumnos", "docentes", "asistencia", "calificaciones", "tareas", "finanzas", "reportes", "comunicacion"}
    if modulo not in permitidos:
        from django.http import Http404
        raise Http404
    if request.user.is_superuser and modulo != "reportes":
        return redirect("core:global_dashboard")
    if not request.user.is_superuser and not request.institucion:
        return redirect("core:sin_institucion")
    return render(request, "core/modulo.html", {"modulo": modulo})


def error_403(request, exception=None):
    return render(request, "errors/error.html", {"codigo": "403", "titulo": "No tienes permiso para acceder.", "icono": "shield-lock"}, status=403)


def error_404(request, exception=None):
    return render(request, "errors/error.html", {"codigo": "404", "titulo": "No encontramos esta página.", "icono": "compass"}, status=404)


def error_500(request):
    return render(request, "errors/error.html", {"codigo": "500", "titulo": "Ocurrió un problema.", "icono": "tools"}, status=500)
