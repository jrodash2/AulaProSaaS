from django.views.decorators.http import require_POST
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

from .forms import InstitucionCrearForm, InstitucionForm, OnboardingFinanzasForm
from .models import Institucion, OnboardingInstitucion, UsuarioInstitucion


@administrador_institucion_required
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
@transaction.atomic
def crear(request):
    form = InstitucionCrearForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        institucion = form.save()
        from datetime import timedelta
        from django.utils import timezone
        from suscripciones.models import Suscripcion
        dias = form.cleaned_data.get("trial_dias") or 0; hoy = timezone.localdate()
        Suscripcion.objects.create(institucion=institucion, plan=form.cleaned_data["plan"], estado="PRUEBA" if dias else "ACTIVA", modalidad="MENSUAL", fecha_inicio=hoy, fecha_fin=hoy + timedelta(days=dias or 30), periodo_prueba_hasta=hoy + timedelta(days=dias) if dias else None, creada_por=request.user)
        from django.contrib.auth import get_user_model
        propietario = get_user_model().objects.create_user(username=form.cleaned_data["propietario_username"], email=form.cleaned_data["propietario_email"], password=form.cleaned_data["propietario_password"])
        UsuarioInstitucion.objects.create(usuario=propietario, institucion=institucion, rol=UsuarioInstitucion.Rol.PROPIETARIO)
        OnboardingInstitucion.objects.create(institucion=institucion, actualizado_por=request.user)
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
    for campo in ("plan", "trial_dias", "propietario_username", "propietario_email", "propietario_password"):
        form.fields.pop(campo, None)
    if request.method == "POST" and form.is_valid():
        form.save()
        evento = registrar_evento(request, "ACTUALIZAR", institucion)
        evento.institucion = institucion
        evento.save(update_fields=("institucion",))
        messages.success(request, "Institución actualizada correctamente.")
        return redirect("instituciones:detalle", uuid=uuid)
    return render(request, "instituciones/formulario.html", {"form": form, "institucion": institucion})


@superusuario_required
@require_POST
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
@require_POST
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


def _puede_onboarding(request, escritura=False):
    roles = {"PROPIETARIO", "ADMINISTRADOR"} if escritura else {"PROPIETARIO", "ADMINISTRADOR", "DIRECTOR"}
    if request.asignacion_institucion.rol not in roles:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied


@institucion_required
@transaction.atomic
def onboarding(request, paso=None):
    from datetime import date
    from django.utils import timezone
    from academico.forms import CicloEscolarForm, JornadaForm
    from academico.models import CicloEscolar, JornadaInstitucion
    from finanzas.models import ConceptoCobro, ConfiguracionFinanciera
    from .onboarding import estado_onboarding, resumen_onboarding

    _puede_onboarding(request, escritura=request.method == "POST")
    estado = estado_onboarding(request.institucion)
    registro = estado["onboarding"]
    paso = paso or registro.paso_actual
    if not 1 <= paso <= OnboardingInstitucion.TOTAL_PASOS:
        return redirect("instituciones:onboarding")
    registro.paso_actual = paso
    form = None
    ciclo = CicloEscolar.objects.filter(institucion=request.institucion, es_actual=True).first() or CicloEscolar.objects.filter(institucion=request.institucion, activo=True).order_by("-anio").first()
    if paso == 1:
        form = InstitucionForm(request.POST or None, request.FILES or None, instance=request.institucion)
    elif paso == 2:
        inicial = {"nombre": f"Ciclo {timezone.localdate().year}", "anio": timezone.localdate().year, "fecha_inicio": date(timezone.localdate().year, 1, 1), "fecha_fin": date(timezone.localdate().year, 11, 30), "es_actual": True}
        form = CicloEscolarForm(request.POST or None, instance=ciclo, initial=inicial if not ciclo else None)
    elif paso == 3:
        form = JornadaForm(request.POST or None, initial={"codigo":"MAT", "nombre":"Matutina", "activa":True})
    elif paso == 9 and estado["paso"]["disponible"]:
        config = ConfiguracionFinanciera.objects.filter(institucion=request.institucion).first()
        initial = {"moneda":getattr(config,"moneda","GTQ"),"simbolo_moneda":getattr(config,"simbolo_moneda","Q"),"dia_vencimiento_mensualidad":getattr(config,"dia_vencimiento_mensualidad",10),"prefijo_recibo":getattr(config,"prefijo_recibo","REC")}
        form = OnboardingFinanzasForm(request.POST or None, initial=initial)

    if request.method == "POST":
        accion = request.POST.get("accion", "siguiente")
        formulario_invalido = accion != "anterior" and form is not None and not form.is_valid()
        if formulario_invalido:
            messages.error(request, "Revisa los campos indicados antes de continuar.")
        elif accion == "anterior":
            registro.paso_actual = max(1, paso - 1)
        elif paso == 1 and form.is_valid():
            form.save(); registro.paso_actual = 2
        elif paso == 2 and form.is_valid():
            item=form.save(commit=False);item.institucion=request.institucion;item.activo=True;item.save();registro.paso_actual=3
        elif paso == 3:
            if accion == "siguiente" and JornadaInstitucion.objects.filter(institucion=request.institucion, activa=True).exists():
                registro.paso_actual=4
            elif form.is_valid():
                item=form.save(commit=False);item.institucion=request.institucion;item.save();registro.paso_actual=4 if accion=="siguiente" else 3
        elif paso == 9 and form and form.is_valid():
            ConfiguracionFinanciera.objects.update_or_create(institucion=request.institucion, defaults={k:form.cleaned_data[k] for k in ("moneda","simbolo_moneda","dia_vencimiento_mensualidad","prefijo_recibo")})
            for marcado,codigo,nombre,tipo,monto,recurrente in (("crear_inscripcion","INS","Inscripción","INSCRIPCION","monto_inscripcion",False),("crear_colegiatura","COL","Colegiatura","MENSUALIDAD","monto_colegiatura",True)):
                if form.cleaned_data[marcado]: ConceptoCobro.objects.update_or_create(institucion=request.institucion,codigo=codigo,defaults={"nombre":nombre,"tipo_general":tipo,"monto_predeterminado":form.cleaned_data[monto] or 0,"recurrente":recurrente,"activo":True})
            registro.paso_actual=10
        elif paso == 11:
            registro.completado=True;registro.omitido=False;registro.fecha_completado=timezone.now();registro.paso_actual=11
        else:
            registro.paso_actual=min(OnboardingInstitucion.TOTAL_PASOS,paso+1)
        if not formulario_invalido:
            registro.actualizado_por=request.user;registro.save()
            messages.success(request,"Progreso de configuración guardado.")
            if registro.completado:return redirect("core:institucion_dashboard")
            return redirect("instituciones:onboarding_paso",paso=registro.paso_actual)

    estado = estado_onboarding(request.institucion)
    acciones={4:("academico:oferta_agregar","Agregar oferta"),5:("academico:grados_secciones","Configurar grados y secciones"),6:("academico:cursos","Revisar cursos"),7:("docentes:crear","Agregar docente"),8:("alumnos:importar","Importar alumnos")}
    return render(request,"instituciones/onboarding.html",{"estado":estado,"paso_numero":paso,"paso":estado["pasos"][paso-1],"form":form,"accion_modulo":acciones.get(paso),"resumen":resumen_onboarding(request.institucion),"ciclo":ciclo})


@institucion_required
@require_POST
def onboarding_omitir(request):
    _puede_onboarding(request, escritura=True)
    if request.asignacion_institucion.rol != "PROPIETARIO":
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    from django.utils import timezone
    registro,_=OnboardingInstitucion.objects.get_or_create(institucion=request.institucion)
    registro.omitido=True;registro.completado=True;registro.fecha_completado=timezone.now();registro.actualizado_por=request.user;registro.save()
    messages.info(request,"Configuración guiada omitida. Puedes usar AulaPro y retomarla desde configuración.")
    return redirect("core:institucion_dashboard")


@superusuario_required
@require_POST
def iniciar_onboarding_global(request, uuid):
    institucion=get_object_or_404(Institucion,uuid=uuid);OnboardingInstitucion.objects.get_or_create(institucion=institucion,defaults={"actualizado_por":request.user})
    messages.success(request,"Onboarding preparado. El propietario puede iniciarlo al ingresar.")
    return redirect("instituciones:detalle",uuid=uuid)
