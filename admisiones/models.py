from pathlib import Path
from uuid import uuid4
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models,transaction
from django.db.models import Q,Max
from django.utils import timezone
from alumnos.models import cui_validator
EXT=("pdf","jpg","jpeg","png","webp")
def validar_archivo(f):
 if f.size>10*1024*1024:raise ValidationError("El archivo excede 10 MB.")
 if Path(f.name).suffix.lower().lstrip('.') not in EXT:raise ValidationError("Tipo de archivo no permitido.")
def ruta(instance,filename):return f"admisiones/{instance.institucion_id}/{instance.solicitud.token}/{uuid4().hex}{Path(filename).suffix.lower()}"
class ConfiguracionAdmision(models.Model):
 institucion=models.OneToOneField("instituciones.Institucion",on_delete=models.CASCADE,related_name="configuracion_admision");admisiones_abiertas=models.BooleanField(default=False);titulo_publico=models.CharField(max_length=180,default="Proceso de admisión");mensaje_publico=models.TextField(blank=True);ciclo_predeterminado=models.ForeignKey("academico.CicloEscolar",null=True,blank=True,on_delete=models.PROTECT);requiere_cui=models.BooleanField(default=False);permitir_carga_documentos=models.BooleanField(default=True);requiere_documentos_completos_para_aprobar=models.BooleanField(default=False);correo_contacto=models.EmailField(blank=True);telefono_contacto=models.CharField(max_length=30,blank=True)
class Aspirante(models.Model):
 class Estado(models.TextChoices):PROSPECTO="PROSPECTO","Prospecto";EN_PROCESO="EN_PROCESO","En proceso";APROBADO="APROBADO","Aprobado";RECHAZADO="RECHAZADO","Rechazado";LISTA_ESPERA="LISTA_ESPERA","Lista de espera";INSCRITO="INSCRITO","Inscrito";RETIRADO="RETIRADO","Retirado"
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="aspirantes");nombres=models.CharField(max_length=160);apellidos=models.CharField(max_length=160);cui=models.CharField(max_length=13,null=True,blank=True,validators=[cui_validator]);fecha_nacimiento=models.DateField();sexo=models.CharField(max_length=1,blank=True,choices=(("F","Femenino"),("M","Masculino"),("O","Otro")));telefono=models.CharField(max_length=30,blank=True);correo=models.EmailField(blank=True);direccion=models.TextField(blank=True);colegio_anterior=models.CharField(max_length=180,blank=True);ultimo_grado_cursado=models.CharField(max_length=120,blank=True);estado=models.CharField(max_length=15,choices=Estado.choices,default=Estado.PROSPECTO);posible_duplicado=models.BooleanField(default=False);creado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL);fecha_registro=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
 class Meta:indexes=[models.Index(fields=("institucion","estado"),name="asp_inst_estado_idx")]
 def clean(self):
  if self.fecha_nacimiento and self.fecha_nacimiento>timezone.localdate():raise ValidationError({"fecha_nacimiento":"No puede ser futura."})
 @property
 def nombre_completo(self):return f"{self.nombres} {self.apellidos}".strip()
 def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
 def __str__(self):return self.nombre_completo
class EncargadoAspirante(models.Model):
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);aspirante=models.ForeignKey(Aspirante,on_delete=models.CASCADE,related_name="encargados");nombres=models.CharField(max_length=160);apellidos=models.CharField(max_length=160,blank=True);parentesco=models.CharField(max_length=30,default="PADRE");telefono=models.CharField(max_length=30);correo=models.EmailField(blank=True);direccion=models.TextField(blank=True);dpi=models.CharField(max_length=13,blank=True);es_principal=models.BooleanField(default=True)
 def clean(self):
  if self.aspirante_id and self.aspirante.institucion_id!=self.institucion_id:raise ValidationError("Tenant inválido.")
 def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
class SolicitudAdmision(models.Model):
 class Estado(models.TextChoices):NUEVA="NUEVA","Nueva";EN_REVISION="EN_REVISION","En revisión";DOCUMENTACION_PENDIENTE="DOCUMENTACION_PENDIENTE","Documentación pendiente";ENTREVISTA_PENDIENTE="ENTREVISTA_PENDIENTE","Entrevista pendiente";EVALUACION_PENDIENTE="EVALUACION_PENDIENTE","Evaluación pendiente";EN_DECISION="EN_DECISION","En decisión";APROBADA="APROBADA","Aprobada";LISTA_ESPERA="LISTA_ESPERA","Lista de espera";RECHAZADA="RECHAZADA","Rechazada";INSCRITA="INSCRITA","Inscrita";CANCELADA="CANCELADA","Cancelada"
 class Origen(models.TextChoices):REFERIDO="REFERIDO","Referido";REDES_SOCIALES="REDES_SOCIALES","Redes sociales";PAGINA_WEB="PAGINA_WEB","Página web";PUBLICIDAD="PUBLICIDAD","Publicidad";VISITA="VISITA","Visita";OTRO="OTRO","Otro"
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="solicitudes_admision");aspirante=models.ForeignKey(Aspirante,on_delete=models.PROTECT,related_name="solicitudes");ciclo_solicitado=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT);jornada_solicitada=models.ForeignKey("academico.JornadaInstitucion",null=True,blank=True,on_delete=models.PROTECT);oferta_solicitada=models.ForeignKey("academico.OfertaAcademica",on_delete=models.PROTECT);grado_solicitado=models.ForeignKey("academico.GradoInstitucion",on_delete=models.PROTECT);numero_solicitud=models.CharField(max_length=24,blank=True);secuencia=models.PositiveIntegerField(null=True,editable=False);token=models.UUIDField(default=uuid4,unique=True,editable=False);fecha_solicitud=models.DateField(default=timezone.localdate);estado=models.CharField(max_length=30,choices=Estado.choices,default=Estado.NUEVA);origen=models.CharField(max_length=20,choices=Origen.choices,default=Origen.OTRO);observaciones=models.TextField(blank=True);motivo_rechazo=models.TextField(blank=True);posicion_espera=models.PositiveIntegerField(null=True,blank=True);fecha_lista_espera=models.DateField(null=True,blank=True);creada_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL);fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
 class Meta:ordering=("-fecha_solicitud",);constraints=[models.UniqueConstraint(fields=("institucion","numero_solicitud"),name="sol_numero_unico_inst"),models.UniqueConstraint(fields=("institucion","ciclo_solicitado","secuencia"),name="sol_secuencia_unica")];indexes=[models.Index(fields=("institucion","estado"),name="sol_inst_estado_idx")]
 def clean(self):
  e={}
  for f in ("aspirante","ciclo_solicitado","jornada_solicitada","oferta_solicitada","grado_solicitado"):
   o=getattr(self,f,None)
   if o and o.institucion_id!=self.institucion_id:e[f]="No pertenece a la institución."
  if self.grado_solicitado_id and self.grado_solicitado.oferta_id!=self.oferta_solicitada_id:e["grado_solicitado"]="No pertenece a la oferta."
  if self.estado==self.Estado.RECHAZADA and not self.motivo_rechazo.strip():e["motivo_rechazo"]="El motivo interno es obligatorio."
  if e:raise ValidationError(e)
 def save(self,*a,**kw):
  with transaction.atomic():
   if not self.secuencia:
    self.institucion.__class__.objects.select_for_update().get(pk=self.institucion_id);self.secuencia=(type(self).objects.filter(institucion=self.institucion,ciclo_solicitado=self.ciclo_solicitado).aggregate(m=Max("secuencia"))["m"] or 0)+1;self.numero_solicitud=f"ADM-{self.ciclo_solicitado.anio}-{self.secuencia:05d}"
   self.full_clean();return super().save(*a,**kw)
 def __str__(self):return self.numero_solicitud
class TipoDocumentoAdmision(models.Model):
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);codigo=models.CharField(max_length=40);nombre=models.CharField(max_length=140);obligatorio=models.BooleanField(default=True);activo=models.BooleanField(default=True)
 class Meta:constraints=[models.UniqueConstraint(fields=("institucion","codigo"),name="tipo_doc_adm_unico")]
class DocumentoAdmision(models.Model):
 class Estado(models.TextChoices):ENTREGADO="ENTREGADO","Entregado";APROBADO="APROBADO","Aprobado";RECHAZADO="RECHAZADO","Rechazado"
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);solicitud=models.ForeignKey(SolicitudAdmision,on_delete=models.CASCADE,related_name="documentos");tipo=models.ForeignKey(TipoDocumentoAdmision,on_delete=models.PROTECT);archivo=models.FileField(upload_to=ruta,validators=[FileExtensionValidator(EXT),validar_archivo]);nombre_original=models.CharField(max_length=255);estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.ENTREGADO);fecha_carga=models.DateTimeField(auto_now_add=True)
 def clean(self):
  if self.solicitud_id and (self.solicitud.institucion_id!=self.institucion_id or self.tipo.institucion_id!=self.institucion_id):raise ValidationError("Tenant inválido.")
 def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
class EntrevistaAdmision(models.Model):
 class Modalidad(models.TextChoices):PRESENCIAL="PRESENCIAL","Presencial";VIRTUAL="VIRTUAL","Virtual";TELEFONICA="TELEFONICA","Telefónica"
 class Estado(models.TextChoices):PROGRAMADA="PROGRAMADA","Programada";REALIZADA="REALIZADA","Realizada";REPROGRAMADA="REPROGRAMADA","Reprogramada";CANCELADA="CANCELADA","Cancelada";NO_ASISTIO="NO_ASISTIO","No asistió"
 class Recomendacion(models.TextChoices):FAVORABLE="FAVORABLE","Favorable";FAVORABLE_CON_OBSERVACIONES="FAVORABLE_CON_OBSERVACIONES","Favorable con observaciones";NO_FAVORABLE="NO_FAVORABLE","No favorable";PENDIENTE="PENDIENTE","Pendiente"
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);solicitud=models.ForeignKey(SolicitudAdmision,on_delete=models.CASCADE,related_name="entrevistas");fecha_programada=models.DateTimeField();fecha_realizada=models.DateTimeField(null=True,blank=True);entrevistador=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT);modalidad=models.CharField(max_length=12,choices=Modalidad.choices);estado=models.CharField(max_length=15,choices=Estado.choices,default=Estado.PROGRAMADA);observaciones=models.TextField(blank=True);recomendacion=models.CharField(max_length=35,choices=Recomendacion.choices,default=Recomendacion.PENDIENTE)
class TipoEvaluacionAdmision(models.Model):
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);nombre=models.CharField(max_length=140);descripcion=models.TextField(blank=True);punteo_maximo=models.DecimalField(max_digits=7,decimal_places=2);punteo_minimo_referencia=models.DecimalField(max_digits=7,decimal_places=2,null=True,blank=True);activo=models.BooleanField(default=True)
class EvaluacionAdmision(models.Model):
 class Estado(models.TextChoices):PENDIENTE="PENDIENTE","Pendiente";REALIZADA="REALIZADA","Realizada";ANULADA="ANULADA","Anulada"
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);solicitud=models.ForeignKey(SolicitudAdmision,on_delete=models.CASCADE,related_name="evaluaciones");tipo_evaluacion=models.ForeignKey(TipoEvaluacionAdmision,on_delete=models.PROTECT);fecha=models.DateField(default=timezone.localdate);punteo=models.DecimalField(max_digits=7,decimal_places=2,null=True,blank=True);observaciones=models.TextField(blank=True);evaluado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT);evaluador=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.PROTECT,related_name="evaluaciones_admision_asignadas");estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.PENDIENTE)
 def clean(self):
  if self.solicitud_id and (self.solicitud.institucion_id!=self.institucion_id or self.tipo_evaluacion.institucion_id!=self.institucion_id):raise ValidationError("Tenant inválido.")
  if self.punteo is not None and (self.punteo<0 or self.punteo>self.tipo_evaluacion.punteo_maximo):raise ValidationError({"punteo":"Debe estar dentro del máximo configurado."})
 def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
