from django.contrib import admin

from .models import Institucion, OnboardingInstitucion, UsuarioInstitucion

admin.site.register(OnboardingInstitucion)


@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "municipio", "activa", "fecha_creacion")
    list_filter = ("activa", "departamento")
    search_fields = ("nombre", "nombre_corto", "codigo")
    readonly_fields = ("uuid", "fecha_creacion", "fecha_actualizacion")


@admin.register(UsuarioInstitucion)
class UsuarioInstitucionAdmin(admin.ModelAdmin):
    list_display = ("usuario", "institucion", "rol", "activo", "fecha_asignacion")
    list_filter = ("rol", "activo", "institucion")
    autocomplete_fields = ("usuario", "institucion")
