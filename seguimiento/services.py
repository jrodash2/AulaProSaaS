from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone
from alumnos.models import AlumnoEncargado
from docentes.models import AsignacionDocente,Docente
from comunicaciones.models import Notificacion
from .models import RegistroSeguimiento
ADMIN={"PROPIETARIO","DIRECTOR","ADMINISTRADOR","SECRETARIA"}
def rol(request):return request.asignacion_institucion.rol
def registros_visibles_para_usuario(request):
 q=RegistroSeguimiento.objects.filter(institucion=request.institucion).select_related("alumno","inscripcion__grado","inscripcion__seccion","categoria","docente")
 r=rol(request)
 if r in {"PROPIETARIO","DIRECTOR","ADMINISTRADOR"}:return q
 if r=="SECRETARIA":return q.exclude(confidencialidad="INTERNO")
 if r=="DOCENTE":
  d=Docente.objects.filter(institucion=request.institucion,usuario=request.user).first()
  return q.filter(confidencialidad__in=("DOCENTES","PADRES","PUBLICABLE_PORTAL"),inscripcion__seccion__asignaciones_docentes__docente=d,inscripcion__seccion__asignaciones_docentes__activa=True).distinct()
 return q.none()
def alumnos_registrables(request):
 q=__import__('alumnos.models',fromlist=['Alumno']).Alumno.objects.filter(institucion=request.institucion)
 if rol(request)=="DOCENTE":q=q.filter(inscripciones__seccion__asignaciones_docentes__docente__usuario=request.user,inscripciones__seccion__asignaciones_docentes__activa=True).distinct()
 return q if rol(request) in ADMIN|{"DOCENTE"} else q.none()
def puede_editar_registro(request,registro):
 if registro.institucion_id!=request.institucion.id:return False
 if rol(request) in {"PROPIETARIO","DIRECTOR","ADMINISTRADOR"}:return True
 if rol(request)=="SECRETARIA":return registro.confidencialidad!="INTERNO"
 return rol(request)=="DOCENTE" and registros_visibles_para_usuario(request).filter(pk=registro.pk,registrado_por=request.user).exists()
def cerrar_registro(request,registro,conclusion):
 if not puede_editar_registro(request,registro):raise PermissionDenied
 registro.estado="CERRADO";registro.conclusion=conclusion;registro.cerrado_por=request.user;registro.fecha_cierre=timezone.now();registro.save();return registro
def notificar_encargados(request,registro):
 if not puede_editar_registro(request,registro) or registro.confidencialidad not in ("PADRES","PUBLICABLE_PORTAL"):raise PermissionDenied
 usuarios=AlumnoEncargado.objects.filter(alumno=registro.alumno,activo=True,encargado__usuario__isnull=False).values_list("encargado__usuario",flat=True)
 for uid in usuarios:Notificacion.objects.get_or_create(institucion=request.institucion,usuario_id=uid,tipo_origen="SEGUIMIENTO",origen_id=str(registro.pk),defaults={"titulo":registro.titulo,"mensaje":"Hay una actualización de seguimiento disponible en el portal.","url_destino":f"/seguimiento/portal/alumnos/{registro.alumno_id}/"})
