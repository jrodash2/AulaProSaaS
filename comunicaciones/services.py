from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from alumnos.models import Inscripcion
from auditoria.services import registrar_evento
from instituciones.models import UsuarioInstitucion
from .models import Comunicacion,ComunicacionDestino,Notificacion
GESTION={"PROPIETARIO","DIRECTOR","ADMINISTRADOR","SECRETARIA"}
ADMIN_ROLES={"PROPIETARIO","DIRECTOR","ADMINISTRADOR","SECRETARIA","CONTABILIDAD"}
def rol(request):return request.asignacion_institucion.rol
def puede_gestionar(request):return rol(request) in GESTION
def puede_crear(request):return rol(request) in GESTION or rol(request)=="DOCENTE"
def docente_destinos_validos(request,comunicacion):
    if rol(request)!="DOCENTE":return True
    from docentes.models import AsignacionDocente
    asignadas=AsignacionDocente.objects.filter(institucion=request.institucion,docente__usuario=request.user,activa=True)
    for d in comunicacion.destinos.all():
        if d.tipo_destino=="SECCION" and asignadas.filter(seccion=d.seccion).exists():continue
        if d.tipo_destino=="CURSO" and asignadas.filter(curso=d.curso).exists():continue
        return False
    return comunicacion.destinos.exists()
def comunicaciones_visibles(usuario,institucion):
    ahora=timezone.now();return Comunicacion.objects.filter(institucion=institucion,notificaciones__usuario=usuario).filter(Q(estado__in=("PUBLICADA","ARCHIVADA"))|Q(estado="PROGRAMADA",fecha_publicacion__lte=ahora)).distinct()
def resolver_destinatarios(comunicacion):
    audiencias=set(comunicacion.audiencias.values_list("rol",flat=True));ids=set();base=UsuarioInstitucion.objects.filter(institucion=comunicacion.institucion,activo=True,usuario__is_active=True)
    for d in comunicacion.destinos.select_related("grado","seccion","curso","usuario"):
        if d.tipo_destino=="USUARIO":ids.add(d.usuario_id);continue
        if d.tipo_destino=="ROL":ids.update(base.filter(rol=d.rol).values_list("usuario_id",flat=True));continue
        if d.tipo_destino=="INSTITUCION":
            q=base.filter(rol__in=audiencias) if audiencias else base
            ids.update(q.values_list("usuario_id",flat=True));continue
        ins=Inscripcion.objects.filter(institucion=comunicacion.institucion,estado="ACTIVA")
        if d.tipo_destino=="GRADO":ins=ins.filter(grado=d.grado)
        elif d.tipo_destino=="SECCION":ins=ins.filter(seccion=d.seccion)
        elif d.tipo_destino=="CURSO":ins=ins.filter(seccion__asignaciones_docentes__curso=d.curso,ciclo=d.curso.ciclo).distinct()
        if "ALUMNO" in audiencias:ids.update(ins.exclude(alumno__usuario=None).values_list("alumno__usuario_id",flat=True))
        if "PADRE" in audiencias:ids.update(ins.filter(alumno__vinculos_encargados__activo=True,alumno__vinculos_encargados__encargado__activo=True).exclude(alumno__vinculos_encargados__encargado__usuario=None).values_list("alumno__vinculos_encargados__encargado__usuario_id",flat=True))
        if "DOCENTE" in audiencias:
            asigs=comunicacion.institucion.asignaciones_docentes.filter(activa=True)
            if d.tipo_destino=="GRADO":asigs=asigs.filter(grado=d.grado)
            elif d.tipo_destino=="SECCION":asigs=asigs.filter(seccion=d.seccion)
            else:asigs=asigs.filter(curso=d.curso)
            ids.update(asigs.exclude(docente__usuario=None).values_list("docente__usuario_id",flat=True))
        admin_aud=audiencias&ADMIN_ROLES
        if admin_aud:ids.update(base.filter(rol__in=admin_aud).values_list("usuario_id",flat=True))
    return base.filter(usuario_id__in=ids).values_list("usuario",flat=True)
@transaction.atomic
def sincronizar_notificaciones(comunicacion):
    usuarios=list(resolver_destinatarios(comunicacion));url=reverse("comunicaciones:detalle",args=[comunicacion.pk])
    Notificacion.objects.bulk_create([Notificacion(institucion=comunicacion.institucion,comunicacion=comunicacion,usuario_id=u,titulo=comunicacion.titulo,mensaje=comunicacion.resumen or comunicacion.contenido[:200],tipo_origen="COMUNICACION",origen_id=str(comunicacion.pk),url_destino=url) for u in usuarios],ignore_conflicts=True)
    return comunicacion.notificaciones.count()
def crear_notificacion(*,institucion,usuario,titulo,mensaje="",tipo="SISTEMA",url="",origen_id=""):
    return Notificacion.objects.get_or_create(institucion=institucion,usuario=usuario,tipo_origen=tipo,origen_id=str(origen_id),defaults={"titulo":titulo,"mensaje":mensaje,"url_destino":url})[0]
@transaction.atomic
def publicar(request,comunicacion):
    if not puede_crear(request) or not docente_destinos_validos(request,comunicacion):raise PermissionDenied
    if not comunicacion.destinos.exists():raise ValidationError("Seleccione al menos un destino.")
    comunicacion.estado="PROGRAMADA" if comunicacion.fecha_publicacion>timezone.now() else "PUBLICADA";comunicacion.publicada_por=request.user;comunicacion.save()
    if comunicacion.estado=="PUBLICADA":sincronizar_notificaciones(comunicacion)
    registrar_evento(request,"PROGRAMAR_COMUNICACION" if comunicacion.estado=="PROGRAMADA" else "PUBLICAR_COMUNICACION",comunicacion);return comunicacion
@transaction.atomic
def anular(request,comunicacion,motivo):
    if not puede_gestionar(request) or not motivo.strip():raise PermissionDenied
    comunicacion.estado="ANULADA";comunicacion.motivo_anulacion=motivo;comunicacion.anulada_por=request.user;comunicacion.fecha_anulacion=timezone.now();comunicacion.save();registrar_evento(request,"ANULAR_COMUNICACION",comunicacion,detalles={"motivo":motivo});return comunicacion
def notificar_tarea(tarea):
    ins=Inscripcion.objects.filter(institucion=tarea.institucion,ciclo=tarea.ciclo,seccion=tarea.seccion,estado="ACTIVA")
    ids=set(ins.exclude(alumno__usuario=None).values_list("alumno__usuario_id",flat=True));ids.update(ins.filter(alumno__vinculos_encargados__activo=True).exclude(alumno__vinculos_encargados__encargado__usuario=None).values_list("alumno__vinculos_encargados__encargado__usuario_id",flat=True))
    from cuentas.models import Usuario
    for u in Usuario.objects.filter(pk__in=ids):crear_notificacion(institucion=tarea.institucion,usuario=u,titulo=f"Nueva tarea: {tarea.curso}",mensaje=f"{tarea.titulo} · vence {timezone.localtime(tarea.fecha_limite):%d/%m/%Y}",tipo="TAREA",url=reverse("portal:tarea",args=[u.perfil_alumno.pk,tarea.pk]) if hasattr(u,"perfil_alumno") else reverse("portal:dashboard"),origen_id=tarea.pk)
