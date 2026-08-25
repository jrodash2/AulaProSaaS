from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

class ConfiguracionCalificaciones(models.Model):
    institucion=models.OneToOneField("instituciones.Institucion",on_delete=models.CASCADE,related_name="configuracion_calificaciones")
    nota_minima_aprobacion=models.DecimalField(max_digits=5,decimal_places=2,default=Decimal("60.00"))
    decimales=models.PositiveSmallIntegerField(default=2)
    mostrar_promedio_acumulado=models.BooleanField(default=False)
    permitir_docente_editar_cerrado=models.BooleanField(default=False)
    fecha_actualizacion=models.DateTimeField(auto_now=True)
    def clean(self):
        if not Decimal("0")<=self.nota_minima_aprobacion<=Decimal("100"): raise ValidationError({"nota_minima_aprobacion":"Debe estar entre 0 y 100."})
    def save(self,*a,**kw): self.full_clean(); return super().save(*a,**kw)

class PeriodoAcademico(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="periodos_academicos")
    ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="periodos_academicos")
    nombre=models.CharField(max_length=120); codigo=models.CharField(max_length=30); numero_orden=models.PositiveSmallIntegerField()
    fecha_inicio=models.DateField(); fecha_fin=models.DateField(); activo=models.BooleanField(default=True); cerrado=models.BooleanField(default=False)
    fecha_cierre=models.DateTimeField(null=True,blank=True); cerrado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="periodos_cerrados")
    motivo_reapertura=models.TextField(blank=True); reabierto_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="periodos_reabiertos")
    fecha_creacion=models.DateTimeField(auto_now_add=True); fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("ciclo__anio","numero_orden")
        constraints=[models.UniqueConstraint(fields=("institucion","ciclo","codigo"),name="periodo_codigo_unico_ciclo"),models.UniqueConstraint(fields=("institucion","ciclo","numero_orden"),name="periodo_orden_unico_ciclo")]
        indexes=[models.Index(fields=("institucion","ciclo"),name="periodo_inst_ciclo_idx")]
    def clean(self):
        e={}
        if self.ciclo_id and self.ciclo.institucion_id!=self.institucion_id:e["ciclo"]="El ciclo no pertenece a la institución."
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin<self.fecha_inicio:e["fecha_fin"]="Debe ser igual o posterior al inicio."
        if self.ciclo_id and self.fecha_inicio and self.fecha_fin and (self.fecha_inicio<self.ciclo.fecha_inicio or self.fecha_fin>self.ciclo.fecha_fin):e["fecha_inicio"]="El período debe estar dentro del ciclo."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
    def __str__(self):return self.nombre

class TipoEvaluacion(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="tipos_evaluacion")
    nombre=models.CharField(max_length=100);codigo=models.CharField(max_length=30);descripcion=models.TextField(blank=True);activo=models.BooleanField(default=True);orden=models.PositiveSmallIntegerField(default=0)
    class Meta:
        ordering=("orden","nombre");constraints=[models.UniqueConstraint(fields=("institucion","codigo"),name="tipo_eval_codigo_unico_inst")]
    def __str__(self):return self.nombre

class ActividadEvaluacion(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="actividades_evaluacion")
    ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="actividades_evaluacion")
    periodo=models.ForeignKey(PeriodoAcademico,on_delete=models.PROTECT,related_name="actividades")
    asignacion_docente=models.ForeignKey("docentes.AsignacionDocente",on_delete=models.PROTECT,related_name="actividades_evaluacion")
    curso=models.ForeignKey("academico.CursoInstitucion",on_delete=models.PROTECT,related_name="actividades_evaluacion")
    grado=models.ForeignKey("academico.GradoInstitucion",on_delete=models.PROTECT,related_name="actividades_evaluacion")
    seccion=models.ForeignKey("academico.Seccion",on_delete=models.PROTECT,related_name="actividades_evaluacion")
    tipo_evaluacion=models.ForeignKey(TipoEvaluacion,on_delete=models.PROTECT,related_name="actividades")
    nombre=models.CharField(max_length=160);descripcion=models.TextField(blank=True);fecha=models.DateField();fecha_entrega=models.DateField(null=True,blank=True)
    punteo_maximo=models.DecimalField(max_digits=7,decimal_places=2);ponderacion=models.DecimalField(max_digits=5,decimal_places=2)
    es_recuperacion=models.BooleanField(default=False);activa=models.BooleanField(default=True);creada_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="actividades_evaluacion_creadas")
    fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("periodo__numero_orden","fecha","nombre");indexes=[models.Index(fields=("institucion","periodo"),name="actividad_inst_periodo_idx"),models.Index(fields=("seccion","periodo"),name="actividad_secc_periodo_idx"),models.Index(fields=("curso","periodo"),name="actividad_curso_periodo_idx")]
    def clean(self):
        e={};a=self.asignacion_docente if self.asignacion_docente_id else None
        for f in ("ciclo","periodo","curso","grado","seccion","tipo_evaluacion","asignacion_docente"):
            o=getattr(self,f,None)
            if o and o.institucion_id!=self.institucion_id:e[f]="Debe pertenecer a la institución."
        if a and (a.ciclo_id!=self.ciclo_id or a.curso_id!=self.curso_id or a.grado_id!=self.grado_id or a.seccion_id!=self.seccion_id):e["asignacion_docente"]="La asignación no coincide con curso, grado y sección."
        if self.periodo_id and self.periodo.ciclo_id!=self.ciclo_id:e["periodo"]="El período no corresponde al ciclo."
        if self.periodo_id and self.periodo.cerrado:e["periodo"]="El período está cerrado."
        if self.punteo_maximo is not None and self.punteo_maximo<=0:e["punteo_maximo"]="Debe ser mayor que cero."
        if self.ponderacion is not None and not Decimal("0")<self.ponderacion<=Decimal("100"):e["ponderacion"]="Debe estar entre 0 y 100."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
    def __str__(self):return self.nombre

class Calificacion(models.Model):
    class Estado(models.TextChoices):PENDIENTE="PENDIENTE","Pendiente";CALIFICADO="CALIFICADO","Calificado";AUSENTE="AUSENTE","Ausente";EXENTO="EXENTO","Exento"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="calificaciones")
    actividad=models.ForeignKey(ActividadEvaluacion,on_delete=models.PROTECT,related_name="calificaciones")
    alumno=models.ForeignKey("alumnos.Alumno",on_delete=models.PROTECT,related_name="calificaciones")
    inscripcion=models.ForeignKey("alumnos.Inscripcion",on_delete=models.PROTECT,related_name="calificaciones")
    estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.PENDIENTE);punteo_obtenido=models.DecimalField(max_digits=7,decimal_places=2,null=True,blank=True);observacion=models.TextField(blank=True)
    registrado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="calificaciones_registradas");fecha_registro=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=("actividad","alumno"),name="calificacion_unica_actividad_alumno")];indexes=[models.Index(fields=("actividad","alumno"),name="calif_actividad_alumno_idx")]
    def clean(self):
        e={}
        if self.actividad_id and self.actividad.institucion_id!=self.institucion_id:e["actividad"]="La actividad no pertenece a la institución."
        if self.alumno_id and self.alumno.institucion_id!=self.institucion_id:e["alumno"]="El alumno no pertenece a la institución."
        if self.inscripcion_id:
            i=self.inscripcion
            if i.institucion_id!=self.institucion_id or i.alumno_id!=self.alumno_id:e["inscripcion"]="La inscripción no corresponde al alumno."
            elif self.actividad_id and (i.ciclo_id!=self.actividad.ciclo_id or i.grado_id!=self.actividad.grado_id or i.seccion_id!=self.actividad.seccion_id):e["inscripcion"]="La inscripción no corresponde a la actividad."
        if self.estado==self.Estado.CALIFICADO:
            if self.punteo_obtenido is None:e["punteo_obtenido"]="Ingrese el punteo."
            elif self.punteo_obtenido<0 or self.punteo_obtenido>self.actividad.punteo_maximo:e["punteo_obtenido"]="Debe estar entre cero y el punteo máximo."
        elif self.punteo_obtenido is not None:e["punteo_obtenido"]="Solo una nota calificada puede tener punteo."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
    @property
    def aporte(self):
        return self.punteo_obtenido/self.actividad.punteo_maximo*self.actividad.ponderacion if self.estado==self.Estado.CALIFICADO else None
