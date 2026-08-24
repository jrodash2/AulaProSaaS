from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

EXTENSIONES=("pdf","doc","docx","xls","xlsx","jpg","jpeg","png")
def validar_adjunto(archivo):
    if Path(archivo.name).suffix.lower().lstrip(".") not in EXTENSIONES: raise ValidationError("Tipo de archivo no permitido.")
    if archivo.size>getattr(settings,"COMUNICACIONES_MAX_UPLOAD_SIZE",10*1024*1024): raise ValidationError("El archivo excede el límite de 10 MB.")
def ruta_adjunto(instance,filename): return f"comunicaciones/{instance.institucion_id}/{instance.comunicacion_id}/{Path(filename).name}"

class Comunicacion(models.Model):
    class Tipo(models.TextChoices): ANUNCIO="ANUNCIO","Anuncio";CIRCULAR="CIRCULAR","Circular";AVISO="AVISO","Aviso";RECORDATORIO="RECORDATORIO","Recordatorio"
    class Prioridad(models.TextChoices): NORMAL="NORMAL","Normal";IMPORTANTE="IMPORTANTE","Importante";URGENTE="URGENTE","Urgente"
    class Estado(models.TextChoices): BORRADOR="BORRADOR","Borrador";PROGRAMADA="PROGRAMADA","Programada";PUBLICADA="PUBLICADA","Publicada";ARCHIVADA="ARCHIVADA","Archivada";ANULADA="ANULADA","Anulada"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="comunicaciones")
    titulo=models.CharField(max_length=200);contenido=models.TextField();resumen=models.CharField(max_length=280,blank=True)
    tipo=models.CharField(max_length=15,choices=Tipo.choices,default=Tipo.AVISO);prioridad=models.CharField(max_length=12,choices=Prioridad.choices,default=Prioridad.NORMAL);estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.BORRADOR)
    fecha_publicacion=models.DateTimeField(default=timezone.now);fecha_expiracion=models.DateTimeField(null=True,blank=True)
    creada_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="comunicaciones_creadas");publicada_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="comunicaciones_publicadas")
    motivo_anulacion=models.TextField(blank=True);anulada_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="comunicaciones_anuladas");fecha_anulacion=models.DateTimeField(null=True,blank=True)
    fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("-fecha_publicacion",);indexes=[models.Index(fields=("institucion","estado"),name="com_inst_estado_idx"),models.Index(fields=("institucion","fecha_publicacion"),name="com_inst_public_idx")]
    def clean(self):
        e={}
        if self.fecha_expiracion and self.fecha_expiracion<self.fecha_publicacion:e["fecha_expiracion"]="Debe ser posterior a la publicación."
        if self.estado==self.Estado.PROGRAMADA and self.fecha_publicacion<=timezone.now():e["fecha_publicacion"]="Una comunicación programada requiere una fecha futura."
        if self.estado==self.Estado.ANULADA and not self.motivo_anulacion.strip():e["motivo_anulacion"]="El motivo es obligatorio."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
    @property
    def visible(self):return self.estado in {self.Estado.PUBLICADA,self.Estado.ARCHIVADA} or (self.estado==self.Estado.PROGRAMADA and self.fecha_publicacion<=timezone.now())
    def __str__(self):return self.titulo

class ComunicacionAudiencia(models.Model):
    comunicacion=models.ForeignKey(Comunicacion,on_delete=models.CASCADE,related_name="audiencias");rol=models.CharField(max_length=20)
    class Meta:constraints=[models.UniqueConstraint(fields=("comunicacion","rol"),name="com_audiencia_unica")]

class ComunicacionDestino(models.Model):
    class Tipo(models.TextChoices):INSTITUCION="INSTITUCION","Toda la institución";ROL="ROL","Rol";GRADO="GRADO","Grado";SECCION="SECCION","Sección";CURSO="CURSO","Curso";USUARIO="USUARIO","Usuario"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="destinos_comunicaciones");comunicacion=models.ForeignKey(Comunicacion,on_delete=models.CASCADE,related_name="destinos");tipo_destino=models.CharField(max_length=12,choices=Tipo.choices)
    ciclo=models.ForeignKey("academico.CicloEscolar",null=True,blank=True,on_delete=models.PROTECT);grado=models.ForeignKey("academico.GradoInstitucion",null=True,blank=True,on_delete=models.PROTECT);seccion=models.ForeignKey("academico.Seccion",null=True,blank=True,on_delete=models.PROTECT);curso=models.ForeignKey("academico.CursoInstitucion",null=True,blank=True,on_delete=models.PROTECT);rol=models.CharField(max_length=20,blank=True);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.PROTECT)
    def clean(self):
        e={}
        if self.comunicacion_id and self.comunicacion.institucion_id!=self.institucion_id:e["comunicacion"]="No pertenece a la institución."
        for f in ("ciclo","grado","seccion","curso"):
            o=getattr(self,f,None)
            if o and o.institucion_id!=self.institucion_id:e[f]="No pertenece a la institución."
        if self.usuario_id and not self.usuario.asignaciones_institucion.filter(institucion_id=self.institucion_id,activo=True).exists():e["usuario"]="No pertenece a la institución."
        required={self.Tipo.ROL:"rol",self.Tipo.GRADO:"grado",self.Tipo.SECCION:"seccion",self.Tipo.CURSO:"curso",self.Tipo.USUARIO:"usuario"}
        field=required.get(self.tipo_destino)
        if field and not getattr(self,f"{field}_id",None) and not getattr(self,field,None):e[field]="Este destino requiere una selección."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)

class AdjuntoComunicacion(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="adjuntos_comunicaciones");comunicacion=models.ForeignKey(Comunicacion,on_delete=models.CASCADE,related_name="adjuntos");archivo=models.FileField(upload_to=ruta_adjunto,validators=[FileExtensionValidator(EXTENSIONES),validar_adjunto]);nombre_original=models.CharField(max_length=255);fecha_creacion=models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.comunicacion_id and self.comunicacion.institucion_id!=self.institucion_id:raise ValidationError({"comunicacion":"No pertenece a la institución."})
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)

class Notificacion(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="notificaciones");usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="notificaciones");comunicacion=models.ForeignKey(Comunicacion,null=True,blank=True,on_delete=models.CASCADE,related_name="notificaciones")
    titulo=models.CharField(max_length=200);mensaje=models.CharField(max_length=400,blank=True);tipo_origen=models.CharField(max_length=30,default="COMUNICACION");origen_id=models.CharField(max_length=80,blank=True);url_destino=models.CharField(max_length=500,blank=True);leida=models.BooleanField(default=False);fecha_lectura=models.DateTimeField(null=True,blank=True);fecha_creacion=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=("-fecha_creacion",);constraints=[models.UniqueConstraint(fields=("comunicacion","usuario"),condition=Q(comunicacion__isnull=False),name="notif_com_usuario_unica"),models.UniqueConstraint(fields=("institucion","usuario","tipo_origen","origen_id"),condition=~Q(origen_id=""),name="notif_origen_usuario_unica")];indexes=[models.Index(fields=("usuario","leida"),name="notif_usuario_leida_idx")]
    def clean(self):
        if self.usuario_id and not self.usuario.asignaciones_institucion.filter(institucion_id=self.institucion_id,activo=True).exists():raise ValidationError({"usuario":"No pertenece a la institución."})
        if self.comunicacion_id and self.comunicacion.institucion_id!=self.institucion_id:raise ValidationError({"comunicacion":"No pertenece a la institución."})
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
