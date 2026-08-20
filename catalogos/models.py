import uuid

from django.core.exceptions import ValidationError
from django.db import models


class ModeloCatalogoBase(models.Model):
    activo = models.BooleanField(default=True)

    class Meta:
        abstract = True


class NivelEducativo(ModeloCatalogoBase):
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=100)
    orden = models.PositiveSmallIntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("orden", "nombre")
        verbose_name = "nivel educativo"
        verbose_name_plural = "niveles educativos"

    def __str__(self):
        return self.nombre


class TipoCarrera(ModeloCatalogoBase):
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("orden", "nombre")
        verbose_name_plural = "tipos de carrera"

    def __str__(self):
        return self.nombre


class CarreraCatalogo(models.Model):
    class Modalidad(models.TextChoices):
        PRESENCIAL = "PRESENCIAL", "Presencial"
        SEMIPRESENCIAL = "SEMIPRESENCIAL", "Semipresencial"
        A_DISTANCIA = "A_DISTANCIA", "A distancia"
        MIXTA = "MIXTA", "Mixta"
        OTRA = "OTRA", "Otra"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    activa = models.BooleanField(default=True)
    codigo_interno = models.CharField(max_length=50, unique=True)
    codigo_mineduc = models.CharField(max_length=50, blank=True)
    nombre = models.CharField(max_length=220)
    nombre_corto = models.CharField(max_length=100, blank=True)
    nivel = models.ForeignKey(
        NivelEducativo,
        on_delete=models.PROTECT,
        related_name="carreras",
    )
    tipo_carrera = models.ForeignKey(
        TipoCarrera,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="carreras",
    )
    duracion_anios = models.PositiveSmallIntegerField()
    descripcion = models.TextField(blank=True)
    modalidad = models.CharField(
        max_length=20,
        choices=Modalidad.choices,
        default=Modalidad.PRESENCIAL,
    )
    jornada_referencia = models.CharField(max_length=100, blank=True)
    acuerdo_ministerial = models.CharField(max_length=120, blank=True)
    fecha_acuerdo = models.DateField(null=True, blank=True)
    fuente_oficial = models.CharField(max_length=220, blank=True)
    url_fuente = models.URLField(blank=True)
    en_revision = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre",)
        verbose_name = "carrera del catálogo"
        verbose_name_plural = "carreras del catálogo"

    def __str__(self):
        return self.nombre


class VersionPensum(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        VIGENTE = "VIGENTE", "Vigente"
        EN_REVISION = "EN_REVISION", "En revisión"
        HISTORICO = "HISTORICO", "Histórico"
        DEROGADO = "DEROGADO", "Derogado"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    carrera = models.ForeignKey(
        CarreraCatalogo,
        on_delete=models.PROTECT,
        related_name="versiones_pensum",
    )
    codigo_version = models.CharField(max_length=50)
    nombre = models.CharField(max_length=160)
    acuerdo_ministerial = models.CharField(max_length=120, blank=True)
    fecha_acuerdo = models.DateField(null=True, blank=True)
    fecha_inicio_vigencia = models.DateField()
    fecha_fin_vigencia = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.BORRADOR,
    )
    observaciones = models.TextField(blank=True)
    fuente_oficial = models.CharField(max_length=220, blank=True)
    url_fuente = models.URLField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-fecha_inicio_vigencia", "-fecha_creacion")
        constraints = [
            models.UniqueConstraint(
                fields=("carrera", "codigo_version"),
                name="version_pensum_codigo_unico_carrera",
            )
        ]
        verbose_name = "versión de pensum"
        verbose_name_plural = "versiones de pensum"

    def __str__(self):
        return f"{self.carrera} · {self.nombre}"

    def clean(self):
        super().clean()
        if (
            self.fecha_inicio_vigencia
            and self.fecha_fin_vigencia
            and self.fecha_fin_vigencia < self.fecha_inicio_vigencia
        ):
            raise ValidationError(
                {"fecha_fin_vigencia": "No puede ser anterior al inicio."}
            )


class GradoPensum(ModeloCatalogoBase):
    pensum = models.ForeignKey(
        VersionPensum,
        on_delete=models.PROTECT,
        related_name="grados",
    )
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=100)
    numero_orden = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("numero_orden", "nombre")
        constraints = [
            models.UniqueConstraint(
                fields=("pensum", "codigo"),
                name="grado_codigo_unico_pensum",
            )
        ]
        verbose_name = "grado de pensum"
        verbose_name_plural = "grados de pensum"

    def __str__(self):
        return f"{self.nombre} · {self.pensum.nombre}"


class AreaCurricular(ModeloCatalogoBase):
    codigo = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ("nombre",)
        verbose_name = "área curricular"
        verbose_name_plural = "áreas curriculares"

    def __str__(self):
        return self.nombre


class CursoCatalogo(ModeloCatalogoBase):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    codigo_interno = models.CharField(max_length=50, unique=True)
    codigo_mineduc = models.CharField(max_length=50, blank=True)
    nombre = models.CharField(max_length=180)
    nombre_corto = models.CharField(max_length=80, blank=True)
    area_curricular = models.ForeignKey(
        AreaCurricular,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="cursos",
    )
    descripcion = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre",)
        verbose_name = "curso del catálogo"
        verbose_name_plural = "cursos del catálogo"

    def __str__(self):
        return self.nombre


class CursoPensum(ModeloCatalogoBase):
    pensum = models.ForeignKey(
        VersionPensum,
        on_delete=models.PROTECT,
        related_name="cursos_pensum",
    )
    grado = models.ForeignKey(
        GradoPensum,
        on_delete=models.PROTECT,
        related_name="cursos_pensum",
    )
    curso = models.ForeignKey(
        CursoCatalogo,
        on_delete=models.PROTECT,
        related_name="apariciones_pensum",
    )
    orden = models.PositiveSmallIntegerField(default=0)
    periodos_semanales = models.PositiveSmallIntegerField(null=True, blank=True)
    obligatorio = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ("grado__numero_orden", "orden", "curso__nombre")
        constraints = [
            models.UniqueConstraint(
                fields=("pensum", "grado", "curso"),
                name="curso_unico_grado_pensum",
            )
        ]
        verbose_name = "curso de pensum"
        verbose_name_plural = "cursos de pensum"

    def __str__(self):
        return f"{self.curso} · {self.grado}"

    def clean(self):
        super().clean()
        if self.grado_id and self.pensum_id:
            grado_pensum_id = (
                self.grado.pensum_id
                if hasattr(self, "grado")
                else GradoPensum.objects.values_list("pensum_id", flat=True).get(
                    pk=self.grado_id
                )
            )
            if grado_pensum_id != self.pensum_id:
                raise ValidationError(
                    {"grado": "El grado debe pertenecer a la versión seleccionada."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
