from django.core.exceptions import ValidationError
from django.db import transaction

from .models import CicloEscolar, CursoInstitucion, GradoInstitucion, OfertaAcademica


@transaction.atomic
def establecer_ciclo_actual(ciclo):
    ciclo = CicloEscolar.objects.select_for_update().get(pk=ciclo.pk, institucion=ciclo.institucion)
    CicloEscolar.objects.filter(institucion=ciclo.institucion, es_actual=True).exclude(pk=ciclo.pk).update(es_actual=False)
    ciclo.es_actual = True
    ciclo.save(update_fields=("es_actual", "fecha_actualizacion"))
    return ciclo


@transaction.atomic
def crear_oferta_desde_pensum(*, institucion, ciclo, nivel, carrera, pensum, nombre_mostrado=None, codigo_interno=None):
    if ciclo.institucion_id != institucion.pk:
        raise ValidationError("El ciclo no pertenece a la institución.")
    if ciclo.cerrado:
        raise ValidationError("Un ciclo cerrado no admite cambios académicos.")
    if pensum.carrera_id != carrera.pk:
        raise ValidationError("El pensum no pertenece a la carrera seleccionada.")
    if carrera.nivel_id != nivel.pk:
        raise ValidationError("La carrera no pertenece al nivel seleccionado.")
    if OfertaAcademica.objects.filter(institucion=institucion, ciclo=ciclo, carrera_catalogo=carrera, version_pensum=pensum).exists():
        raise ValidationError("Esta carrera y versión ya están configuradas para el ciclo.")
    oferta = OfertaAcademica.objects.create(
        institucion=institucion, ciclo=ciclo, nivel=nivel, carrera_catalogo=carrera,
        version_pensum=pensum, nombre_mostrado=nombre_mostrado or carrera.nombre,
        codigo_interno=codigo_interno or f"{carrera.codigo_interno}-{ciclo.anio}", origen=OfertaAcademica.Origen.CATALOGO,
    )
    grados = {}
    for grado_origen in pensum.grados.filter(activo=True):
        grados[grado_origen.pk] = GradoInstitucion.objects.create(
            institucion=institucion, ciclo=ciclo, oferta=oferta, grado_pensum_origen=grado_origen,
            codigo=grado_origen.codigo, nombre=grado_origen.nombre, orden=grado_origen.numero_orden,
        )
    for curso_origen in pensum.cursos_pensum.filter(activo=True).select_related("curso", "grado"):
        CursoInstitucion.objects.create(
            institucion=institucion, ciclo=ciclo, oferta=oferta, grado=grados[curso_origen.grado_id],
            curso_catalogo=curso_origen.curso, curso_pensum_origen=curso_origen,
            periodos_semanales=curso_origen.periodos_semanales, obligatorio=curso_origen.obligatorio,
            origen=CursoInstitucion.Origen.OFICIAL, orden=curso_origen.orden,
        )
    return oferta
