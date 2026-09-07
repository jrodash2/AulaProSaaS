from pathlib import Path
from uuid import uuid4
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

EXTENSIONES=("pdf","jpg","jpeg","png")
def validar_adjunto(archivo):
    if archivo.size>10*1024*1024: raise ValidationError("El archivo excede 10 MB.")
    if Path(archivo.name).suffix.lower().lstrip(".") not in EXTENSIONES: raise ValidationError("Tipo de archivo no permitido.")
def ruta_adjunto(instance,filename): return f"seguimiento/{instance.institucion_id}/{instance.registro.alumno_id}/{uuid4().hex}{Path(filename).suffix.lower()}"

class CategoriaSeguimiento(models.Model):
    class Tipo(models.TextChoices): POSITIVO="POSITIVO","Positivo";INCIDENCIA="INCIDENCIA","Incidencia";ACADEMICO="ACADEMICO","Académico";CONVIVENCIA="CONVIVENCIA","Convivencia";OTRO="OTRO","Otro"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="categorias_seguimiento");codigo=models.CharField(max_length=40);nombre=models.CharField(max_length=120);tipo=models.CharField(max_length=15,choices=Tipo.choices);descripcion=models.TextField(blank=True);color=models.CharField(max_length=20,blank=True);activo=models.BooleanField(default=True);orden=models.PositiveSmallIntegerField(default=0)
    class Meta: ordering=("orden","nombre");constraints=[models.UniqueConstraint(fields=("institucion","codigo"),name="seg_categoria_codigo_inst")]
    def save(self,*a,**kw): self.codigo=self.codigo.upper().strip();self.full_clean();return super().save(*a,**kw)
    def __str__(self): return self.nombre

class RegistroSeguimiento(models.Model):
    class Gravedad(models.TextChoices): NO_APLICA="NO_APLICA","No aplica";BAJA="BAJA","Baja";MEDIA="MEDIA","Media";ALTA="ALTA","Alta";CRITICA="CRITICA","Crítica"
    class Estado(models.TextChoices): ABIERTO="ABIERTO","Abierto";EN_SEGUIMIENTO="EN_SEGUIMIENTO","En seguimiento";RESUELTO="RESUELTO","Resuelto";CERRADO="CERRADO","Cerrado";ANULADO="ANULADO","Anulado"
    class Confidencialidad(models.TextChoices): INTERNO="INTERNO","Interno";DOCENTES="DOCENTES","Docentes";PADRES="PADRES","Padres";PUBLICABLE_PORTAL="PUBLICABLE_PORTAL","Publicable en portal"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="registros_seguimiento");alumno=models.ForeignKey("alumnos.Alumno",on_delete=models.PROTECT,related_name="registros_seguimiento");inscripcion=models.ForeignKey("alumnos.Inscripcion",on_delete=models.PROTECT,related_name="registros_seguimiento");ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="registros_seguimiento");categoria=models.ForeignKey(CategoriaSeguimiento,on_delete=models.PROTECT,related_name="registros");tipo=models.CharField(max_length=15,choices=CategoriaSeguimiento.Tipo.choices);fecha=models.DateField(default=timezone.localdate);titulo=models.CharField(max_length=180);descripcion=models.TextField();gravedad=models.CharField(max_length=12,choices=Gravedad.choices,default=Gravedad.NO_APLICA);confidencialidad=models.CharField(max_length=20,choices=Confidencialidad.choices,default=Confidencialidad.INTERNO);curso=models.ForeignKey("academico.CursoInstitucion",null=True,blank=True,on_delete=models.PROTECT);docente=models.ForeignKey("docentes.Docente",null=True,blank=True,on_delete=models.PROTECT);registrado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="seguimientos_creados");estado=models.CharField(max_length=20,choices=Estado.choices,default=Estado.ABIERTO);conclusion=models.TextField(blank=True);cerrado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.PROTECT,related_name="seguimientos_cerrados");fecha_cierre=models.DateTimeField(null=True,blank=True);motivo_anulacion=models.TextField(blank=True);fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta: ordering=("-fecha","-fecha_creacion");indexes=[models.Index(fields=("institucion","ciclo","estado"),name="seg_inst_ciclo_estado"),models.Index(fields=("alumno","fecha"),name="seg_alumno_fecha")]
    def clean(self):
        e={}
        for f in ("alumno","inscripcion","ciclo","categoria","curso","docente"):
            o=getattr(self,f,None)
            if o and o.institucion_id!=self.institucion_id:e[f]="No pertenece a la institución."
        if self.inscripcion_id and (self.inscripcion.alumno_id!=self.alumno_id or self.inscripcion.ciclo_id!=self.ciclo_id):e["inscripcion"]="No corresponde al alumno y ciclo."
        if self.tipo==CategoriaSeguimiento.Tipo.POSITIVO and self.gravedad!=self.Gravedad.NO_APLICA:e["gravedad"]="Un reconocimiento no requiere gravedad."
        if self.estado==self.Estado.CERRADO and not self.conclusion.strip():e["conclusion"]="La conclusión es obligatoria para cerrar."
        if self.estado==self.Estado.ANULADO and not self.motivo_anulacion.strip():e["motivo_anulacion"]="El motivo es obligatorio para anular."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
    def __str__(self):return f"{self.alumno} · {self.titulo}"

class CompromisoSeguimiento(models.Model):
    class Responsable(models.TextChoices):ALUMNO="ALUMNO","Alumno";PADRE="PADRE","Padre";DOCENTE="DOCENTE","Docente";INSTITUCION="INSTITUCION","Institución";OTRO="OTRO","Otro"
    class Estado(models.TextChoices):PENDIENTE="PENDIENTE","Pendiente";CUMPLIDO="CUMPLIDO","Cumplido";VENCIDO="VENCIDO","Vencido";CANCELADO="CANCELADO","Cancelado"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);registro=models.ForeignKey(RegistroSeguimiento,on_delete=models.CASCADE,related_name="compromisos");descripcion=models.TextField();responsable=models.CharField(max_length=15,choices=Responsable.choices);fecha_compromiso=models.DateField(default=timezone.localdate);fecha_limite=models.DateField(null=True,blank=True);estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.PENDIENTE);cumplido_fecha=models.DateField(null=True,blank=True);creado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    @property
    def estado_vigente(self):return self.Estado.VENCIDO if self.estado==self.Estado.PENDIENTE and self.fecha_limite and self.fecha_limite<timezone.localdate() else self.estado
    def clean(self):
        if self.registro_id and self.registro.institucion_id!=self.institucion_id:raise ValidationError({"registro":"No pertenece a la institución."})
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)

class NotaSeguimiento(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);registro=models.ForeignKey(RegistroSeguimiento,on_delete=models.CASCADE,related_name="notas");fecha=models.DateField(default=timezone.localdate);comentario=models.TextField();autor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT);visible_padre=models.BooleanField(default=False);fecha_creacion=models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.registro_id and self.registro.institucion_id!=self.institucion_id:raise ValidationError({"registro":"No pertenece a la institución."})
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)

class ReunionSeguimiento(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);alumno=models.ForeignKey("alumnos.Alumno",on_delete=models.PROTECT,related_name="reuniones_seguimiento");registro=models.ForeignKey(RegistroSeguimiento,null=True,blank=True,on_delete=models.PROTECT,related_name="reuniones");fecha=models.DateTimeField();encargado=models.ForeignKey("alumnos.Encargado",null=True,blank=True,on_delete=models.PROTECT);participantes=models.TextField(blank=True);motivo=models.TextField();acuerdos=models.TextField(blank=True);observaciones=models.TextField(blank=True);creado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT);fecha_creacion=models.DateTimeField(auto_now_add=True)
    def clean(self):
        e={}
        for f in ("alumno","registro","encargado"):
            o=getattr(self,f,None)
            if o and o.institucion_id!=self.institucion_id:e[f]="No pertenece a la institución."
        if self.registro_id and self.registro.alumno_id!=self.alumno_id:e["registro"]="No corresponde al alumno."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)

class AdjuntoSeguimiento(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);registro=models.ForeignKey(RegistroSeguimiento,on_delete=models.CASCADE,related_name="adjuntos");archivo=models.FileField(upload_to=ruta_adjunto,validators=[FileExtensionValidator(EXTENSIONES),validar_adjunto]);nombre_original=models.CharField(max_length=255);cargado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT);fecha_creacion=models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.registro_id and self.registro.institucion_id!=self.institucion_id:raise ValidationError({"registro":"No pertenece a la institución."})
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
