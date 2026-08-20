from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.services import registrar_evento
from auditoria.models import EventoAuditoria
from core.decorators import (
    administrador_institucion_required,
    institucion_required,
    superusuario_required,
)
from cuentas.forms import UsuarioInstitucionCrearForm, UsuarioInstitucionEditarForm
from cuentas.forms import AulaProSetPasswordForm

from .forms import InstitucionCrearForm, InstitucionForm
from .models import Institucion, UsuarioInstitucion


@institucion_required
def configuracion(request):
    institucion = request.institucion
    if request.method == "POST":
        form = InstitucionForm(request.POST, request.FILES, instance=institucion)
        if form.is_valid():
            form.save()
            registrar_evento(request, "ACTUALIZAR", institucion)
            messages.success(request, "La información institucional se actualizó correctamente.")
            return redirect("instituciones:configuracion")
    else:
        form = InstitucionForm(instance=institucion)
    return render(request, "instituciones/configuracion.html", {"form": form})


@superusuario_required
def lista(request):
    instituciones = Institucion.objects.annotate(total_usuarios=Count("asignaciones_usuario"))
    q = request.GET.get("q", "")
    if q:
        instituciones = instituciones.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))
    return render(request, "instituciones/lista.html", {"instituciones": instituciones, "q": q, "total": Institucion.objects.count(), "activas": Institucion.objects.filter(activa=True).count(), "inactivas": Institucion.objects.filter(activa=False).count()})


@superusuario_required
def crear(request):
    form = InstitucionCrearForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        institucion = form.save()
        evento = registrar_evento(request, "CREAR", institucion)
        evento.institucion = institucion
        evento.save(update_fields=("institucion",))
        messages.success(request, "Institución creada correctamente.")
        return redirect("instituciones:detalle", uuid=institucion.uuid)
    return render(request, "instituciones/formulario.html", {"form": form})


@superusuario_required
def detalle(request, uuid):
    institucion = get_object_or_404(Institucion.objects.annotate(total_usuarios=Count("asignaciones_usuario")), uuid=uuid)
    eventos = EventoAuditoria.objects.filter(institucion=institucion).select_related("usuario")[:10]
    asignaciones = institucion.asignaciones_usuario.select_related("usuario")
    return render(request, "instituciones/detalle.html", {"institucion": institucion, "eventos": eventos, "asignaciones": asignaciones})


@superusuario_required
def editar(request, uuid):
    institucion = get_object_or_404(Institucion, uuid=uuid)
    form = InstitucionCrearForm(request.POST or None, request.FILES or None, instance=institucion)
    if request.method == "POST" and form.is_valid():
        form.save()
        evento = registrar_evento(request, "ACTUALIZAR", institucion)
        evento.institucion = institucion
        evento.save(update_fields=("institucion",))
        messages.success(request, "Institución actualizada correctamente.")
        return redirect("instituciones:detalle", uuid=uuid)
    return render(request, "instituciones/formulario.html", {"form": form, "institucion": institucion})


@superusuario_required
def cambiar_estado(request, uuid):
    if request.method != "POST":
        return redirect("instituciones:detalle", uuid=uuid)
    institucion = get_object_or_404(Institucion, uuid=uuid)
    institucion.activa = not institucion.activa
    institucion.save(update_fields=("activa",))
    evento = registrar_evento(request, "ACTIVAR" if institucion.activa else "DESACTIVAR", institucion)
    evento.institucion = institucion
    evento.save(update_fields=("institucion",))
    messages.success(request, f"Institución {'activada' if institucion.activa else 'desactivada'} correctamente.")
    return redirect("instituciones:detalle", uuid=uuid)


@administrador_institucion_required
def usuarios(request):
    asignaciones = UsuarioInstitucion.objects.filter(institucion=request.institucion).select_related("usuario")
    q = request.GET.get("q", "")
    if q:
        asignaciones = asignaciones.filter(Q(usuario__username__icontains=q) | Q(usuario__first_name__icontains=q) | Q(usuario__last_name__icontains=q) | Q(usuario__email__icontains=q))
    if request.GET.get("rol"):
        asignaciones = asignaciones.filter(rol=request.GET["rol"])
    if request.GET.get("estado") in {"activo", "inactivo"}:
        asignaciones = asignaciones.filter(activo=request.GET["estado"] == "activo")
    return render(request, "instituciones/usuarios/lista.html", {"asignaciones": asignaciones, "roles": UsuarioInstitucion.Rol.choices, "q": q})


@administrador_institucion_required
@transaction.atomic
def usuario_crear(request):
    form = UsuarioInstitucionCrearForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        asignacion = UsuarioInstitucion.objects.create(usuario=usuario, institucion=request.institucion, rol=form.cleaned_data["rol"])
        registrar_evento(request, "CREAR", asignacion)
        messages.success(request, "Usuario creado correctamente.")
        return redirect("instituciones:usuario_detalle", pk=asignacion.pk)
    return render(request, "instituciones/usuarios/formulario.html", {"form": form, "titulo": "Nuevo usuario"})


def _asignacion(request, pk):
    return get_object_or_404(UsuarioInstitucion.objects.select_related("usuario", "institucion"), pk=pk, institucion=request.institucion)


@administrador_institucion_required
def usuario_detalle(request, pk):
    return render(request, "instituciones/usuarios/detalle.html", {"asignacion": _asignacion(request, pk)})


@administrador_institucion_required
@transaction.atomic
def usuario_editar(request, pk):
    asignacion = _asignacion(request, pk)
    form = UsuarioInstitucionEditarForm(request.POST or None, instance=asignacion.usuario, asignacion=asignacion)
    if request.method == "POST" and form.is_valid():
        form.save()
        asignacion.rol = form.cleaned_data["rol"]
        asignacion.activo = form.cleaned_data["activo"]
        asignacion.save(update_fields=("rol", "activo"))
        registrar_evento(request, "ACTUALIZAR", asignacion)
        messages.success(request, "Usuario actualizado correctamente.")
        return redirect("instituciones:usuario_detalle", pk=asignacion.pk)
    return render(request, "instituciones/usuarios/formulario.html", {"form": form, "titulo": "Editar usuario", "asignacion": asignacion})


@administrador_institucion_required
def usuario_estado(request, pk):
    asignacion = _asignacion(request, pk)
    if request.method == "POST":
        asignacion.activo = not asignacion.activo
        asignacion.save(update_fields=("activo",))
        registrar_evento(request, "ACTIVAR" if asignacion.activo else "DESACTIVAR", asignacion)
        messages.success(request, f"Usuario {'activado' if asignacion.activo else 'desactivado'} correctamente.")
    return redirect("instituciones:usuario_detalle", pk=pk)


@administrador_institucion_required
@transaction.atomic
def usuario_password(request, pk):
    asignacion = _asignacion(request, pk)
    form = AulaProSetPasswordForm(asignacion.usuario, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        registrar_evento(request, "RESTABLECER_PASSWORD", asignacion)
        messages.success(request, "Contraseña restablecida correctamente.")
        return redirect("instituciones:usuario_detalle", pk=pk)
    return render(request, "instituciones/usuarios/password.html", {"form": form, "asignacion": asignacion})
