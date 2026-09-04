"""Consultas agregadas para el Centro de Demostración.

La presentación consume esta estructura ya calculada y nunca consulta objetos
tenant-owned desde el template.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from academico.models import CicloEscolar
from admisiones.models import SolicitudAdmision
from alumnos.models import Alumno, DocumentoAlumno, Encargado, Familia, Inscripcion
from asistencia.models import RegistroAsistencia, SesionAsistencia
from calificaciones.models import ActividadEvaluacion, Calificacion, PeriodoAcademico
from docentes.models import AsignacionDocente, Docente
from finanzas.models import AplicacionPago, Cargo, Pago
from horarios.models import Aula, BloqueHorario, HorarioClase
from rrhh.models import ContratoLaboral, Empleado, PermisoLaboral
from seguimiento.models import CategoriaSeguimiento, CompromisoSeguimiento, RegistroSeguimiento
from tareas.models import Tarea


def _counts(queryset, field, values):
    grouped = dict(
        queryset.filter(**{f"{field}__in": values})
        .values_list(field)
        .annotate(total=Count("pk"))
    )
    return {value: grouped.get(value, 0) for value in values}


def obtener_resumen_demo(institucion):
    """Devuelve únicamente métricas agregadas y aisladas por institución."""
    hoy = timezone.localdate()
    tareas = Tarea.objects.filter(institucion=institucion)
    solicitudes = SolicitudAdmision.objects.filter(institucion=institucion)
    documentos = DocumentoAlumno.objects.filter(institucion=institucion)
    seguimientos = RegistroSeguimiento.objects.filter(institucion=institucion)
    contratos = ContratoLaboral.objects.filter(institucion=institucion)
    cargos = Cargo.objects.filter(institucion=institucion).exclude(estado=Cargo.Estado.ANULADO)
    aplicaciones = AplicacionPago.objects.filter(
        institucion=institucion, pago__estado=Pago.Estado.CONFIRMADO
    ).aggregate(total=Coalesce(Sum("monto_aplicado"), Decimal("0")))["total"]
    total_cargos = cargos.aggregate(
        total=Coalesce(
            Sum("monto_total"),
            Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"]

    return {
        "academico": {
            "ciclos": CicloEscolar.objects.filter(institucion=institucion).count(),
            "anios": list(CicloEscolar.objects.filter(institucion=institucion).order_by("anio").values_list("anio", flat=True)),
        },
        "alumnos": {
            "alumnos": Alumno.objects.filter(institucion=institucion).count(),
            "familias": Familia.objects.filter(institucion=institucion).count(),
            "encargados": Encargado.objects.filter(institucion=institucion).count(),
            "inscripciones": Inscripcion.objects.filter(institucion=institucion).count(),
        },
        "docentes": {
            "activos": Docente.objects.filter(institucion=institucion, estado=Docente.Estado.ACTIVO).count(),
            "inactivos": Docente.objects.filter(institucion=institucion).exclude(estado=Docente.Estado.ACTIVO).count(),
            "asignaciones": AsignacionDocente.objects.filter(institucion=institucion, activa=True).count(),
        },
        "asistencia": {
            "sesiones": SesionAsistencia.objects.filter(institucion=institucion).count(),
            "registros": RegistroAsistencia.objects.filter(institucion=institucion).count(),
        },
        "calificaciones": {
            "periodos": PeriodoAcademico.objects.filter(institucion=institucion).count(),
            "actividades": ActividadEvaluacion.objects.filter(institucion=institucion).count(),
            "calificaciones": Calificacion.objects.filter(institucion=institucion).count(),
        },
        "tareas": {
            "publicadas": tareas.filter(estado=Tarea.Estado.PUBLICADA).count(),
            "vigentes": tareas.filter(estado=Tarea.Estado.PUBLICADA, fecha_limite__gte=timezone.now()).count(),
            "vencidas": tareas.filter(fecha_limite__lt=timezone.now()).exclude(estado=Tarea.Estado.ANULADA).count(),
        },
        "finanzas": {
            "cargos": cargos.count(),
            "pagos": Pago.objects.filter(institucion=institucion, estado=Pago.Estado.CONFIRMADO).count(),
            "saldo": max(total_cargos - aplicaciones, Decimal("0")),
        },
        "expediente": _counts(
            documentos, "estado", (DocumentoAlumno.Estado.APROBADO, DocumentoAlumno.Estado.PENDIENTE, DocumentoAlumno.Estado.RECHAZADO)
        ),
        "horarios": {
            "aulas": Aula.objects.filter(institucion=institucion, activa=True).count(),
            "bloques": BloqueHorario.objects.filter(institucion=institucion, activo=True).count(),
            "clases": HorarioClase.objects.filter(institucion=institucion, activo=True).count(),
        },
        "seguimiento": {
            "reconocimientos": seguimientos.filter(tipo=CategoriaSeguimiento.Tipo.POSITIVO).count(),
            "incidencias": seguimientos.filter(tipo=CategoriaSeguimiento.Tipo.INCIDENCIA).count(),
            "abiertos": seguimientos.filter(estado__in=(RegistroSeguimiento.Estado.ABIERTO, RegistroSeguimiento.Estado.EN_SEGUIMIENTO)).count(),
            "compromisos": CompromisoSeguimiento.objects.filter(institucion=institucion).count(),
        },
        "admisiones": _counts(
            solicitudes,
            "estado",
            (SolicitudAdmision.Estado.NUEVA, SolicitudAdmision.Estado.EN_REVISION, SolicitudAdmision.Estado.APROBADA, SolicitudAdmision.Estado.LISTA_ESPERA, SolicitudAdmision.Estado.INSCRITA),
        ),
        "rrhh": {
            "empleados": Empleado.objects.filter(institucion=institucion, estado=Empleado.Estado.ACTIVO).count(),
            "contratos": contratos.filter(estado=ContratoLaboral.Estado.VIGENTE).count(),
            "por_vencer": contratos.filter(estado=ContratoLaboral.Estado.VIGENTE, fecha_fin__range=(hoy, hoy + timedelta(days=30))).count(),
            "permisos": PermisoLaboral.objects.filter(institucion=institucion, estado=PermisoLaboral.Estado.PENDIENTE).count(),
        },
    }
