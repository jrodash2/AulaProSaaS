from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import HistorialSuscripcion, ModuloSaaS, Plan, PlanModulo, Suscripcion

ROLES_LICENCIADOS = ("PROPIETARIO", "DIRECTOR", "ADMINISTRADOR", "SECRETARIA", "CONTABILIDAD", "DOCENTE")
ESTADOS_VIGENTES = (Suscripcion.Estado.PRUEBA, Suscripcion.Estado.ACTIVA, Suscripcion.Estado.SUSPENDIDA)


def suscripcion_actual(institucion):
    if not institucion:
        return None
    vigente = (
        Suscripcion.objects.filter(institucion=institucion, estado__in=ESTADOS_VIGENTES)
        .select_related("plan")
        .order_by("-fecha_inicio", "-pk")
        .first()
    )
    return vigente or Suscripcion.objects.filter(institucion=institucion).select_related("plan").order_by("-fecha_inicio", "-pk").first()


def estado_suscripcion(institucion, hoy=None):
    suscripcion = suscripcion_actual(institucion)
    if not suscripcion:
        return None
    hoy = hoy or timezone.localdate()
    if suscripcion.estado in (Suscripcion.Estado.SUSPENDIDA, Suscripcion.Estado.CANCELADA):
        return suscripcion.estado
    if hoy < suscripcion.fecha_inicio or suscripcion.fecha_fin < hoy:
        return Suscripcion.Estado.VENCIDA
    if suscripcion.estado == Suscripcion.Estado.PRUEBA:
        if not suscripcion.periodo_prueba_hasta or suscripcion.periodo_prueba_hasta < hoy:
            return Suscripcion.Estado.VENCIDA
        return Suscripcion.Estado.PRUEBA
    return Suscripcion.Estado.ACTIVA


def obtener_uso_plan(institucion):
    from academico.models import CicloEscolar
    from alumnos.models import Inscripcion
    from instituciones.models import UsuarioInstitucion

    suscripcion = suscripcion_actual(institucion)
    ciclo = (
        CicloEscolar.objects.filter(institucion=institucion, es_actual=True).first()
        or CicloEscolar.objects.filter(institucion=institucion, activo=True).order_by("-anio", "-pk").first()
    )
    alumnos = Inscripcion.objects.filter(institucion=institucion, ciclo=ciclo, estado=Inscripcion.Estado.ACTIVA).count() if ciclo else 0
    usuarios = UsuarioInstitucion.objects.filter(institucion=institucion, activo=True, rol__in=ROLES_LICENCIADOS).count()
    return {
        "alumnos": {"usados": alumnos, "limite": suscripcion.limite_alumnos if suscripcion else None},
        "usuarios": {"usados": usuarios, "limite": suscripcion.limite_usuarios if suscripcion else None},
    }


def validar_cupo_alumnos(institucion, cantidad=1):
    uso = obtener_uso_plan(institucion)["alumnos"]
    if uso["limite"] is not None and uso["usados"] + cantidad > uso["limite"]:
        suscripcion = suscripcion_actual(institucion)
        raise ValidationError(
            f"Has alcanzado el límite de {uso['limite']} estudiantes de tu plan {suscripcion.plan.nombre}. "
            f"Disponibles: {max(uso['limite'] - uso['usados'], 0)}; solicitados: {cantidad}."
        )
    return uso


def validar_cupo_usuarios(institucion, cantidad=1):
    uso = obtener_uso_plan(institucion)["usuarios"]
    if uso["limite"] is not None and uso["usados"] + cantidad > uso["limite"]:
        suscripcion = suscripcion_actual(institucion)
        raise ValidationError(f"Has alcanzado el límite de {uso['limite']} usuarios de tu plan {suscripcion.plan.nombre}.")
    return uso


def modulo_habilitado(institucion, codigo):
    suscripcion = suscripcion_actual(institucion)
    if not suscripcion:
        return True  # compatibilidad para tenants existentes hasta ejecutar asignar_plan_inicial
    return PlanModulo.objects.filter(plan=suscripcion.plan, modulo__codigo=codigo, modulo__activo=True, habilitado=True).exists()


def modo_solo_lectura_suscripcion(institucion):
    return estado_suscripcion(institucion) == Suscripcion.Estado.VENCIDA


def _registrar(suscripcion, accion, usuario, **detalles):
    historial = HistorialSuscripcion.objects.create(
        suscripcion=suscripcion,
        accion=accion,
        estado_anterior=detalles.pop("estado_anterior", ""),
        estado_nuevo=suscripcion.estado,
        plan_anterior=detalles.pop("plan_anterior", None),
        plan_nuevo=suscripcion.plan,
        detalles=detalles,
        realizada_por=usuario,
    )
    from auditoria.models import EventoAuditoria
    EventoAuditoria.objects.create(
        usuario=usuario, institucion=suscripcion.institucion, accion=accion,
        modelo="suscripciones.Suscripcion", objeto_id=str(suscripcion.pk), detalles=detalles,
    )
    return historial


@transaction.atomic
def cambiar_plan(suscripcion, nuevo_plan, usuario):
    suscripcion = Suscripcion.objects.select_for_update().select_related("institucion", "plan").get(pk=suscripcion.pk)
    uso = obtener_uso_plan(suscripcion.institucion)
    limite = suscripcion.max_alumnos_override if suscripcion.max_alumnos_override is not None else nuevo_plan.max_alumnos
    if limite is not None and uso["alumnos"]["usados"] > limite:
        raise ValidationError(f"La institución utiliza {uso['alumnos']['usados']} alumnos y el plan permite {limite}.")
    anterior = suscripcion.plan
    suscripcion.plan = nuevo_plan
    suscripcion.save(update_fields=("plan", "fecha_actualizacion"))
    _registrar(suscripcion, "CAMBIAR_PLAN", usuario, plan_anterior=anterior)
    return suscripcion


def _sumar_meses(fecha, meses):
    mes = fecha.month - 1 + meses
    anio = fecha.year + mes // 12
    mes = mes % 12 + 1
    return date(anio, mes, min(fecha.day, monthrange(anio, mes)[1]))


@transaction.atomic
def renovar_suscripcion(suscripcion, usuario, meses=None, fecha_fin=None):
    suscripcion = Suscripcion.objects.select_for_update().get(pk=suscripcion.pk)
    if not fecha_fin:
        if meses not in (1, 12):
            raise ValidationError("Seleccione 1 mes, 12 meses o una fecha personalizada.")
        base = max(suscripcion.fecha_fin, timezone.localdate())
        fecha_fin = _sumar_meses(base, meses)
    if fecha_fin <= timezone.localdate():
        raise ValidationError("La renovación debe finalizar en una fecha futura.")
    anterior = suscripcion.estado
    suscripcion.fecha_fin = fecha_fin
    suscripcion.estado = Suscripcion.Estado.ACTIVA
    suscripcion.periodo_prueba_hasta = None
    suscripcion.save(update_fields=("fecha_fin", "estado", "periodo_prueba_hasta", "fecha_actualizacion"))
    _registrar(suscripcion, "RENOVAR_SUSCRIPCION", usuario, estado_anterior=anterior, fecha_fin=str(fecha_fin))
    return suscripcion


@transaction.atomic
def cambiar_estado(suscripcion, estado, usuario):
    permitidos = {Suscripcion.Estado.SUSPENDIDA, Suscripcion.Estado.ACTIVA, Suscripcion.Estado.CANCELADA}
    if estado not in permitidos:
        raise ValidationError("Estado no permitido para esta acción.")
    suscripcion = Suscripcion.objects.select_for_update().get(pk=suscripcion.pk)
    anterior = suscripcion.estado
    suscripcion.estado = estado
    suscripcion.save(update_fields=("estado", "fecha_actualizacion"))
    acciones = {
        Suscripcion.Estado.SUSPENDIDA: "SUSPENDER_SUSCRIPCION",
        Suscripcion.Estado.ACTIVA: "REACTIVAR_SUSCRIPCION",
        Suscripcion.Estado.CANCELADA: "CANCELAR_SUSCRIPCION",
    }
    _registrar(suscripcion, acciones[estado], usuario, estado_anterior=anterior)
    return suscripcion


def metricas_saas():
    vigentes = Suscripcion.objects.filter(estado=Suscripcion.Estado.ACTIVA, fecha_inicio__lte=timezone.localdate(), fecha_fin__gte=timezone.localdate()).select_related("plan")
    mrr = sum((s.precio_mensual_equivalente for s in vigentes), Decimal("0"))
    return {"mrr": mrr, "arr": mrr * Decimal("12"), "activas": vigentes.count()}


def crear_catalogo_inicial():
    from .catalogo import MODULOS_OFICIALES, MODULOS_POR_PLAN
    modulos = {}
    for codigo, nombre, orden, descripcion, icono in MODULOS_OFICIALES:
        modulos[codigo], _ = ModuloSaaS.objects.update_or_create(codigo=codigo, defaults={"nombre": nombre, "orden": orden, "descripcion": descripcion, "icono": icono, "activo": True})
    datos = (
        ("INICIO", "Inicio", Decimal("199"), Decimal("1990"), 100, 10),
        ("CRECE", "Crece", Decimal("299"), Decimal("2990"), 250, 20),
        ("PRO", "Pro", Decimal("449"), Decimal("4490"), 500, 40),
        ("EMPRESA", "Empresa", Decimal("599"), Decimal("5990"), None, None),
    )
    planes = {}
    for orden, (codigo, nombre, mensual, anual, alumnos, usuarios) in enumerate(datos, 1):
        plan, _ = Plan.objects.update_or_create(codigo=codigo, defaults={"nombre": nombre, "precio_mensual": mensual, "precio_anual": anual, "max_alumnos": alumnos, "max_usuarios": usuarios, "es_personalizado": codigo == "EMPRESA", "orden": orden, "activo": True, "publico": True})
        planes[codigo] = plan
        for modulo in modulos.values():
            PlanModulo.objects.get_or_create(plan=plan, modulo=modulo, defaults={"habilitado": modulo.codigo in MODULOS_POR_PLAN[codigo]})
    return planes
