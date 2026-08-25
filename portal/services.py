from decimal import Decimal
from django.db.models import Count
from asistencia.models import RegistroAsistencia
from tareas.models import EntregaTarea, Tarea
from finanzas.models import Cargo

def resumen_alumno(alumno):
    ins=alumno.inscripciones.filter(estado="ACTIVA").select_related("grado","seccion").order_by("-ciclo__anio").first()
    registros=RegistroAsistencia.objects.filter(alumno=alumno).exclude(sesion__estado="ANULADA").exclude(estado="SIN_MARCAR")
    asistencias=registros.filter(estado__in=("PRESENTE","TARDE")).count()
    tareas=Tarea.objects.filter(institucion=alumno.institucion,seccion=ins.seccion,estado="PUBLICADA") if ins else Tarea.objects.none()
    pendientes=EntregaTarea.objects.filter(alumno=alumno,tarea__in=tareas,estado="PENDIENTE").count()
    cargos=Cargo.objects.filter(alumno=alumno).exclude(estado="ANULADO")
    saldo=sum((c.saldo for c in cargos),Decimal("0"))
    return {"alumno":alumno,"inscripcion":ins,"asistencia":round(asistencias*100/registros.count(),1) if registros.exists() else None,"tareas_pendientes":pendientes,"saldo":saldo}
