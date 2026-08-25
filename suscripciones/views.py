from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.decorators import institucion_required, superusuario_required
from .forms import CambioPlanForm, PlanForm, RenovacionForm, SolicitudCambioPlanForm, SuscripcionForm
from .models import HistorialSuscripcion, ModuloSaaS, Plan, SolicitudCambioPlan, Suscripcion
from .services import cambiar_estado, cambiar_plan, estado_suscripcion, metricas_saas, obtener_uso_plan, renovar_suscripcion, suscripcion_actual


@superusuario_required
def dashboard(request):
    from alumnos.models import Inscripcion
    hoy = timezone.localdate()
    metricas = metricas_saas()
    metricas.update({
        "trials": Suscripcion.objects.filter(estado=Suscripcion.Estado.PRUEBA, periodo_prueba_hasta__gte=hoy).count(),
        "vencidas": Suscripcion.objects.filter(estado=Suscripcion.Estado.VENCIDA).count(),
        "suspendidas": Suscripcion.objects.filter(estado=Suscripcion.Estado.SUSPENDIDA).count(),
        "instituciones": Suscripcion.objects.values("institucion_id").distinct().count(),
        "alumnos_gestionados": Inscripcion.objects.filter(estado="ACTIVA", ciclo__es_actual=True).count(),
    })
    proximas = Suscripcion.objects.filter(estado__in=(Suscripcion.Estado.ACTIVA, Suscripcion.Estado.PRUEBA), fecha_fin__range=(hoy, hoy + timedelta(days=30))).select_related("institucion", "plan")[:10]
    return render(request, "suscripciones/dashboard.html", {"metricas": metricas, "proximas": proximas})


@superusuario_required
def planes(request):
    return render(request, "suscripciones/planes.html", {"planes": Plan.objects.annotate(total_instituciones=Count("suscripciones__institucion", distinct=True), total_modulos=Count("configuracion_modulos", filter=Q(configuracion_modulos__habilitado=True), distinct=True)).prefetch_related("modulos")})


@superusuario_required
def plan_detalle(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    modulos = ModuloSaaS.objects.filter(configuracion_planes__plan=plan, configuracion_planes__habilitado=True, activo=True).order_by("orden")
    return render(request, "suscripciones/plan_detalle.html", {"plan": plan, "modulos": modulos})


@superusuario_required
def plan_form(request, pk=None):
    plan = get_object_or_404(Plan, pk=pk) if pk else None
    form = PlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, "Plan guardado correctamente.")
        return redirect("suscripciones:planes")
    return render(request, "suscripciones/plan_formulario.html", {"form": form, "titulo": "Editar plan" if plan else "Nuevo plan"})


@superusuario_required
def lista_suscripciones(request):
    qs = Suscripcion.objects.select_related("institucion", "plan")
    for campo in ("plan", "estado", "modalidad"):
        if request.GET.get(campo): qs = qs.filter(**{campo: request.GET[campo]})
    if request.GET.get("q"): qs = qs.filter(institucion__nombre__icontains=request.GET["q"])
    return render(request, "suscripciones/lista.html", {"suscripciones": qs, "planes": Plan.objects.filter(activo=True), "estados": Suscripcion.Estado.choices, "modalidades": Suscripcion.Modalidad.choices})


@superusuario_required
@transaction.atomic
def suscripcion_form(request, pk=None):
    item = get_object_or_404(Suscripcion, pk=pk) if pk else None
    form = SuscripcionForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        suscripcion = form.save(commit=False); suscripcion.creada_por = suscripcion.creada_por or request.user; suscripcion.save()
        accion = "EDITAR_SUSCRIPCION" if item else "CREAR_SUSCRIPCION"
        HistorialSuscripcion.objects.create(suscripcion=suscripcion, accion=accion, estado_nuevo=suscripcion.estado, plan_nuevo=suscripcion.plan, realizada_por=request.user)
        from auditoria.models import EventoAuditoria
        EventoAuditoria.objects.create(usuario=request.user, institucion=suscripcion.institucion, accion=accion, modelo="suscripciones.Suscripcion", objeto_id=str(suscripcion.pk), detalles={"plan":suscripcion.plan.codigo,"estado":suscripcion.estado})
        messages.success(request, "Suscripción guardada correctamente.")
        return redirect("suscripciones:detalle", pk=suscripcion.pk)
    return render(request, "suscripciones/formulario.html", {"form": form, "titulo": "Editar suscripción" if item else "Nueva suscripción"})


@superusuario_required
def detalle(request, pk):
    item = get_object_or_404(Suscripcion.objects.select_related("institucion", "plan"), pk=pk)
    return render(request, "suscripciones/detalle.html", {"suscripcion": item, "uso": obtener_uso_plan(item.institucion), "estado_efectivo": estado_suscripcion(item.institucion), "historial": item.historial.select_related("realizada_por", "plan_anterior", "plan_nuevo"), "solicitudes": item.institucion.solicitudes_plan.select_related("plan_solicitado")})


@superusuario_required
def renovar(request, pk):
    item = get_object_or_404(Suscripcion, pk=pk); form = RenovacionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            periodo = form.cleaned_data["periodo"]
            renovar_suscripcion(item, request.user, meses=int(periodo) if periodo != "FECHA" else None, fecha_fin=form.cleaned_data.get("fecha_fin"))
        except ValidationError as exc: form.add_error(None, exc)
        else: messages.success(request, "Suscripción renovada."); return redirect("suscripciones:detalle", pk=pk)
    return render(request, "suscripciones/formulario.html", {"form": form, "titulo": "Renovar suscripción"})


@superusuario_required
def cambiar_plan_view(request, pk):
    item = get_object_or_404(Suscripcion, pk=pk); form = CambioPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try: cambiar_plan(item, form.cleaned_data["plan"], request.user)
        except ValidationError as exc: form.add_error("plan", exc)
        else: messages.success(request, "Plan actualizado."); return redirect("suscripciones:detalle", pk=pk)
    return render(request, "suscripciones/formulario.html", {"form": form, "titulo": "Cambiar plan"})


@superusuario_required
@require_POST
def estado_view(request, pk, estado):
    item = get_object_or_404(Suscripcion, pk=pk)
    try: cambiar_estado(item, estado.upper(), request.user)
    except ValidationError as exc: messages.error(request, "; ".join(exc.messages))
    else: messages.success(request, "Estado actualizado.")
    return redirect("suscripciones:detalle", pk=pk)


@superusuario_required
def solicitudes(request):
    return render(request, "suscripciones/solicitudes.html", {"solicitudes": SolicitudCambioPlan.objects.select_related("institucion", "plan_actual", "plan_solicitado", "solicitada_por")})


@superusuario_required
@require_POST
@transaction.atomic
def solicitud_estado(request, pk, estado):
    solicitud = get_object_or_404(SolicitudCambioPlan.objects.select_for_update().select_related("plan_solicitado", "institucion"), pk=pk, estado=SolicitudCambioPlan.Estado.PENDIENTE)
    nuevo_estado = estado.upper()
    if nuevo_estado not in (SolicitudCambioPlan.Estado.APROBADA, SolicitudCambioPlan.Estado.RECHAZADA):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    if nuevo_estado == SolicitudCambioPlan.Estado.APROBADA:
        try: cambiar_plan(suscripcion_actual(solicitud.institucion), solicitud.plan_solicitado, request.user)
        except ValidationError as exc: messages.error(request, "; ".join(exc.messages)); return redirect("suscripciones:solicitudes")
    solicitud.estado=nuevo_estado;solicitud.atendida_por=request.user;solicitud.fecha_atencion=timezone.now();solicitud.save(update_fields=("estado","atendida_por","fecha_atencion"))
    messages.success(request, "Solicitud atendida.")
    return redirect("suscripciones:solicitudes")


@superusuario_required
def uso(request):
    from django.db.models import Count
    from alumnos.models import Inscripcion
    from instituciones.models import UsuarioInstitucion
    from .services import ROLES_LICENCIADOS
    suscripciones = list(Suscripcion.objects.filter(estado__in=(Suscripcion.Estado.ACTIVA, Suscripcion.Estado.PRUEBA, Suscripcion.Estado.SUSPENDIDA)).select_related("institucion", "plan"))
    ids = [s.institucion_id for s in suscripciones]
    alumnos = dict(Inscripcion.objects.filter(institucion_id__in=ids, ciclo__es_actual=True, estado="ACTIVA").values_list("institucion_id").annotate(total=Count("id")))
    usuarios = dict(UsuarioInstitucion.objects.filter(institucion_id__in=ids, activo=True, rol__in=ROLES_LICENCIADOS).values_list("institucion_id").annotate(total=Count("id")))
    filas = [(s, {"alumnos":{"usados":alumnos.get(s.institucion_id,0),"limite":s.limite_alumnos},"usuarios":{"usados":usuarios.get(s.institucion_id,0),"limite":s.limite_usuarios}}) for s in suscripciones]
    return render(request, "suscripciones/uso.html", {"filas": filas})


@institucion_required
def mi_plan(request):
    if request.asignacion_institucion.rol not in ("PROPIETARIO", "DIRECTOR"):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    item = suscripcion_actual(request.institucion)
    return render(request, "suscripciones/mi_plan.html", {"suscripcion": item, "estado_efectivo": estado_suscripcion(request.institucion), "uso": obtener_uso_plan(request.institucion)})


@institucion_required
def solicitar_cambio(request):
    if request.asignacion_institucion.rol != "PROPIETARIO":
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    item = suscripcion_actual(request.institucion)
    if not item: return redirect("mi_suscripcion:mi_plan")
    form = SolicitudCambioPlanForm(request.POST or None, plan_actual=item.plan)
    if request.method == "POST" and form.is_valid():
        solicitud = form.save(commit=False); solicitud.institucion=request.institucion; solicitud.plan_actual=item.plan; solicitud.solicitada_por=request.user; solicitud.save()
        messages.success(request, "Solicitud enviada al equipo de AulaPro.")
        return redirect("mi_suscripcion:mi_plan")
    return render(request, "suscripciones/formulario.html", {"form": form, "titulo": "Solicitar cambio de plan"})
