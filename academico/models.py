from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q


class CicloEscolar(models.Model):
    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="ciclos_escolares")
    nombre = models.CharField(max_length=120)
    anio = models.PositiveSmallIntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)
    es_actual = models.BooleanField(default=False)
    cerrado = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-anio", "nombre")
        constraints = [
            models.UniqueConstraint(fields=("institucion", "anio"), name="ciclo_anio_unico_institucion"),
            models.UniqueConstraint(fields=("institucion",), condition=Q(es_actual=True), name="un_ciclo_actual_institucion"),
        ]
        indexes = [models.Index(fields=("institucion", "activo"), name="ciclo_inst_activo_idx")]

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin <= self.fecha_inicio:
            raise ValidationError({"fecha_fin": "La fecha final debe ser posterior a la fecha inicial."})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.es_actual and self.institucion_id:
                from instituciones.models import Institucion
                Institucion.objects.select_for_update().get(pk=self.institucion_id)
                type(self).objects.filter(institucion_id=self.institucion_id, es_actual=True).exclude(pk=self.pk).update(es_actual=False)
            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class JornadaInstitucion(models.Model):
    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="jornadas")
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=100)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("orden", "nombre")
        constraints = [models.UniqueConstraint(fields=("institucion", "codigo"), name="jornada_codigo_unico_institucion")]
        indexes = [models.Index(fields=("institucion", "activa"), name="jornada_inst_activa_idx")]

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora final debe ser posterior a la inicial."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class OfertaAcademica(models.Model):
    class Origen(models.TextChoices):
        CATALOGO = "CATALOGO", "Catálogo"
        PERSONALIZADA = "PERSONALIZADA", "Personalizada"

    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="ofertas_academicas")
    ciclo = models.ForeignKey(CicloEscolar, on_delete=models.PROTECT, related_name="ofertas")
    nivel = models.ForeignKey("catalogos.NivelEducativo", on_delete=models.PROTECT, related_name="ofertas_institucionales")
    carrera_catalogo = models.ForeignKey("catalogos.CarreraCatalogo", null=True, blank=True, on_delete=models.PROTECT, related_name="ofertas_institucionales")
    version_pensum = models.ForeignKey("catalogos.VersionPensum", null=True, blank=True, on_delete=models.PROTECT, related_name="ofertas_institucionales")
    nombre_mostrado = models.CharField(max_length=220)
    codigo_interno = models.CharField(max_length=50)
    origen = models.CharField(max_length=20, choices=Origen.choices, default=Origen.CATALOGO)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nivel__orden", "nombre_mostrado")
        constraints = [
            models.UniqueConstraint(fields=("institucion", "ciclo", "codigo_interno"), name="oferta_codigo_unico_ciclo"),
            models.UniqueConstraint(fields=("institucion", "ciclo", "carrera_catalogo", "version_pensum"), condition=Q(version_pensum__isnull=False), name="oferta_pensum_unico_institucion"),
        ]
        indexes = [models.Index(fields=("institucion", "ciclo", "activa"), name="oferta_inst_ciclo_idx")]

    def clean(self):
        errors = {}
        if self.ciclo_id and self.institucion_id and self.ciclo.institucion_id != self.institucion_id:
            errors["ciclo"] = "El ciclo debe pertenecer a la institución."
        if self.version_pensum_id:
            if not self.carrera_catalogo_id or self.version_pensum.carrera_id != self.carrera_catalogo_id:
                errors["version_pensum"] = "El pensum debe pertenecer a la carrera seleccionada."
        if self.carrera_catalogo_id and self.nivel_id and self.carrera_catalogo.nivel_id != self.nivel_id:
            errors["carrera_catalogo"] = "La carrera debe pertenecer al nivel seleccionado."
        if self.origen == self.Origen.CATALOGO and self.carrera_catalogo_id and not self.version_pensum_id:
            errors["version_pensum"] = "Seleccione una versión de pensum."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre_mostrado


class GradoInstitucion(models.Model):
    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="grados_institucionales")
    ciclo = models.ForeignKey(CicloEscolar, on_delete=models.PROTECT, related_name="grados")
    oferta = models.ForeignKey(OfertaAcademica, on_delete=models.CASCADE, related_name="grados")
    grado_pensum_origen = models.ForeignKey("catalogos.GradoPensum", null=True, blank=True, on_delete=models.PROTECT, related_name="grados_institucionales")
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=100)
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("orden", "nombre")
        constraints = [models.UniqueConstraint(fields=("oferta", "codigo"), name="grado_codigo_unico_oferta")]
        indexes = [models.Index(fields=("institucion", "ciclo", "activo"), name="grado_inst_ciclo_idx")]

    def clean(self):
        if self.oferta_id and (self.oferta.institucion_id != self.institucion_id or self.oferta.ciclo_id != self.ciclo_id):
            raise ValidationError({"oferta": "La oferta debe pertenecer a la misma institución y ciclo."})
        if self.grado_pensum_origen_id and self.oferta.version_pensum_id != self.grado_pensum_origen.pensum_id:
            raise ValidationError({"grado_pensum_origen": "El grado de origen no pertenece al pensum de la oferta."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class CursoInstitucion(models.Model):
    class Origen(models.TextChoices):
        OFICIAL = "OFICIAL", "Oficial"
        INSTITUCIONAL = "INSTITUCIONAL", "Institucional"

    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="cursos_institucionales")
    ciclo = models.ForeignKey(CicloEscolar, on_delete=models.PROTECT, related_name="cursos")
    oferta = models.ForeignKey(OfertaAcademica, on_delete=models.CASCADE, related_name="cursos")
    grado = models.ForeignKey(GradoInstitucion, on_delete=models.CASCADE, related_name="cursos")
    curso_catalogo = models.ForeignKey("catalogos.CursoCatalogo", null=True, blank=True, on_delete=models.PROTECT, related_name="cursos_institucionales")
    curso_pensum_origen = models.ForeignKey("catalogos.CursoPensum", null=True, blank=True, on_delete=models.PROTECT, related_name="cursos_institucionales")
    nombre_mostrado = models.CharField(max_length=180, blank=True)
    nombre_personalizado = models.CharField(max_length=180, blank=True)
    periodos_semanales = models.PositiveSmallIntegerField(null=True, blank=True)
    obligatorio = models.BooleanField(default=True)
    origen = models.CharField(max_length=20, choices=Origen.choices)
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("grado__orden", "orden", "nombre_mostrado")
        constraints = [
            models.UniqueConstraint(fields=("grado", "curso_catalogo"), condition=Q(curso_catalogo__isnull=False), name="curso_catalogo_unico_grado_inst"),
            models.CheckConstraint(condition=Q(origen="OFICIAL", curso_catalogo__isnull=False) | Q(origen="INSTITUCIONAL", nombre_personalizado__gt=""), name="curso_inst_origen_valido"),
        ]
        indexes = [models.Index(fields=("institucion", "ciclo", "activo"), name="curso_inst_ciclo_idx")]

    @property
    def nombre(self):
        return self.nombre_mostrado or (self.curso_catalogo.nombre if self.curso_catalogo_id else self.nombre_personalizado)

    def clean(self):
        errors = {}
        if self.grado_id and (self.grado.institucion_id != self.institucion_id or self.grado.ciclo_id != self.ciclo_id or self.grado.oferta_id != self.oferta_id):
            errors["grado"] = "El grado debe pertenecer a la misma institución, ciclo y oferta."
        if self.origen == self.Origen.OFICIAL and not self.curso_catalogo_id:
            errors["curso_catalogo"] = "Un curso oficial exige referencia al catálogo."
        if self.origen == self.Origen.INSTITUCIONAL and not self.nombre_personalizado.strip():
            errors["nombre_personalizado"] = "Ingrese el nombre del curso institucional."
        if self.curso_pensum_origen_id and self.curso_pensum_origen.curso_id != self.curso_catalogo_id:
            errors["curso_pensum_origen"] = "El curso de origen no coincide con el catálogo."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Seccion(models.Model):
    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="secciones")
    ciclo = models.ForeignKey(CicloEscolar, on_delete=models.PROTECT, related_name="secciones")
    grado = models.ForeignKey(GradoInstitucion, on_delete=models.CASCADE, related_name="secciones")
    jornada = models.ForeignKey(JornadaInstitucion, null=True, blank=True, on_delete=models.PROTECT, related_name="secciones")
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=80)
    capacidad = models.PositiveSmallIntegerField(null=True, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ("grado__orden", "jornada__orden", "nombre")
        constraints = [
            models.UniqueConstraint(fields=("grado", "jornada", "nombre"), condition=Q(jornada__isnull=False), name="seccion_unica_grado_jornada"),
            models.UniqueConstraint(fields=("grado", "nombre"), condition=Q(jornada__isnull=True), name="seccion_unica_grado_sin_jornada"),
        ]
        indexes = [models.Index(fields=("institucion", "ciclo", "activa"), name="seccion_inst_ciclo_idx")]

    def clean(self):
        errors = {}
        if self.grado_id and (self.grado.institucion_id != self.institucion_id or self.grado.ciclo_id != self.ciclo_id):
            errors["grado"] = "El grado debe pertenecer a la misma institución y ciclo."
        if self.jornada_id and self.jornada.institucion_id != self.institucion_id:
            errors["jornada"] = "La jornada debe pertenecer a la institución."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.grado} · {self.nombre}"
