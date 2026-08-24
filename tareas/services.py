from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.utils import timezone
from alumnos.models import Inscripcion
from auditoria.services import registrar_evento
from docentes.models import AsignacionDocente,Docente
from .models import AdjuntoTarea,EntregaTarea,Tarea
GESTION={"PROPIETARIO","DIRECTOR","ADMINISTRADOR"}
def rol(r):return r.asignacion_institucion.rol
def docente(r):return Docente.objects.filter(institucion=r.institucion,usuario=r.user,estado="ACTIVO").first()
def asignaciones_usuario(r):
 q=AsignacionDocente.objects.filter(institucion=r.institucion,activa=True)
 return q.filter(docente=docente(r)) if rol(r)=="DOCENTE" else q
def tareas_permitidas(r):
 q=Tarea.objects.filter(institucion=r.institucion)
 if rol(r)=="DOCENTE":q=q.filter(asignacion_docente__in=asignaciones_usuario(r))
 return q
def puede_editar(r,tarea):return rol(r) in GESTION or (rol(r)=="DOCENTE" and asignaciones_usuario(r).filter(pk=tarea.asignacion_docente_id).exists())
def tarea_publicada(tarea):return None
@transaction.atomic
def crear_tarea(request,asignacion,**datos):
 if not (rol(request) in GESTION or (rol(request)=="DOCENTE" and asignaciones_usuario(request).filter(pk=asignacion.pk).exists())):raise PermissionDenied
 t=Tarea.objects.create(institucion=request.institucion,ciclo=asignacion.ciclo,asignacion_docente=asignacion,curso=asignacion.curso,grado=asignacion.grado,seccion=asignacion.seccion,creada_por=request.user,**datos);registrar_evento(request,"CREAR_TAREA",t);return t
@transaction.atomic
def sincronizar_entregas_tarea(tarea):
 ins=Inscripcion.objects.filter(institucion=tarea.institucion,ciclo=tarea.ciclo,grado=tarea.grado,seccion=tarea.seccion,estado=Inscripcion.Estado.ACTIVA).select_related("alumno");existentes=set(tarea.entregas.values_list("alumno_id",flat=True));EntregaTarea.objects.bulk_create([EntregaTarea(institucion=tarea.institucion,tarea=tarea,alumno=i.alumno,inscripcion=i) for i in ins if i.alumno_id not in existentes]);return tarea.entregas.count()
@transaction.atomic
def cambiar_estado(request,tarea,estado,motivo=""):
 if not puede_editar(request,tarea):raise PermissionDenied
 acciones={"PUBLICADA":"PUBLICAR_TAREA","CERRADA":"CERRAR_TAREA","ANULADA":"ANULAR_TAREA","BORRADOR":"REABRIR_TAREA"}
 if estado not in acciones:raise ValidationError("Estado inválido.")
 if estado in {"ANULADA","BORRADOR"} and not motivo.strip():raise ValidationError("El motivo es obligatorio.")
 anterior=tarea.estado;tarea.estado=estado
 if estado=="ANULADA":tarea.motivo_anulacion=motivo.strip();tarea.anulada_por=request.user;tarea.fecha_anulacion=timezone.now()
 if estado=="BORRADOR":
  if rol(request) not in GESTION:raise PermissionDenied
  tarea.motivo_reapertura=motivo.strip();tarea.reabierta_por=request.user
 tarea.save()
 if estado=="PUBLICADA":sincronizar_entregas_tarea(tarea);tarea_publicada(tarea)
 registrar_evento(request,acciones[estado],tarea,detalles={"anterior":anterior,"nuevo":estado,"motivo":motivo});return tarea
@transaction.atomic
def editar_tarea(request,tarea,**datos):
 if not puede_editar(request,tarea):raise PermissionDenied
 anterior=str(tarea.fecha_limite)
 if tarea.estado!="BORRADOR":
  for campo in ("asignacion_docente","ciclo","curso","grado","seccion"):
   if campo in datos and getattr(tarea,f"{campo}_id",None)!=getattr(datos[campo],"pk",datos[campo]):raise ValidationError("No puede cambiar la clase después de publicar.")
 for k,v in datos.items():setattr(tarea,k,v)
 tarea.save();registrar_evento(request,"EDITAR_TAREA",tarea,detalles={"fecha_limite_anterior":anterior,"fecha_limite_nueva":str(tarea.fecha_limite)});return tarea
def agregar_adjunto(request,tarea,archivo):
 if not puede_editar(request,tarea):raise PermissionDenied
 x=AdjuntoTarea(institucion=request.institucion,tarea=tarea,archivo=archivo,nombre_original=archivo.name,tipo=getattr(archivo,"content_type","") or "");x.save();registrar_evento(request,"AGREGAR_ADJUNTO_TAREA",x);return x
