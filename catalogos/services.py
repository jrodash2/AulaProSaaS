from django.db import transaction

from .models import CursoPensum, GradoPensum, VersionPensum


@transaction.atomic
def duplicar_version_pensum(
    original,
    *,
    codigo_version,
    nombre,
    fecha_inicio_vigencia,
):
    nueva_version = VersionPensum.objects.create(
        carrera=original.carrera,
        codigo_version=codigo_version,
        nombre=nombre,
        acuerdo_ministerial="",
        fecha_inicio_vigencia=fecha_inicio_vigencia,
        estado=VersionPensum.Estado.BORRADOR,
        observaciones=f"Duplicado desde {original.codigo_version}.",
        fuente_oficial=original.fuente_oficial,
        url_fuente=original.url_fuente,
    )
    grados_nuevos = {}
    for grado in original.grados.all():
        grados_nuevos[grado.pk] = GradoPensum.objects.create(
            pensum=nueva_version,
            codigo=grado.codigo,
            nombre=grado.nombre,
            numero_orden=grado.numero_orden,
            activo=grado.activo,
        )
    CursoPensum.objects.bulk_create(
        [
            CursoPensum(
                pensum=nueva_version,
                grado=grados_nuevos[item.grado_id],
                curso=item.curso,
                orden=item.orden,
                periodos_semanales=item.periodos_semanales,
                obligatorio=item.obligatorio,
                observaciones=item.observaciones,
                activo=item.activo,
            )
            for item in original.cursos_pensum.select_related("curso", "grado")
        ]
    )
    return nueva_version
