from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from auditoria.models import EventoAuditoria
from cuentas.forms import PerfilForm

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
    return render(request, "core/institucion_dashboard.html")


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
    return redirect("core:institucion_dashboard")


@superusuario_required
def auditoria(request):
    eventos = EventoAuditoria.objects.select_related("usuario", "institucion")
    if request.GET.get("q"):
        q = request.GET["q"]
        eventos = eventos.filter(Q(usuario__username__icontains=q) | Q(accion__icontains=q) | Q(modelo__icontains=q))
    if request.GET.get("institucion"):
        eventos = eventos.filter(institucion_id=request.GET["institucion"])
    return render(request, "core/auditoria.html", {"eventos": eventos[:100], "instituciones": Institucion.objects.all()})


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
