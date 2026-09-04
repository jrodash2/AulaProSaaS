from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from alumnos.models import Alumno,AlumnoEncargado,DocumentoAlumno,Encargado,Familia,Inscripcion,TipoDocumentoAlumno
from suscripciones.services import validar_cupo_alumnos
from .models import Aspirante,SolicitudAdmision

def posibles_duplicados(institucion,nombres,apellidos,fecha_nacimiento,cui="",correo=""):
 q=Aspirante.objects.filter(institucion=institucion)
 return q.filter(cui=cui).exists() if cui else q.filter(nombres__iexact=nombres,apellidos__iexact=apellidos,fecha_nacimiento=fecha_nacimiento).exists() or bool(correo and q.filter(correo__iexact=correo).exists())

def cambiar_estado(solicitud,estado,motivo=""):
 if estado not in SolicitudAdmision.Estado.values:raise ValidationError("Estado inválido.")
 solicitud.estado=estado
 if estado==SolicitudAdmision.Estado.RECHAZADA:solicitud.motivo_rechazo=motivo
 solicitud.aspirante.estado={"APROBADA":"APROBADO","RECHAZADA":"RECHAZADO","LISTA_ESPERA":"LISTA_ESPERA"}.get(estado,"EN_PROCESO")
 solicitud.aspirante.save();solicitud.save();return solicitud

def documentos_completos(solicitud):
 requeridos=solicitud.institucion.tipodocumentoadmision_set.filter(activo=True,obligatorio=True);aprobados=solicitud.documentos.filter(tipo__in=requeridos,estado="APROBADO").values("tipo").distinct().count();return aprobados,requeridos.count()

def aprobar(solicitud):
 config=getattr(solicitud.institucion,"configuracion_admision",None)
 if config and config.requiere_documentos_completos_para_aprobar:
  completos,total=documentos_completos(solicitud)
  if completos<total:raise ValidationError("Faltan documentos obligatorios.")
 return cambiar_estado(solicitud,"APROBADA")

@transaction.atomic
def convertir_solicitud_a_alumno(solicitud,seccion,usuario=None):
 solicitud=SolicitudAdmision.objects.select_for_update().select_related("aspirante","ciclo_solicitado","oferta_solicitada","grado_solicitado").get(pk=solicitud.pk)
 if solicitud.estado not in ("APROBADA","INSCRITA"):raise ValidationError("Solo una solicitud aprobada puede convertirse.")
 if seccion.institucion_id!=solicitud.institucion_id or seccion.ciclo_id!=solicitud.ciclo_solicitado_id:raise ValidationError("Sección destino inválida.")
 aspirante=solicitud.aspirante
 alumno=Alumno.objects.filter(institucion=solicitud.institucion,cui=aspirante.cui).first() if aspirante.cui else None
 if not alumno:
  validar_cupo_alumnos(solicitud.institucion)
  alumno=Alumno.objects.create(institucion=solicitud.institucion,cui=aspirante.cui or None,primer_nombre=aspirante.nombres,primer_apellido=aspirante.apellidos,fecha_nacimiento=aspirante.fecha_nacimiento,sexo=aspirante.sexo or "O",telefono=aspirante.telefono,email=aspirante.correo,direccion=aspirante.direccion,fecha_ingreso=solicitud.fecha_solicitud)
 encargado_asp=aspirante.encargados.order_by("-es_principal","pk").first();familia=None
 if encargado_asp:
  filtros={"institucion":solicitud.institucion};encargado=None
  if encargado_asp.dpi:encargado=Encargado.objects.filter(**filtros,cui=encargado_asp.dpi).first()
  if not encargado and encargado_asp.correo:encargado=Encargado.objects.filter(**filtros,email__iexact=encargado_asp.correo).first()
  if not encargado:encargado=Encargado.objects.create(**filtros,cui=encargado_asp.dpi or None,nombres=encargado_asp.nombres,apellidos=encargado_asp.apellidos,telefono=encargado_asp.telefono,email=encargado_asp.correo,direccion=encargado_asp.direccion)
  familia=encargado.vinculos_alumnos.select_related("alumno__familia").filter(alumno__familia__isnull=False).values_list("alumno__familia",flat=True).first()
  familia=Familia.objects.filter(pk=familia).first() if familia else Familia.objects.create(institucion=solicitud.institucion,nombre_referencia=f"Familia {encargado.apellidos or encargado.nombres}",direccion=encargado.direccion,telefono_principal=encargado.telefono,email_principal=encargado.email)
  if alumno.familia_id!=familia.pk:alumno.familia=familia;alumno.save()
  AlumnoEncargado.objects.get_or_create(institucion=solicitud.institucion,alumno=alumno,encargado=encargado,defaults={"parentesco":encargado_asp.parentesco if encargado_asp.parentesco in AlumnoEncargado.Parentesco.values else "OTRO","parentesco_otro":"" if encargado_asp.parentesco in AlumnoEncargado.Parentesco.values else encargado_asp.parentesco,"es_principal":True})
 if Inscripcion.objects.filter(institucion=solicitud.institucion,alumno=alumno,ciclo=solicitud.ciclo_solicitado,estado="ACTIVA").exists():raise ValidationError("El alumno ya tiene inscripción activa en el ciclo.")
 ins=Inscripcion.objects.create(institucion=solicitud.institucion,alumno=alumno,ciclo=solicitud.ciclo_solicitado,oferta_academica=solicitud.oferta_solicitada,grado=seccion.grado,seccion=seccion,fecha_inscripcion=__import__('django.utils.timezone',fromlist=['localdate']).localdate())
 for doc in solicitud.documentos.filter(estado="APROBADO").select_related("tipo"):
  tipo=TipoDocumentoAlumno.objects.filter(institucion=solicitud.institucion,codigo=doc.tipo.codigo).first()
  if tipo and doc.archivo:
   doc.archivo.open('rb');contenido=ContentFile(doc.archivo.read(),name=doc.nombre_original);doc.archivo.close();DocumentoAlumno.objects.create(institucion=solicitud.institucion,alumno=alumno,tipo_documento=tipo,inscripcion=ins,ciclo=ins.ciclo,estado="APROBADO",archivo=contenido,nombre_original=doc.nombre_original,cargado_por=usuario,revisado_por=usuario)
 solicitud.estado="INSCRITA";solicitud.save();aspirante.estado="INSCRITO";aspirante.save();return alumno,ins
