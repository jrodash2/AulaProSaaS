from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

EXTENSIONES=("pdf","doc","docx","xls","xlsx","ppt","pptx","jpg","jpeg","png","webp")
MIMES={"application/pdf","application/msword","application/vnd.openxmlformats-officedocument.wordprocessingml.document","application/vnd.ms-excel","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","application/vnd.ms-powerpoint","application/vnd.openxmlformats-officedocument.presentationml.presentation","image/jpeg","image/png","image/webp"}
def validar_archivo_seguro(archivo):
    extension=Path(archivo.name).suffix.lower().lstrip(".")
    if extension not in EXTENSIONES:raise ValidationError("Tipo de archivo no permitido.")
    if archivo.size>getattr(settings,"TAREAS_MAX_UPLOAD_SIZE",10*1024*1024):raise ValidationError("El archivo excede el límite de 10 MB.")
    content_type=getattr(archivo,"content_type",None) or getattr(getattr(archivo,"file",None),"content_type",None)
    if content_type and content_type not in MIMES:raise ValidationError("El contenido del archivo no coincide con un tipo permitido.")

def ruta_tarea(instance,filename):return f"tareas/{instance.institucion_id}/{instance.tarea_id}/{Path(filename).name}"
def ruta_entrega(instance,filename):return f"tareas/entregas/{instance.institucion_id}/{instance.entrega_id}/{Path(filename).name}"

class Tarea(models.Model):
    class Estado(models.TextChoices):BORRADOR="BORRADOR","Borrador";PUBLICADA="PUBLICADA","Publicada";CERRADA="CERRADA","Cerrada";ANULADA="ANULADA","Anulada"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="tareas")
    ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="tareas")
    asignacion_docente=models.ForeignKey("docentes.AsignacionDocente",on_delete=models.PROTECT,related_name="tareas")
    curso=models.ForeignKey("academico.CursoInstitucion",on_delete=models.PROTECT,related_name="tareas")
    grado=models.ForeignKey("academico.GradoInstitucion",on_delete=models.PROTECT,related_name="tareas")
    seccion=models.ForeignKey("academico.Seccion",on_delete=models.PROTECT,related_name="tareas")
    actividad_evaluacion=models.ForeignKey("calificaciones.ActividadEvaluacion",null=True,blank=True,on_delete=models.SET_NULL,related_name="tareas")
    titulo=models.CharField(max_length=180);descripcion=models.TextField(blank=True);instrucciones=models.TextField()
    fecha_publicacion=models.DateTimeField();fecha_limite=models.DateTimeField();estado=models.CharField(max_length=10,choices=Estado.choices,default=Estado.BORRADOR)
    permite_entrega_archivo=models.BooleanField(default=False);activa=models.BooleanField(default=True);creada_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="tareas_creadas")
    motivo_anulacion=models.TextField(blank=True);anulada_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="tareas_anuladas");fecha_anulacion=models.DateTimeField(null=True,blank=True)
    motivo_reapertura=models.TextField(blank=True);reabierta_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="tareas_reabiertas")
    fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("-fecha_publicacion","fecha_limite");indexes=[models.Index(fields=("institucion","ciclo"),name="tarea_inst_ciclo_idx"),models.Index(fields=("institucion","estado"),name="tarea_inst_estado_idx"),models.Index(fields=("seccion","fecha_limite"),name="tarea_secc_limite_idx"),models.Index(fields=("asignacion_docente","estado"),name="tarea_asig_estado_idx")]
    def clean(self):
        e={};a=self.asignacion_docente if self.asignacion_docente_id else None
        for f in ("ciclo","asignacion_docente","curso","grado","seccion"):
            o=getattr(self,f,None)
            if o and o.institucion_id!=self.institucion_id:e[f]="Debe pertenecer a la institución."
        if a and (a.ciclo_id!=self.ciclo_id or a.curso_id!=self.curso_id or a.grado_id!=self.grado_id or a.seccion_id!=self.seccion_id):e["asignacion_docente"]="La asignación no coincide con la estructura académica."
        if self.fecha_publicacion and self.fecha_limite and self.fecha_limite<self.fecha_publicacion:e["fecha_limite"]="Debe ser igual o posterior a la publicación."
        if self.actividad_evaluacion_id:
            x=self.actividad_evaluacion
            if x.institucion_id!=self.institucion_id or x.ciclo_id!=self.ciclo_id or x.curso_id!=self.curso_id or x.grado_id!=self.grado_id or x.seccion_id!=self.seccion_id or x.asignacion_docente_id!=self.asignacion_docente_id:e["actividad_evaluacion"]="La actividad evaluada no coincide con la tarea."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
    def __str__(self):return self.titulo

class AdjuntoTarea(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="adjuntos_tareas");tarea=models.ForeignKey(Tarea,on_delete=models.CASCADE,related_name="adjuntos");archivo=models.FileField(upload_to=ruta_tarea,validators=[FileExtensionValidator(EXTENSIONES),validar_archivo_seguro]);nombre_original=models.CharField(max_length=255);tipo=models.CharField(max_length=100,blank=True);fecha_creacion=models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.tarea_id and self.tarea.institucion_id!=self.institucion_id:raise ValidationError({"tarea":"La tarea no pertenece a la institución."})
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
class EntregaTarea(models.Model):
    class Estado(models.TextChoices):PENDIENTE="PENDIENTE","Pendiente";ENTREGADA="ENTREGADA","Entregada";ENTREGADA_TARDE="ENTREGADA_TARDE","Entregada tarde";NO_ENTREGADA="NO_ENTREGADA","No entregada"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="entregas_tareas");tarea=models.ForeignKey(Tarea,on_delete=models.PROTECT,related_name="entregas");alumno=models.ForeignKey("alumnos.Alumno",on_delete=models.PROTECT,related_name="entregas_tareas");inscripcion=models.ForeignKey("alumnos.Inscripcion",on_delete=models.PROTECT,related_name="entregas_tareas");estado=models.CharField(max_length=16,choices=Estado.choices,default=Estado.PENDIENTE);comentario=models.TextField(blank=True);fecha_entrega=models.DateTimeField(null=True,blank=True);entregada_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="entregas_tareas_realizadas");calificada=models.BooleanField(default=False);observacion_docente=models.TextField(blank=True);fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:constraints=[models.UniqueConstraint(fields=("tarea","alumno"),name="entrega_unica_tarea_alumno")];indexes=[models.Index(fields=("tarea","alumno"),name="entrega_tarea_alumno_idx")]
    def clean(self):
        e={}
        if self.tarea_id and self.tarea.institucion_id!=self.institucion_id:e["tarea"]="La tarea no pertenece a la institución."
        if self.alumno_id and self.alumno.institucion_id!=self.institucion_id:e["alumno"]="El alumno no pertenece a la institución."
        if self.inscripcion_id and (self.inscripcion.institucion_id!=self.institucion_id or self.inscripcion.alumno_id!=self.alumno_id):e["inscripcion"]="La inscripción no corresponde al alumno."
        if self.tarea_id and self.inscripcion_id and (self.inscripcion.ciclo_id!=self.tarea.ciclo_id or self.inscripcion.seccion_id!=self.tarea.seccion_id):e["inscripcion"]="La inscripción no corresponde a la tarea."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
class AdjuntoEntrega(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="adjuntos_entregas");entrega=models.ForeignKey(EntregaTarea,on_delete=models.CASCADE,related_name="adjuntos");archivo=models.FileField(upload_to=ruta_entrega,validators=[FileExtensionValidator(EXTENSIONES),validar_archivo_seguro]);nombre_original=models.CharField(max_length=255);fecha_creacion=models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.entrega_id and self.entrega.institucion_id!=self.institucion_id:raise ValidationError({"entrega":"La entrega no pertenece a la institución."})
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
