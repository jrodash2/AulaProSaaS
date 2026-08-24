from django.conf import settings
from django.db import models


class EventoAuditoria(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="eventos_auditoria")
    institucion = models.ForeignKey("instituciones.Institucion", null=True, blank=True, on_delete=models.SET_NULL, related_name="eventos_auditoria")
    accion = models.CharField(max_length=40)
    modelo = models.CharField(max_length=120)
    objeto_id = models.CharField(max_length=64, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    detalles = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-fecha",)
        verbose_name = "evento de auditoría"
        verbose_name_plural = "eventos de auditoría"

    def __str__(self):
        return f"{self.accion} · {self.modelo} · {self.fecha:%Y-%m-%d %H:%M}"
