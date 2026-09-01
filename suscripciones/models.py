from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ModuloSaaS(models.Model):
    class Codigo(models.TextChoices):
        ACADEMICO = "ACADEMICO", "Académico"
        ALUMNOS = "ALUMNOS", "Alumnos"
        DOCENTES = "DOCENTES", "Docentes"
        ASISTENCIA = "ASISTENCIA", "Asistencia"
        CALIFICACIONES = "CALIFICACIONES", "Calificaciones"
        TAREAS = "TAREAS", "Tareas"
        FINANZAS = "FINANZAS", "Finanzas"
        PORTAL = "PORTAL", "Portal familiar"
        COMUNICACIONES = "COMUNICACIONES", "Comunicaciones"
        REPORTES = "REPORTES", "Reportes"
        EXPEDIENTE = "EXPEDIENTE", "Expediente digital"

    codigo = models.CharField(max_length=24, choices=Codigo.choices, unique=True)
    nombre = models.CharField(max_length=80)
    descripcion = models.CharField(max_length=240, blank=True)
    icono = models.CharField(max_length=40, blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("orden", "nombre")

    def __str__(self):
        return self.nombre


class Plan(models.Model):
    codigo = models.SlugField(max_length=30, unique=True)
    nombre = models.CharField(max_length=80)
    descripcion = models.TextField(blank=True)
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    precio_anual = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_alumnos = models.PositiveIntegerField(null=True, blank=True)
    max_usuarios = models.PositiveIntegerField(null=True, blank=True)
    max_docentes = models.PositiveIntegerField(null=True, blank=True)
    es_personalizado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    publico = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)
    modulos = models.ManyToManyField(ModuloSaaS, through="PlanModulo", related_name="planes")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("orden", "nombre")

    def clean(self):
        errors = {}
        if self.precio_mensual is not None and self.precio_mensual < 0:
            errors["precio_mensual"] = "El precio no puede ser negativo."
        if self.precio_anual is not None and self.precio_anual < 0:
            errors["precio_anual"] = "El precio no puede ser negativo."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.upper()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class PlanModulo(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="configuracion_modulos")
    modulo = models.ForeignKey(ModuloSaaS, on_delete=models.PROTECT, related_name="configuracion_planes")
    habilitado = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("plan", "modulo"), name="plan_modulo_unico")]


class Suscripcion(models.Model):
    class Estado(models.TextChoices):
        PRUEBA = "PRUEBA", "Prueba"
        ACTIVA = "ACTIVA", "Activa"
        VENCIDA = "VENCIDA", "Vencida"
        SUSPENDIDA = "SUSPENDIDA", "Suspendida"
        CANCELADA = "CANCELADA", "Cancelada"

    class Modalidad(models.TextChoices):
        MENSUAL = "MENSUAL", "Mensual"
        ANUAL = "ANUAL", "Anual"
        PERSONALIZADA = "PERSONALIZADA", "Personalizada"

    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.PROTECT, related_name="suscripciones")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="suscripciones")
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PRUEBA)
    modalidad = models.CharField(max_length=15, choices=Modalidad.choices, default=Modalidad.MENSUAL)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    periodo_prueba_hasta = models.DateField(null=True, blank=True)
    renovacion_automatica = models.BooleanField(default=False)
    max_alumnos_override = models.PositiveIntegerField(null=True, blank=True)
    max_usuarios_override = models.PositiveIntegerField(null=True, blank=True)
    precio_acordado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notas_internas = models.TextField(blank=True)
    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="suscripciones_creadas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-fecha_inicio", "-pk")
        constraints = [
            models.UniqueConstraint(
                fields=("institucion",),
                condition=Q(estado__in=("PRUEBA", "ACTIVA", "SUSPENDIDA")),
                name="suscripcion_actual_unica_institucion",
            ),
            models.CheckConstraint(condition=Q(fecha_fin__gte=models.F("fecha_inicio")), name="suscripcion_fechas_validas"),
        ]
        indexes = [models.Index(fields=("estado", "fecha_fin"), name="sus_estado_fin_idx")]

    @property
    def limite_alumnos(self):
        return self.max_alumnos_override if self.max_alumnos_override is not None else self.plan.max_alumnos

    @property
    def limite_usuarios(self):
        return self.max_usuarios_override if self.max_usuarios_override is not None else self.plan.max_usuarios

    @property
    def precio_mensual_equivalente(self):
        precio = self.precio_acordado
        if precio is None:
            precio = self.plan.precio_anual if self.modalidad == self.Modalidad.ANUAL else self.plan.precio_mensual
        if self.modalidad == self.Modalidad.ANUAL:
            return (precio or Decimal("0")) / Decimal("12")
        return precio or Decimal("0")

    def clean(self):
        errors = {}
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            errors["fecha_fin"] = "La fecha final debe ser igual o posterior al inicio."
        if self.estado == self.Estado.PRUEBA and not self.periodo_prueba_hasta:
            errors["periodo_prueba_hasta"] = "Indique cuándo finaliza el período de prueba."
        if self.periodo_prueba_hasta and self.fecha_fin and self.periodo_prueba_hasta > self.fecha_fin:
            errors["periodo_prueba_hasta"] = "El período de prueba no puede superar la fecha final."
        if self.precio_acordado is not None and self.precio_acordado < 0:
            errors["precio_acordado"] = "El precio no puede ser negativo."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.institucion} · {self.plan}"


class HistorialSuscripcion(models.Model):
    suscripcion = models.ForeignKey(Suscripcion, on_delete=models.PROTECT, related_name="historial")
    accion = models.CharField(max_length=40)
    estado_anterior = models.CharField(max_length=12, blank=True)
    estado_nuevo = models.CharField(max_length=12, blank=True)
    plan_anterior = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.PROTECT, related_name="historial_origen")
    plan_nuevo = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.PROTECT, related_name="historial_destino")
    detalles = models.JSONField(default=dict, blank=True)
    realizada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-fecha",)


class SolicitudCambioPlan(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        CANCELADA = "CANCELADA", "Cancelada"

    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.PROTECT, related_name="solicitudes_plan")
    plan_actual = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="solicitudes_desde")
    plan_solicitado = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="solicitudes_hacia")
    mensaje = models.TextField(blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    solicitada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="solicitudes_plan_creadas")
    atendida_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="solicitudes_plan_atendidas")
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_atencion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-fecha",)
        constraints = [
            models.UniqueConstraint(fields=("institucion",), condition=Q(estado="PENDIENTE"), name="solicitud_plan_pendiente_unica")
        ]
