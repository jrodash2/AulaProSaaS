from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models, transaction
from django.db.models import Q

cui_validator = RegexValidator(r"^\d{13}$", "El CUI debe contener exactamente 13 dígitos.")


class Familia(models.Model):
    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="familias")
    codigo = models.CharField(max_length=20, null=True, blank=True)
    nombre_referencia = models.CharField(max_length=180)
    direccion = models.TextField(blank=True)
    telefono_principal = models.CharField(max_length=30, blank=True)
    email_principal = models.EmailField(blank=True)
    observaciones = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre_referencia",)
        constraints = [models.UniqueConstraint(fields=("institucion", "codigo"), condition=Q(codigo__isnull=False), name="familia_codigo_unico_institucion")]
        indexes = [models.Index(fields=("institucion", "activa"), name="familia_inst_activa_idx")]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.full_clean()
            super().save(*args, **kwargs)
            if not self.codigo:
                self.codigo = f"FAM-{self.pk:06d}"
                type(self).objects.filter(pk=self.pk).update(codigo=self.codigo)
        return self

    def __str__(self): return self.nombre_referencia


class Alumno(models.Model):
    class EstadoIdentificacion(models.TextChoices):
        VALIDADO = "VALIDADO", "Validado"
        PENDIENTE = "PENDIENTE", "Pendiente"
    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        INACTIVO = "INACTIVO", "Inactivo"
        RETIRADO = "RETIRADO", "Retirado"
        EGRESADO = "EGRESADO", "Egresado"
    class Sexo(models.TextChoices):
        FEMENINO = "F", "Femenino"
        MASCULINO = "M", "Masculino"
        OTRO = "O", "Otro / no especificado"

    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="alumnos")
    familia = models.ForeignKey(Familia, null=True, blank=True, on_delete=models.SET_NULL, related_name="alumnos")
    cui = models.CharField(max_length=13, null=True, blank=True, validators=[cui_validator])
    estado_identificacion = models.CharField(max_length=12, choices=EstadoIdentificacion.choices, default=EstadoIdentificacion.PENDIENTE)
    codigo_interno = models.CharField(max_length=40, blank=True)
    primer_nombre = models.CharField(max_length=60)
    segundo_nombre = models.CharField(max_length=60, blank=True)
    otros_nombres = models.CharField(max_length=100, blank=True)
    primer_apellido = models.CharField(max_length=60)
    segundo_apellido = models.CharField(max_length=60, blank=True)
    apellido_casada = models.CharField(max_length=60, blank=True)
    fecha_nacimiento = models.DateField()
    sexo = models.CharField(max_length=1, choices=Sexo.choices)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    departamento = models.CharField(max_length=80, blank=True)
    municipio = models.CharField(max_length=80, blank=True)
    fotografia = models.ImageField(upload_to="alumnos/fotografias/", blank=True, validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])])
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
    fecha_ingreso = models.DateField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("primer_apellido", "segundo_apellido", "primer_nombre")
        constraints = [models.UniqueConstraint(fields=("institucion", "cui"), condition=Q(cui__isnull=False), name="alumno_cui_unico_institucion")]
        indexes = [models.Index(fields=("institucion", "estado"), name="alumno_inst_estado_idx"), models.Index(fields=("institucion", "primer_apellido", "primer_nombre"), name="alumno_nombre_idx")]

    @property
    def nombre_completo(self):
        return " ".join(filter(None, [self.primer_nombre, self.segundo_nombre, self.otros_nombres, self.primer_apellido, self.segundo_apellido, self.apellido_casada]))

    def clean(self):
        errors = {}
        if self.cui:
            self.estado_identificacion = self.EstadoIdentificacion.VALIDADO
        elif self.estado_identificacion == self.EstadoIdentificacion.VALIDADO:
            errors["cui"] = "Un alumno validado debe tener CUI."
        if self.familia_id and self.familia.institucion_id != self.institucion_id:
            errors["familia"] = "La familia debe pertenecer a la institución."
        if errors: raise ValidationError(errors)

    def save(self, *args, **kwargs): self.full_clean(); return super().save(*args, **kwargs)
    def __str__(self): return self.nombre_completo


class Encargado(models.Model):
    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="encargados")
    cui = models.CharField(max_length=13, null=True, blank=True, validators=[cui_validator])
    nombres = models.CharField(max_length=160)
    apellidos = models.CharField(max_length=160)
    telefono = models.CharField(max_length=30)
    telefono_secundario = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    ocupacion = models.CharField(max_length=120, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("apellidos", "nombres")
        constraints = [models.UniqueConstraint(fields=("institucion", "cui"), condition=Q(cui__isnull=False), name="encargado_cui_unico_institucion")]
        indexes = [models.Index(fields=("institucion", "activo"), name="encargado_inst_activo_idx")]
    @property
    def nombre_completo(self): return f"{self.nombres} {self.apellidos}".strip()
    def save(self, *args, **kwargs): self.full_clean(); return super().save(*args, **kwargs)
    def __str__(self): return self.nombre_completo


class AlumnoEncargado(models.Model):
    class Parentesco(models.TextChoices):
        MADRE="MADRE","Madre"; PADRE="PADRE","Padre"; ABUELO="ABUELO","Abuelo"; ABUELA="ABUELA","Abuela"; TUTOR="TUTOR","Tutor"; HERMANO="HERMANO","Hermano"; HERMANA="HERMANA","Hermana"; OTRO="OTRO","Otro"
    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="vinculos_encargados")
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="vinculos_encargados")
    encargado = models.ForeignKey(Encargado, on_delete=models.CASCADE, related_name="vinculos_alumnos")
    parentesco = models.CharField(max_length=12, choices=Parentesco.choices)
    parentesco_otro = models.CharField(max_length=80, blank=True)
    es_principal = models.BooleanField(default=False)
    es_responsable_financiero = models.BooleanField(default=False)
    es_contacto_emergencia = models.BooleanField(default=False)
    autorizado_recoger = models.BooleanField(default=False)
    convive_con_alumno = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=("alumno","encargado"), name="alumno_encargado_unico")]
        indexes=[models.Index(fields=("institucion","activo"), name="vinculo_inst_activo_idx")]
    def clean(self):
        if self.alumno_id and self.encargado_id and (self.alumno.institucion_id != self.institucion_id or self.encargado.institucion_id != self.institucion_id): raise ValidationError("Alumno y encargado deben pertenecer a la institución.")
        if self.parentesco == self.Parentesco.OTRO and not self.parentesco_otro: raise ValidationError({"parentesco_otro":"Especifique el parentesco."})
    def save(self,*args,**kwargs): self.full_clean(); return super().save(*args,**kwargs)


class Inscripcion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR="BORRADOR","Borrador"; ACTIVA="ACTIVA","Activa"; RETIRADA="RETIRADA","Retirada"; TRASLADADA="TRASLADADA","Trasladada"; FINALIZADA="FINALIZADA","Finalizada"; ANULADA="ANULADA","Anulada"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="inscripciones")
    alumno=models.ForeignKey(Alumno,on_delete=models.PROTECT,related_name="inscripciones")
    ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="inscripciones")
    oferta_academica=models.ForeignKey("academico.OfertaAcademica",on_delete=models.PROTECT,related_name="inscripciones")
    grado=models.ForeignKey("academico.GradoInstitucion",on_delete=models.PROTECT,related_name="inscripciones")
    seccion=models.ForeignKey("academico.Seccion",on_delete=models.PROTECT,related_name="inscripciones")
    fecha_inscripcion=models.DateField()
    numero_inscripcion=models.CharField(max_length=40,blank=True)
    estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.ACTIVA)
    es_reingreso=models.BooleanField(default=False)
    observaciones=models.TextField(blank=True)
    fecha_retiro=models.DateField(null=True,blank=True)
    motivo_retiro=models.TextField(blank=True)
    fecha_creacion=models.DateTimeField(auto_now_add=True)
    fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("-ciclo__anio","alumno__primer_apellido")
        constraints=[models.UniqueConstraint(fields=("alumno","ciclo"),condition=Q(estado="ACTIVA"),name="inscripcion_activa_unica_ciclo")]
        indexes=[models.Index(fields=("institucion","ciclo","estado"),name="inscripcion_inst_ciclo_idx")]
    def clean(self):
        errors={}
        if self.alumno_id and self.alumno.institucion_id != self.institucion_id: errors["alumno"]="El alumno no pertenece a la institución."
        if self.ciclo_id and self.ciclo.institucion_id != self.institucion_id: errors["ciclo"]="El ciclo no pertenece a la institución."
        if self.oferta_academica_id and (self.oferta_academica.institucion_id != self.institucion_id or self.oferta_academica.ciclo_id != self.ciclo_id): errors["oferta_academica"]="La oferta no corresponde a la institución y ciclo."
        if self.grado_id and (self.grado.institucion_id != self.institucion_id or self.grado.ciclo_id != self.ciclo_id or self.grado.oferta_id != self.oferta_academica_id): errors["grado"]="El grado no corresponde a la oferta."
        if self.seccion_id and (self.seccion.institucion_id != self.institucion_id or self.seccion.ciclo_id != self.ciclo_id or self.seccion.grado_id != self.grado_id): errors["seccion"]="La sección no corresponde al grado."
        if self.estado == self.Estado.RETIRADA and (not self.fecha_retiro or not self.motivo_retiro): errors["motivo_retiro"]="Indique fecha y motivo del retiro."
        if errors: raise ValidationError(errors)
    def save(self,*args,**kwargs): self.full_clean(); return super().save(*args,**kwargs)


class ImportacionAlumnos(models.Model):
    class Estado(models.TextChoices): VALIDANDO="VALIDANDO","Validando"; LISTA="LISTA","Lista"; PROCESADA="PROCESADA","Procesada"; FALLIDA="FALLIDA","Fallida"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="importaciones_alumnos")
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="importaciones_alumnos")
    ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="importaciones_alumnos")
    archivo_original=models.FileField(upload_to="alumnos/importaciones/",blank=True)
    nombre_archivo=models.CharField(max_length=255)
    estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.VALIDANDO)
    total_filas=models.PositiveIntegerField(default=0); creados=models.PositiveIntegerField(default=0); actualizados=models.PositiveIntegerField(default=0); inscripciones_creadas=models.PositiveIntegerField(default=0); errores=models.PositiveIntegerField(default=0)
    detalle_errores=models.JSONField(default=list,blank=True)
    fecha_inicio=models.DateTimeField(auto_now_add=True); fecha_fin=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=("-fecha_inicio",); indexes=[models.Index(fields=("institucion","estado"),name="import_inst_estado_idx")]
    def clean(self):
        if self.ciclo_id and self.ciclo.institucion_id != self.institucion_id:
            raise ValidationError({"ciclo":"El ciclo de importación no pertenece a la institución."})
    def save(self,*args,**kwargs): self.full_clean(); return super().save(*args,**kwargs)
