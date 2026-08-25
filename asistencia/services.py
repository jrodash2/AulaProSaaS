from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from alumnos.models import Inscripcion
from auditoria.services import registrar_evento
from docentes.models import AsignacionDocente, AsignacionGuia, Docente
from .models import RegistroAsistencia, SesionAsistencia

ROLES_GESTION = {"PROPIETARIO", "DIRECTOR", "ADMINISTRADOR"}
ROLES_LECTURA = ROLES_GESTION | {"SECRETARIA", "DOCENTE"}

def rol(request): return request.asignacion_institucion.rol

def docente_usuario(request):
    return Docente.objects.filter(institucion=request.institucion, usuario=request.user, estado=Docente.Estado.ACTIVO).first()

def puede_crear(request, *, tipo, seccion, curso=None):
    r = rol(request)
    if r in ROLES_GESTION or (r == "SECRETARIA" and tipo == SesionAsistencia.Tipo.GENERAL): return True
    if r != "DOCENTE": return False
    docente = docente_usuario(request)
    if not docente: return False
    if tipo == SesionAsistencia.Tipo.GENERAL:
        return AsignacionGuia.objects.filter(institucion=request.institucion, docente=docente, seccion=seccion, ciclo=seccion.ciclo, activa=True).exists()
    return AsignacionDocente.objects.filter(institucion=request.institucion, docente=docente, seccion=seccion, curso=curso, ciclo=seccion.ciclo, activa=True).exists()

def sesiones_permitidas(request):
    qs = SesionAsistencia.objects.filter(institucion=request.institucion)
    if rol(request) != "DOCENTE": return qs
    docente = docente_usuario(request)
    if not docente: return qs.none()
    clases = AsignacionDocente.objects.filter(institucion=request.institucion, docente=docente, activa=True).values("seccion_id", "curso_id")
    guias = AsignacionGuia.objects.filter(institucion=request.institucion, docente=docente, activa=True).values_list("seccion_id", flat=True)
    filtro = Q(tipo="GENERAL", seccion_id__in=guias)
    for clase in clases: filtro |= Q(tipo="CURSO", seccion_id=clase["seccion_id"], curso_id=clase["curso_id"])
    return qs.filter(filtro)

def puede_editar_sesion(request, sesion):
    r = rol(request)
    if r in ROLES_GESTION: return True
    if r == "SECRETARIA": return sesion.tipo == SesionAsistencia.Tipo.GENERAL
    if r != "DOCENTE": return False
    docente = docente_usuario(request)
    if not docente: return False
    if sesion.tipo == SesionAsistencia.Tipo.GENERAL:
        return AsignacionGuia.objects.filter(institucion=request.institucion, docente=docente, ciclo=sesion.ciclo, seccion=sesion.seccion, activa=True).exists()
    return AsignacionDocente.objects.filter(institucion=request.institucion, docente=docente, ciclo=sesion.ciclo, seccion=sesion.seccion, curso=sesion.curso, activa=True).exists()

@transaction.atomic
def crear_sesion(*, request, ciclo, oferta, grado, seccion, tipo, fecha, curso=None):
    if fecha > timezone.localdate(): raise ValidationError("No se permite crear asistencia en fechas futuras.")
    if not puede_crear(request, tipo=tipo, seccion=seccion, curso=curso): raise PermissionDenied
    lookup = dict(institucion=request.institucion, fecha=fecha, seccion=seccion, tipo=tipo)
    if tipo == SesionAsistencia.Tipo.CURSO: lookup["curso"] = curso
    existente = SesionAsistencia.objects.exclude(estado=SesionAsistencia.Estado.ANULADA).filter(**lookup).first()
    if existente: return existente, False
    inscripciones = list(Inscripcion.objects.select_related("alumno").filter(institucion=request.institucion, ciclo=ciclo, oferta_academica=oferta, grado=grado, seccion=seccion, estado=Inscripcion.Estado.ACTIVA))
    if not inscripciones: raise ValidationError("No hay estudiantes inscritos en esta sección.")
    docente = docente_usuario(request) if rol(request) == "DOCENTE" else None
    asignacion = None
    if tipo == SesionAsistencia.Tipo.CURSO and docente:
        asignacion = AsignacionDocente.objects.get(institucion=request.institucion, docente=docente, ciclo=ciclo, seccion=seccion, curso=curso, activa=True)
    sesion = SesionAsistencia.objects.create(institucion=request.institucion, ciclo=ciclo, fecha=fecha, tipo=tipo, oferta_academica=oferta, grado=grado, seccion=seccion, curso=curso, asignacion_docente=asignacion, docente=docente, creada_por=request.user)
    RegistroAsistencia.objects.bulk_create([RegistroAsistencia(institucion=request.institucion, sesion=sesion, alumno=i.alumno, inscripcion=i, registrado_por=request.user) for i in inscripciones])
    registrar_evento(request, "CREAR_SESION_ASISTENCIA", sesion)
    return sesion, True

@transaction.atomic
def guardar_registros(sesion, estados, usuario, request=None):
    if sesion.estado not in {SesionAsistencia.Estado.ABIERTA, SesionAsistencia.Estado.BORRADOR}: raise ValidationError("La sesión cerrada o anulada no puede modificarse.")
    validos = set(RegistroAsistencia.Estado.values)
    registros = list(sesion.registros.select_for_update())
    for registro in registros:
        estado = estados.get(str(registro.pk))
        if estado in validos:
            registro.estado, registro.registrado_por = estado, usuario
            registro.save(update_fields=("estado", "registrado_por", "fecha_actualizacion"))
    if request: registrar_evento(request, "MODIFICAR_ASISTENCIA", sesion)

@transaction.atomic
def cerrar_sesion(sesion, usuario, request=None):
    original = sesion
    sesion = SesionAsistencia.objects.select_for_update().get(pk=sesion.pk)
    pendientes = sesion.registros.filter(estado=RegistroAsistencia.Estado.SIN_MARCAR).count()
    if pendientes: raise ValidationError(f"{pendientes} estudiantes pendientes por registrar.")
    if sesion.estado != SesionAsistencia.Estado.ABIERTA: raise ValidationError("Solo una sesión abierta puede cerrarse.")
    sesion.estado, sesion.cerrada_por, sesion.fecha_cierre = SesionAsistencia.Estado.CERRADA, usuario, timezone.now()
    sesion.save(update_fields=("estado", "cerrada_por", "fecha_cierre", "fecha_actualizacion"))
    original.estado, original.cerrada_por, original.fecha_cierre = sesion.estado, sesion.cerrada_por, sesion.fecha_cierre
    if request: registrar_evento(request, "CERRAR_ASISTENCIA", sesion)
    return sesion

@transaction.atomic
def reabrir_sesion(sesion, usuario, motivo, request=None):
    if not motivo.strip(): raise ValidationError("El motivo de reapertura es obligatorio.")
    if sesion.estado != SesionAsistencia.Estado.CERRADA: raise ValidationError("Solo una sesión cerrada puede reabrirse.")
    sesion.estado, sesion.reabierta_por, sesion.fecha_reapertura, sesion.motivo_reapertura = SesionAsistencia.Estado.ABIERTA, usuario, timezone.now(), motivo.strip()
    sesion.save(update_fields=("estado", "reabierta_por", "fecha_reapertura", "motivo_reapertura", "fecha_actualizacion"))
    if request: registrar_evento(request, "REABRIR_ASISTENCIA", sesion)
    return sesion

@transaction.atomic
def anular_sesion(sesion, usuario, motivo, request=None):
    if not motivo.strip(): raise ValidationError("El motivo de anulación es obligatorio.")
    sesion.estado, sesion.anulada_por, sesion.fecha_anulacion, sesion.motivo_anulacion = SesionAsistencia.Estado.ANULADA, usuario, timezone.now(), motivo.strip()
    sesion.save(update_fields=("estado", "anulada_por", "fecha_anulacion", "motivo_anulacion", "fecha_actualizacion"))
    if request: registrar_evento(request, "ANULAR_ASISTENCIA", sesion)
    return sesion

@transaction.atomic
def justificar(registro, usuario, motivo, request=None):
    if registro.estado != RegistroAsistencia.Estado.AUSENTE: raise ValidationError("Solo se justifican ausencias.")
    if not motivo.strip(): raise ValidationError("El motivo es obligatorio.")
    registro.justificada, registro.motivo_justificacion, registro.justificada_por, registro.fecha_justificacion = True, motivo.strip(), usuario, timezone.now()
    registro.save(update_fields=("justificada", "motivo_justificacion", "justificada_por", "fecha_justificacion", "fecha_actualizacion"))
    if request: registrar_evento(request, "JUSTIFICAR_AUSENCIA", registro)
    return registro

def resumen_alumno(alumno, ciclo=None):
    qs = RegistroAsistencia.objects.filter(alumno=alumno, sesion__tipo=SesionAsistencia.Tipo.GENERAL, sesion__estado=SesionAsistencia.Estado.CERRADA)
    if ciclo: qs = qs.filter(sesion__ciclo=ciclo)
    datos = qs.aggregate(total=Count("id"), presentes=Count("id", filter=Q(estado="PRESENTE")), tardanzas=Count("id", filter=Q(estado="TARDE")), ausencias=Count("id", filter=Q(estado="AUSENTE")), justificadas=Count("id", filter=Q(estado="AUSENTE", justificada=True)))
    datos["porcentaje"] = round((datos["presentes"] + datos["tardanzas"]) * 100 / datos["total"], 1) if datos["total"] else None
    return datos
