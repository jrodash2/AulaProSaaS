from django.contrib import admin

from .models import EventoAuditoria


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "accion", "modelo", "objeto_id", "usuario", "institucion", "ip")
    list_filter = ("accion", "modelo", "institucion")
    search_fields = ("objeto_id", "usuario__username", "institucion__nombre")
    readonly_fields = ("usuario", "institucion", "accion", "modelo", "objeto_id", "fecha", "ip")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
