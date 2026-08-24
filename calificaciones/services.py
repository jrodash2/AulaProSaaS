from collections import defaultdict
from decimal import Decimal
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from alumnos.models import Inscripcion
from auditoria.services import registrar_evento
from docentes.models import AsignacionDocente,Docente
from .models import ActividadEvaluacion,Calificacion,ConfiguracionCalificaciones
GESTION={"PROPIETARIO","DIRECTOR","ADMINISTRADOR"}
def rol(r):return r.asignacion_institucion.rol
def docente(r):return Docente.objects.filter(institucion=r.institucion,usuario=r.user,estado="ACTIVO").first()
def asignaciones_usuario(r):
 q=AsignacionDocente.objects.filter(institucion=r.institucion,activa=True)
 return q.filter(docente=docente(r)) if rol(r)=="DOCENTE" else q
def actividades_permitidas(r):
 q=ActividadEvaluacion.objects.filter(institucion=r.institucion)
 return q.filter(asignacion_docente__in=asignaciones_usuario(r)) if rol(r)=="DOCENTE" else q
def puede_editar(r,asignacion):return rol(r) in GESTION or (rol(r)=="DOCENTE" and asignaciones_usuario(r).filter(pk=asignacion.pk).exists())
@transaction.atomic
def crear_actividad(request,**datos):
 a=datos["asignacion_docente"]
 if not puede_editar(request,a):raise PermissionDenied
 if datos["periodo"].cerrado:raise ValidationError("El período está cerrado.")
 total=ActividadEvaluacion.objects.filter(institucion=request.institucion,periodo=datos["periodo"],curso=datos["curso"],seccion=datos["seccion"],activa=True).aggregate(x=Sum("ponderacion"))["x"] or Decimal("0")
 if total+datos["ponderacion"]>Decimal("100"):raise ValidationError(f"La ponderación excedería 100% (actual: {total}%).")
 actividad=ActividadEvaluacion.objects.create(institucion=request.institucion,creada_por=request.user,**datos);inicializar_calificaciones_actividad(actividad,request.user);registrar_evento(request,"CREAR_ACTIVIDAD",actividad);return actividad
@transaction.atomic
def inicializar_calificaciones_actividad(a,usuario):
 ins=Inscripcion.objects.filter(institucion=a.institucion,ciclo=a.ciclo,grado=a.grado,seccion=a.seccion,estado=Inscripcion.Estado.ACTIVA).select_related("alumno")
 existentes=set(a.calificaciones.values_list("alumno_id",flat=True));Calificacion.objects.bulk_create([Calificacion(institucion=a.institucion,actividad=a,alumno=i.alumno,inscripcion=i,registrado_por=usuario) for i in ins if i.alumno_id not in existentes]);return a.calificaciones.count()
@transaction.atomic
def guardar_calificacion(request,calificacion,estado,punteo=None):
 if not puede_editar(request,calificacion.actividad.asignacion_docente):raise PermissionDenied
 if calificacion.actividad.periodo.cerrado:raise ValidationError("El período está cerrado.")
 anterior={"estado":calificacion.estado,"punteo":str(calificacion.punteo_obtenido) if calificacion.punteo_obtenido is not None else None}
 calificacion.estado=estado;calificacion.punteo_obtenido=Decimal(str(punteo)) if estado=="CALIFICADO" and punteo not in (None,"") else None;calificacion.registrado_por=request.user;calificacion.save()
 registrar_evento(request,"MODIFICAR_CALIFICACION" if anterior["estado"]!="PENDIENTE" else "REGISTRAR_CALIFICACION",calificacion,detalles={"actividad":calificacion.actividad_id,"alumno":calificacion.alumno_id,"anterior":anterior,"nuevo":{"estado":estado,"punteo":str(calificacion.punteo_obtenido) if calificacion.punteo_obtenido is not None else None}});return calificacion
@transaction.atomic
def cerrar_periodo(request,periodo):
 if rol(request) not in GESTION:raise PermissionDenied
 acts=list(periodo.actividades.filter(activa=True).select_related("curso","seccion"))
 if not acts:raise ValidationError("El período no tiene actividades activas.")
 grupos=defaultdict(Decimal)
 for a in acts:grupos[(a.curso_id,a.seccion_id)]+=a.ponderacion
 incompletos=[k for k,v in grupos.items() if v!=Decimal("100")]
 if incompletos:raise ValidationError(f"{len(incompletos)} cursos/secciones no tienen ponderación 100%.")
 pendientes=Calificacion.objects.filter(actividad__in=acts,estado="PENDIENTE").count()
 if pendientes:raise ValidationError(f"Existen {pendientes} calificaciones pendientes.")
 periodo.cerrado=True;periodo.fecha_cierre=timezone.now();periodo.cerrado_por=request.user;periodo.save();registrar_evento(request,"CERRAR_PERIODO",periodo);return periodo
@transaction.atomic
def reabrir_periodo(request,periodo,motivo):
 if rol(request) not in GESTION:raise PermissionDenied
 if not motivo.strip():raise ValidationError("El motivo es obligatorio.")
 periodo.cerrado=False;periodo.fecha_cierre=None;periodo.cerrado_por=None;periodo.motivo_reapertura=motivo.strip();periodo.reabierto_por=request.user;periodo.save();registrar_evento(request,"REABRIR_PERIODO",periodo);return periodo
def promedio_alumno(alumno,periodo,curso):
 qs=Calificacion.objects.filter(alumno=alumno,actividad__periodo=periodo,actividad__curso=curso,actividad__activa=True).select_related("actividad")
 if qs.filter(estado="PENDIENTE").exists() or not qs.exists():return None
 return sum((c.aporte or Decimal("0") for c in qs),Decimal("0"))
def resultado(promedio,config):
 if promedio is None:return "PENDIENTE"
 return "APROBADO" if promedio>=config.nota_minima_aprobacion else "NO APROBADO"
def config(inst):return ConfiguracionCalificaciones.objects.get_or_create(institucion=inst)[0]
