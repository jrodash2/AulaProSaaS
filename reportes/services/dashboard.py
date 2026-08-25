from decimal import Decimal
from django.db.models import Count,Q
from alumnos.models import Alumno,Inscripcion
from docentes.models import Docente,AsignacionDocente
from academico.models import Seccion
from tareas.models import EntregaTarea
from calificaciones.models import Calificacion
from finanzas.models import Cargo
from .asistencia import registros,resumen
def datos(institucion,ciclo,params,finanzas=False,asignaciones=None):
 ins=Inscripcion.objects.filter(institucion=institucion,estado="ACTIVA");alumnos=Alumno.objects.filter(institucion=institucion,estado="ACTIVO")
 if ciclo:ins=ins.filter(ciclo=ciclo);alumnos=alumnos.filter(inscripciones__in=ins).distinct()
 asist=resumen(registros(institucion,ciclo,params,asignaciones))
 notas=Calificacion.objects.filter(institucion=institucion,estado="CALIFICADO",actividad__activa=True)
 pendientes=Calificacion.objects.filter(institucion=institucion,estado="PENDIENTE",actividad__activa=True)
 if ciclo:notas=notas.filter(actividad__ciclo=ciclo);pendientes=pendientes.filter(actividad__ciclo=ciclo)
 promedio=None
 if notas.exists() and not pendientes.exists():
  aportes=[n.aporte for n in notas.select_related("actividad") if n.aporte is not None];promedio=sum(aportes,Decimal("0"))/len({n.alumno_id for n in notas}) if aportes else None
 result={"alumnos":alumnos.count(),"inscripciones":ins.count(),"docentes":Docente.objects.filter(institucion=institucion,estado="ACTIVO").count(),"secciones":Seccion.objects.filter(institucion=institucion,ciclo=ciclo,activa=True).count() if ciclo else 0,"asistencia":asist["porcentaje"],"promedio":promedio,"tareas_pendientes":EntregaTarea.objects.filter(institucion=institucion,estado="PENDIENTE",tarea__ciclo=ciclo).count() if ciclo else 0}
 if finanzas:
  cargos=Cargo.objects.filter(institucion=institucion).exclude(estado="ANULADO");result["saldo"]=sum((c.saldo for c in cargos),Decimal("0"))
 return result
def asignaciones_docente(request,ciclo):
 return AsignacionDocente.objects.filter(institucion=request.institucion,ciclo=ciclo,docente__usuario=request.user,activa=True)
