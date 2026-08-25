import uuid

from django.conf import settings
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models, transaction


color_validator = RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Use un color hexadecimal, por ejemplo #1F4E5F.")


class Institucion(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nombre = models.CharField(max_length=180)
    nombre_corto = models.CharField(max_length=80, blank=True)
    codigo = models.CharField(max_length=40, unique=True)
    razon_social = models.CharField(max_length=180, blank=True)
    direccion = models.TextField(blank=True)
    departamento = models.CharField(max_length=80, blank=True)
    municipio = models.CharField(max_length=80, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    sitio_web = models.URLField(blank=True)
    logo_principal = models.ImageField(upload_to="instituciones/logos/", blank=True, validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])] )
    logo_secundario = models.ImageField(upload_to="instituciones/logos/", blank=True, validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])] )
    color_primario = models.CharField(max_length=7, default="#1F4E5F", validators=[color_validator])
    color_secundario = models.CharField(max_length=7, default="#3B8C88", validators=[color_validator])
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre


class UsuarioInstitucion(models.Model):
    class Rol(models.TextChoices):
        PROPIETARIO = "PROPIETARIO", "Propietario"
        DIRECTOR = "DIRECTOR", "Director"
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
        SECRETARIA = "SECRETARIA", "Secretaría"
        CONTABILIDAD = "CONTABILIDAD", "Contabilidad"
        DOCENTE = "DOCENTE", "Docente"
        PADRE = "PADRE", "Padre / encargado"
        ALUMNO = "ALUMNO", "Alumno"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asignaciones_institucion")
    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE, related_name="asignaciones_usuario")
    rol = models.CharField(max_length=20, choices=Rol.choices)
    activo = models.BooleanField(default=True)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("usuario", "institucion"), name="usuario_institucion_unica")]
        verbose_name = "asignación usuario-institución"
        verbose_name_plural = "asignaciones usuario-institución"

    def __str__(self):
        return f"{self.usuario} · {self.institucion}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            Institucion.objects.select_for_update().get(pk=self.institucion_id)
            consume = self.activo and self.rol not in (self.Rol.PADRE, self.Rol.ALUMNO)
            antes_consume = False
            if self.pk:
                anterior = type(self).objects.filter(pk=self.pk).values("activo", "rol").first()
                antes_consume = bool(anterior and anterior["activo"] and anterior["rol"] not in (self.Rol.PADRE, self.Rol.ALUMNO))
            if consume and not antes_consume:
                from suscripciones.services import validar_cupo_usuarios
                validar_cupo_usuarios(self.institucion, 1)
            return super().save(*args, **kwargs)
