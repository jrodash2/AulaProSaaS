from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models, transaction
from django.db.models import Q

cui_validator = RegexValidator(r"^\d{13}$", "El CUI debe contener exactamente 13 dígitos.")


class Docente(models.Model):
    class Estado(models.TextChoices):
        ACTIVO="ACTIVO","Activo"; INACTIVO="INACTIVO","Inactivo"; SUSPENDIDO="SUSPENDIDO","Suspendido"; RETIRADO="RETIRADO","Retirado"
    class Sexo(models.TextChoices):
        FEMENINO="F","Femenino"; MASCULINO="M","Masculino"; OTRO="O","Otro / no especificado"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="docentes")
    usuario=models.OneToOneField(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="expediente_docente")
    codigo=models.CharField(max_length=20,null=True,blank=True)
    cui=models.CharField(max_length=13,null=True,blank=True,validators=[cui_validator])
    primer_nombre=models.CharField(max_length=60); segundo_nombre=models.CharField(max_length=60,blank=True); otros_nombres=models.CharField(max_length=100,blank=True)
    primer_apellido=models.CharField(max_length=60); segundo_apellido=models.CharField(max_length=60,blank=True)
    fecha_nacimiento=models.DateField(null=True,blank=True); sexo=models.CharField(max_length=1,choices=Sexo.choices,blank=True)
    telefono=models.CharField(max_length=30); email=models.EmailField(blank=True); direccion=models.TextField(blank=True)
    titulo_profesional=models.CharField(max_length=180,blank=True); especialidad=models.CharField(max_length=160,blank=True)
    fotografia=models.ImageField(upload_to="docentes/fotografias/",blank=True,validators=[FileExtensionValidator(["jpg","jpeg","png","webp"])])
    fecha_ingreso=models.DateField(); estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.ACTIVO); observaciones=models.TextField(blank=True)
    fecha_creacion=models.DateTimeField(auto_now_add=True); fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("primer_apellido","segundo_apellido","primer_nombre")
        constraints=[models.UniqueConstraint(fields=("institucion","codigo"),condition=Q(codigo__isnull=False),name="docente_codigo_unico_inst"),models.UniqueConstraint(fields=("institucion","cui"),condition=Q(cui__isnull=False),name="docente_cui_unico_inst")]
        indexes=[models.Index(fields=("institucion","estado"),name="docente_inst_estado_idx"),models.Index(fields=("institucion","primer_apellido","primer_nombre"),name="docente_nombre_idx")]
    @property
    def nombre_completo(self): return " ".join(filter(None,[self.primer_nombre,self.segundo_nombre,self.otros_nombres,self.primer_apellido,self.segundo_apellido]))
    def clean(self):
        if self.usuario_id and not self.usuario.asignaciones_institucion.filter(institucion_id=self.institucion_id,activo=True).exists(): raise ValidationError({"usuario":"El usuario no pertenece a esta institución."})
    def save(self,*args,**kwargs):
        with transaction.atomic():
            self.full_clean(); super().save(*args,**kwargs)
            if not self.codigo:
                self.codigo=f"DOC-{self.pk:06d}"; type(self).objects.filter(pk=self.pk).update(codigo=self.codigo)
        return self
    def __str__(self): return self.nombre_completo


class AsignacionDocente(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="asignaciones_docentes")
    ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="asignaciones_docentes")
    docente=models.ForeignKey(Docente,on_delete=models.PROTECT,related_name="asignaciones")
    oferta_academica=models.ForeignKey("academico.OfertaAcademica",on_delete=models.PROTECT,related_name="asignaciones_docentes")
    grado=models.ForeignKey("academico.GradoInstitucion",on_delete=models.PROTECT,related_name="asignaciones_docentes")
    seccion=models.ForeignKey("academico.Seccion",on_delete=models.PROTECT,related_name="asignaciones_docentes")
    curso=models.ForeignKey("academico.CursoInstitucion",on_delete=models.PROTECT,related_name="asignaciones_docentes")
    fecha_inicio=models.DateField(); fecha_fin=models.DateField(null=True,blank=True); activa=models.BooleanField(default=True); es_titular=models.BooleanField(default=True); observaciones=models.TextField(blank=True)
    fecha_creacion=models.DateTimeField(auto_now_add=True); fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("ciclo__anio","seccion__nombre","curso__orden")
        constraints=[models.UniqueConstraint(fields=("docente","ciclo","seccion","curso"),condition=Q(activa=True),name="asignacion_docente_activa_unica"),models.UniqueConstraint(fields=("ciclo","seccion","curso"),condition=Q(es_titular=True,activa=True),name="titular_unico_curso_seccion")]
        indexes=[models.Index(fields=("institucion","ciclo","activa"),name="asig_doc_inst_ciclo_idx")]
    def clean(self):
        errors={}
        same=(("docente",self.docente_id),("ciclo",self.ciclo_id),("oferta_academica",self.oferta_academica_id),("grado",self.grado_id),("seccion",self.seccion_id),("curso",self.curso_id))
        for field,ident in same:
            if ident and getattr(self,field).institucion_id!=self.institucion_id: errors[field]="Debe pertenecer a la institución."
        if self.grado_id and self.grado.oferta_id!=self.oferta_academica_id: errors["grado"]="El grado no pertenece a la oferta."
        if self.seccion_id and self.seccion.grado_id!=self.grado_id: errors["seccion"]="La sección no pertenece al grado."
        if self.curso_id and (self.curso.grado_id!=self.grado_id or self.curso.oferta_id!=self.oferta_academica_id or self.curso.ciclo_id!=self.ciclo_id): errors["curso"]="El curso no corresponde a la estructura seleccionada."
        if self.fecha_fin and self.fecha_inicio and self.fecha_fin<self.fecha_inicio: errors["fecha_fin"]="Debe ser igual o posterior al inicio."
        if errors: raise ValidationError(errors)
    def save(self,*args,**kwargs): self.full_clean(); return super().save(*args,**kwargs)


class AsignacionGuia(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="asignaciones_guia")
    ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="asignaciones_guia")
    seccion=models.ForeignKey("academico.Seccion",on_delete=models.PROTECT,related_name="asignaciones_guia")
    docente=models.ForeignKey(Docente,on_delete=models.PROTECT,related_name="secciones_guia")
    fecha_inicio=models.DateField(); fecha_fin=models.DateField(null=True,blank=True); activa=models.BooleanField(default=True)
    fecha_creacion=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=("-ciclo__anio","seccion__nombre")
        constraints=[models.UniqueConstraint(fields=("ciclo","seccion"),condition=Q(activa=True),name="guia_activo_unico_seccion")]
        indexes=[models.Index(fields=("institucion","ciclo","activa"),name="guia_inst_ciclo_idx")]
    def clean(self):
        errors={}
        if self.ciclo_id and self.ciclo.institucion_id!=self.institucion_id: errors["ciclo"]="El ciclo no pertenece a la institución."
        if self.seccion_id and (self.seccion.institucion_id!=self.institucion_id or self.seccion.ciclo_id!=self.ciclo_id): errors["seccion"]="La sección no corresponde al ciclo."
        if self.docente_id and self.docente.institucion_id!=self.institucion_id: errors["docente"]="El docente no pertenece a la institución."
        if self.fecha_fin and self.fecha_fin<self.fecha_inicio: errors["fecha_fin"]="Debe ser posterior al inicio."
        if errors: raise ValidationError(errors)
    def save(self,*args,**kwargs): self.full_clean(); return super().save(*args,**kwargs)
