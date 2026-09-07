from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Aula(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="aulas")
    codigo=models.CharField(max_length=40);nombre=models.CharField(max_length=120);capacidad=models.PositiveSmallIntegerField(null=True,blank=True);ubicacion=models.CharField(max_length=180,blank=True);descripcion=models.TextField(blank=True);activa=models.BooleanField(default=True)
    fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("codigo","nombre");constraints=[models.UniqueConstraint(fields=("institucion","codigo"),name="aula_codigo_unico_inst")]
    def save(self,*a,**kw):self.codigo=self.codigo.upper().strip();self.full_clean();return super().save(*a,**kw)
    def __str__(self):return f"{self.codigo} · {self.nombre}"


class BloqueHorario(models.Model):
    class Tipo(models.TextChoices):CLASE="CLASE","Clase";RECREO="RECREO","Recreo";ALMUERZO="ALMUERZO","Almuerzo";OTRO="OTRO","Otro"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="bloques_horario")
    jornada=models.ForeignKey("academico.JornadaInstitucion",on_delete=models.PROTECT,related_name="bloques_horario")
    nombre=models.CharField(max_length=100);orden=models.PositiveSmallIntegerField();hora_inicio=models.TimeField();hora_fin=models.TimeField();tipo=models.CharField(max_length=10,choices=Tipo.choices,default=Tipo.CLASE);activo=models.BooleanField(default=True)
    class Meta:
        ordering=("jornada__orden","orden");constraints=[models.UniqueConstraint(fields=("institucion","jornada","orden"),name="bloque_orden_unico_jornada")];indexes=[models.Index(fields=("institucion","jornada","activo"),name="bloque_inst_jornada_idx")]
    def clean(self):
        e={}
        if self.jornada_id and self.jornada.institucion_id!=self.institucion_id:e["jornada"]="La jornada no pertenece a la institución."
        if self.hora_inicio and self.hora_fin and self.hora_fin<=self.hora_inicio:e["hora_fin"]="Debe ser posterior a la hora inicial."
        if self.activo and self.jornada_id and self.hora_inicio and self.hora_fin:
            cruces=type(self).objects.filter(institucion_id=self.institucion_id,jornada_id=self.jornada_id,activo=True,hora_inicio__lt=self.hora_fin,hora_fin__gt=self.hora_inicio).exclude(pk=self.pk)
            if cruces.exists():e["hora_inicio"]="El bloque se traslapa con otro bloque activo de la jornada."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
    def __str__(self):return f"{self.nombre} · {self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}"


class HorarioClase(models.Model):
    class Dia(models.TextChoices):LUNES="LUNES","Lunes";MARTES="MARTES","Martes";MIERCOLES="MIERCOLES","Miércoles";JUEVES="JUEVES","Jueves";VIERNES="VIERNES","Viernes";SABADO="SABADO","Sábado";DOMINGO="DOMINGO","Domingo"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="horarios_clase")
    ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="horarios_clase")
    jornada=models.ForeignKey("academico.JornadaInstitucion",on_delete=models.PROTECT,related_name="horarios_clase")
    seccion=models.ForeignKey("academico.Seccion",on_delete=models.PROTECT,related_name="horarios_clase")
    asignacion_docente=models.ForeignKey("docentes.AsignacionDocente",on_delete=models.PROTECT,related_name="horarios_clase")
    bloque=models.ForeignKey(BloqueHorario,on_delete=models.PROTECT,related_name="horarios_clase")
    dia_semana=models.CharField(max_length=10,choices=Dia.choices);aula=models.ForeignKey(Aula,null=True,blank=True,on_delete=models.PROTECT,related_name="horarios_clase");activo=models.BooleanField(default=True);observaciones=models.TextField(blank=True)
    fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("dia_semana","bloque__orden");constraints=[models.UniqueConstraint(fields=("seccion","dia_semana","bloque"),condition=Q(activo=True),name="horario_seccion_bloque_activo")]
        indexes=[models.Index(fields=("institucion","ciclo"),name="horario_inst_ciclo_idx"),models.Index(fields=("seccion","dia_semana"),name="horario_seccion_dia_idx"),models.Index(fields=("asignacion_docente","dia_semana"),name="horario_asig_dia_idx"),models.Index(fields=("aula","dia_semana"),name="horario_aula_dia_idx")]
    @property
    def curso(self):return self.asignacion_docente.curso
    @property
    def docente(self):return self.asignacion_docente.docente
    @property
    def grado(self):return self.seccion.grado
    def clean(self):
        e={};a=self.asignacion_docente if self.asignacion_docente_id else None
        if self.ciclo_id and (self.ciclo.institucion_id!=self.institucion_id or self.ciclo.estado not in ("PLANIFICACION","ACTIVO")):e["ciclo"]="El ciclo no pertenece a la institución o no admite cambios de horario."
        if self.jornada_id and self.jornada.institucion_id!=self.institucion_id:e["jornada"]="La jornada no pertenece a la institución."
        if self.seccion_id and (self.seccion.institucion_id!=self.institucion_id or self.seccion.ciclo_id!=self.ciclo_id or self.seccion.jornada_id!=self.jornada_id):e["seccion"]="La sección no coincide con ciclo y jornada."
        if a and (a.institucion_id!=self.institucion_id or a.ciclo_id!=self.ciclo_id or a.seccion_id!=self.seccion_id):e["asignacion_docente"]="La asignación no corresponde a institución, ciclo y sección."
        if self.bloque_id and (self.bloque.institucion_id!=self.institucion_id or self.bloque.jornada_id!=self.jornada_id or self.bloque.tipo!=BloqueHorario.Tipo.CLASE):e["bloque"]="Seleccione un bloque de clase de la misma jornada."
        if self.aula_id and self.aula.institucion_id!=self.institucion_id:e["aula"]="El aula no pertenece a la institución."
        if not e and self.activo:
            from .services import detectar_conflictos
            conflictos=detectar_conflictos(self)
            if conflictos:e["dia_semana"]=conflictos
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
    def __str__(self):return f"{self.get_dia_semana_display()} · {self.bloque} · {self.curso}"
