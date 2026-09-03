from datetime import timedelta
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from comunicaciones.models import Notificacion
from .models import *
ADMIN={"PROPIETARIO","DIRECTOR","ADMINISTRADOR"}
def rol(request):return request.asignacion_institucion.rol
def puede_gestionar(request):return rol(request) in ADMIN
def puede_ver_salario(request):return rol(request)=="PROPIETARIO" or request.user.has_perm("rrhh.ver_datos_salariales")
def empleados_visibles(request):
 q=Empleado.objects.filter(institucion=request.institucion).select_related("puesto","area","usuario","docente")
 return q if rol(request) in ADMIN|{"SECRETARIA","CONTABILIDAD"} else q.filter(usuario=request.user)
def contratos_por_vencer(institucion,dias=30):
 hoy=timezone.localdate();return ContratoLaboral.objects.filter(institucion=institucion,estado="VIGENTE",fecha_fin__range=(hoy,hoy+timedelta(days=dias))).select_related("empleado","puesto")
def resumen_expediente(empleado):
 tipos=TipoDocumentoEmpleado.objects.filter(institucion=empleado.institucion,activo=True,obligatorio=True).filter(Q(puesto__isnull=True)|Q(puesto=empleado.puesto)).filter(Q(area__isnull=True)|Q(area=empleado.area));excluidos=empleado.documentos.filter(tipo_documento__in=tipos,estado="NO_APLICA").values_list("tipo_documento",flat=True);tipos=tipos.exclude(pk__in=excluidos);aprobados=empleado.documentos.filter(tipo_documento__in=tipos,estado="APROBADO").values("tipo_documento").distinct().count();total=tipos.count();return {"aprobados":aprobados,"total":total,"porcentaje":round(aprobados*100/total) if total else 100,"pendientes":max(total-aprobados,0)}
@transaction.atomic
def cambiar_puesto(empleado,puesto,area,fecha,descripcion,usuario):
 empleado=Empleado.objects.select_for_update().get(pk=empleado.pk);anterior_puesto=empleado.puesto;anterior_area=empleado.area
 if puesto.institucion_id!=empleado.institucion_id or area.institucion_id!=empleado.institucion_id or puesto.area_id!=area.pk:raise ValidationError("Destino laboral inválido.")
 empleado.puesto=puesto;empleado.area=area;empleado.save();tipo="CAMBIO_PUESTO" if puesto.pk!=anterior_puesto.pk else "CAMBIO_AREA";return MovimientoLaboral.objects.create(institucion=empleado.institucion,empleado=empleado,fecha=fecha,tipo=tipo,puesto_anterior=anterior_puesto,puesto_nuevo=puesto,area_anterior=anterior_area,area_nueva=area,descripcion=descripcion,registrado_por=usuario)
@transaction.atomic
def registrar_egreso(empleado,fecha,motivo,usuario,desactivar_usuario=True):
 empleado=Empleado.objects.select_for_update().get(pk=empleado.pk);empleado.estado="RETIRADO";empleado.fecha_egreso=fecha;empleado.save();mov=MovimientoLaboral.objects.create(institucion=empleado.institucion,empleado=empleado,fecha=fecha,tipo="EGRESO",puesto_anterior=empleado.puesto,area_anterior=empleado.area,descripcion=motivo,registrado_por=usuario)
 if desactivar_usuario and empleado.usuario_id:
  vinculo=empleado.usuario.asignaciones_institucion.filter(institucion=empleado.institucion).first()
  if vinculo:vinculo.activo=False;vinculo.save()
 return mov
def resolver_permiso(request,permiso,estado):
 if not puede_gestionar(request):raise PermissionDenied
 if estado not in ("APROBADO","RECHAZADO"):raise ValidationError("Resolución inválida.")
 permiso.estado=estado;permiso.autorizado_por=request.user;permiso.fecha_resolucion=timezone.now();permiso.save()
 if permiso.empleado.usuario_id:Notificacion.objects.get_or_create(institucion=permiso.institucion,usuario=permiso.empleado.usuario,tipo_origen="PERMISO_LABORAL",origen_id=str(permiso.pk),defaults={"titulo":f"Permiso {permiso.get_estado_display().lower()}","mensaje":f"Tu solicitud de {permiso.get_tipo_display().lower()} fue resuelta.","url_destino":"/rrhh/mi-perfil/"})
 return permiso
