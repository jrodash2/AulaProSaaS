from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import CicloEscolar, CursoInstitucion, GradoInstitucion, OfertaAcademica, ResultadoAnualAlumno, Seccion


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


def obtener_grado_siguiente(grado):
    """Devuelve el grado posterior por orden dentro de la misma oferta, nunca por nombre."""
    return grado.oferta.grados.filter(activo=True, orden__gt=grado.orden).order_by("orden", "pk").first()


def _promedio_anual(inscripcion):
    from calificaciones.models import Calificacion
    from calificaciones.services import promedio_alumno

    cursos = list(inscripcion.grado.cursos.filter(activo=True, obligatorio=True))
    periodos = list(inscripcion.ciclo.periodos_academicos.filter(activo=True).order_by("numero_orden"))
    if not cursos or not periodos or any(not periodo.cerrado for periodo in periodos):
        return None
    notas = []
    for curso in cursos:
        for periodo in periodos:
            if not Calificacion.objects.filter(inscripcion=inscripcion, actividad__curso=curso, actividad__periodo=periodo, actividad__activa=True).exists():
                return None
            nota = promedio_alumno(inscripcion.alumno, periodo, curso)
            if nota is None:
                return None
            notas.append(nota)
    return (sum(notas, Decimal("0")) / Decimal(len(notas))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@transaction.atomic
def generar_resultado_anual(inscripcion):
    """Genera una sugerencia reproducible sin convertir notas ausentes en cero."""
    from alumnos.models import Inscripcion
    from calificaciones.services import config

    inscripcion = Inscripcion.objects.select_for_update().select_related("alumno", "ciclo", "grado__oferta").get(pk=inscripcion.pk)
    if inscripcion.estado == Inscripcion.Estado.RETIRADA:
        promedio, sugerido = None, ResultadoAnualAlumno.Resultado.RETIRADO
    elif inscripcion.estado == Inscripcion.Estado.TRASLADADA:
        promedio, sugerido = None, ResultadoAnualAlumno.Resultado.TRASLADADO
    else:
        promedio = _promedio_anual(inscripcion)
        if promedio is None:
            sugerido = ResultadoAnualAlumno.Resultado.PENDIENTE
        elif promedio < config(inscripcion.institucion).nota_minima_aprobacion:
            sugerido = ResultadoAnualAlumno.Resultado.NO_PROMOVIDO
        elif obtener_grado_siguiente(inscripcion.grado) is None:
            sugerido = ResultadoAnualAlumno.Resultado.EGRESADO
        else:
            sugerido = ResultadoAnualAlumno.Resultado.PROMOVIDO
    resultado, _ = ResultadoAnualAlumno.objects.update_or_create(
        inscripcion=inscripcion,
        defaults={"institucion": inscripcion.institucion, "ciclo": inscripcion.ciclo, "alumno": inscripcion.alumno,
                  "promedio_final": promedio, "resultado_sugerido": sugerido, "generado_automaticamente": True},
    )
    return resultado


@transaction.atomic
def confirmar_resultado(resultado, resultado_final, usuario, observaciones=""):
    resultado = ResultadoAnualAlumno.objects.select_for_update().get(pk=resultado.pk)
    if resultado_final == ResultadoAnualAlumno.Resultado.PENDIENTE:
        raise ValidationError("Un resultado pendiente no puede confirmarse.")
    resultado.resultado_final = resultado_final
    resultado.observaciones = observaciones
    resultado.confirmado_por = usuario
    resultado.fecha_confirmacion = timezone.now()
    resultado.save()
    return resultado


def validar_cierre(ciclo):
    bloqueos, advertencias = [], []
    if ciclo.periodos_academicos.filter(activo=True, cerrado=False).exists():
        bloqueos.append("Existen períodos académicos abiertos.")
    activas = ciclo.inscripciones.filter(estado="ACTIVA")
    faltantes = activas.exclude(resultado_anual__resultado_final__isnull=False).count()
    if faltantes:
        bloqueos.append(f"Existen {faltantes} estudiantes sin resultado final confirmado.")
    abiertas = ciclo.tareas.exclude(estado="CERRADA").count() if hasattr(ciclo, "tareas") else 0
    if abiertas:
        advertencias.append(f"Existen {abiertas} tareas abiertas.")
    return {"bloqueos": bloqueos, "advertencias": advertencias, "puede_cerrar": not bloqueos}


@transaction.atomic
def cerrar_ciclo(ciclo):
    ciclo = CicloEscolar.objects.select_for_update().get(pk=ciclo.pk)
    validacion = validar_cierre(ciclo)
    if not validacion["puede_cerrar"]:
        raise ValidationError(validacion["bloqueos"])
    ciclo.inscripciones.filter(estado="ACTIVA").update(estado="FINALIZADA")
    ciclo.estado, ciclo.cerrado, ciclo.activo, ciclo.es_actual = CicloEscolar.Estado.CERRADO, True, False, False
    ciclo.save()
    return ciclo


@transaction.atomic
def crear_ciclo_siguiente(ciclo, *, anio=None):
    """Copia solamente estructura dependiente del ciclo; jornadas siguen siendo institucionales."""
    if not ciclo.cerrado:
        raise ValidationError("El ciclo de origen debe estar cerrado.")
    anio = anio or ciclo.anio + 1
    nuevo = CicloEscolar.objects.create(institucion=ciclo.institucion, nombre=f"Ciclo {anio}", anio=anio,
        fecha_inicio=ciclo.fecha_inicio.replace(year=anio), fecha_fin=ciclo.fecha_fin.replace(year=anio), estado=CicloEscolar.Estado.PLANIFICACION)
    grados = {}
    for oferta in ciclo.ofertas.all():
        nueva = OfertaAcademica.objects.create(institucion=ciclo.institucion, ciclo=nuevo, nivel=oferta.nivel,
            carrera_catalogo=oferta.carrera_catalogo, version_pensum=oferta.version_pensum, nombre_mostrado=oferta.nombre_mostrado,
            codigo_interno=oferta.codigo_interno, origen=oferta.origen, activa=oferta.activa)
        for grado in oferta.grados.all():
            grados[grado.pk] = GradoInstitucion.objects.create(institucion=ciclo.institucion, ciclo=nuevo, oferta=nueva,
                grado_pensum_origen=grado.grado_pensum_origen, codigo=grado.codigo, nombre=grado.nombre, orden=grado.orden, activo=grado.activo)
    for seccion in ciclo.secciones.all():
        Seccion.objects.create(institucion=ciclo.institucion, ciclo=nuevo, grado=grados[seccion.grado_id], jornada=seccion.jornada,
            codigo=seccion.codigo, nombre=seccion.nombre, capacidad=seccion.capacidad, activa=seccion.activa)
    for curso in ciclo.cursos.all():
        CursoInstitucion.objects.create(institucion=ciclo.institucion, ciclo=nuevo, oferta=grados[curso.grado_id].oferta,
            grado=grados[curso.grado_id], curso_catalogo=curso.curso_catalogo, curso_pensum_origen=curso.curso_pensum_origen,
            nombre_mostrado=curso.nombre_mostrado, nombre_personalizado=curso.nombre_personalizado,
            periodos_semanales=curso.periodos_semanales, obligatorio=curso.obligatorio, origen=curso.origen, orden=curso.orden, activo=curso.activo)
    return nuevo
