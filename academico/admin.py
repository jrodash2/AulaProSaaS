from django.contrib import admin

from .models import CicloEscolar, CursoInstitucion, GradoInstitucion, JornadaInstitucion, OfertaAcademica, Seccion


@admin.register(CicloEscolar)
class CicloEscolarAdmin(admin.ModelAdmin):
    list_display = ("nombre", "institucion", "anio", "es_actual", "activo", "cerrado")
    list_filter = ("institucion", "activo", "es_actual", "cerrado")


@admin.register(JornadaInstitucion)
class JornadaInstitucionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "institucion", "codigo", "activa", "orden")
    list_filter = ("institucion", "activa")


@admin.register(OfertaAcademica)
class OfertaAcademicaAdmin(admin.ModelAdmin):
    list_display = ("nombre_mostrado", "institucion", "ciclo", "nivel", "origen", "activa")
    list_filter = ("institucion", "ciclo", "origen", "activa")


admin.site.register(GradoInstitucion)
admin.site.register(CursoInstitucion)
admin.site.register(Seccion)
