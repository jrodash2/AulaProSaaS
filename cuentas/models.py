from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def save(self, *args, **kwargs):
        self.is_active = self.activo
        super().save(*args, **kwargs)
