from django.contrib import admin

from .models import (
    AreaCurricular,
    CarreraCatalogo,
    CursoCatalogo,
    CursoPensum,
    GradoPensum,
    NivelEducativo,
    TipoCarrera,
    VersionPensum,
)


@admin.register(NivelEducativo)
class NivelEducativoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "orden", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
    ordering = ("orden", "nombre")


@admin.register(TipoCarrera)
class TipoCarreraAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "orden", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(CarreraCatalogo)
class CarreraCatalogoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_interno",
        "nombre",
        "nivel",
        "tipo_carrera",
        "duracion_anios",
        "activa",
        "en_revision",
    )
    list_filter = ("nivel", "tipo_carrera", "modalidad", "activa", "en_revision")
    search_fields = (
        "codigo_interno",
        "codigo_mineduc",
        "nombre",
        "acuerdo_ministerial",
    )
    autocomplete_fields = ("nivel", "tipo_carrera")
    readonly_fields = ("uuid", "fecha_creacion", "fecha_actualizacion")


class GradoPensumInline(admin.TabularInline):
    model = GradoPensum
    extra = 0


@admin.register(VersionPensum)
class VersionPensumAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_version",
        "nombre",
        "carrera",
        "estado",
        "fecha_inicio_vigencia",
    )
    list_filter = ("estado", "carrera__nivel")
    search_fields = ("codigo_version", "nombre", "carrera__nombre")
    autocomplete_fields = ("carrera",)
    readonly_fields = ("uuid", "fecha_creacion", "fecha_actualizacion")
    inlines = (GradoPensumInline,)


@admin.register(GradoPensum)
class GradoPensumAdmin(admin.ModelAdmin):
    list_display = ("nombre", "pensum", "numero_orden", "activo")
    list_filter = ("activo", "pensum__estado")
    search_fields = ("codigo", "nombre", "pensum__nombre")
    autocomplete_fields = ("pensum",)


@admin.register(AreaCurricular)
class AreaCurricularAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(CursoCatalogo)
class CursoCatalogoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_interno",
        "nombre",
        "area_curricular",
        "activo",
    )
    list_filter = ("activo", "area_curricular")
    search_fields = ("codigo_interno", "codigo_mineduc", "nombre")
    autocomplete_fields = ("area_curricular",)
    readonly_fields = ("uuid", "fecha_creacion", "fecha_actualizacion")


@admin.register(CursoPensum)
class CursoPensumAdmin(admin.ModelAdmin):
    list_display = (
        "curso",
        "pensum",
        "grado",
        "orden",
        "periodos_semanales",
        "obligatorio",
        "activo",
    )
    list_filter = ("obligatorio", "activo", "pensum__estado")
    search_fields = ("curso__nombre", "pensum__nombre", "grado__nombre")
    autocomplete_fields = ("pensum", "grado", "curso")
