from django.db.models import Count,Q
from django.utils import timezone
from tareas.models import Tarea,EntregaTarea
def datos(institucion,ciclo,params,asignaciones=None):
 tareas=Tarea.objects.filter(institucion=institucion)
 if ciclo:tareas=tareas.filter(ciclo=ciclo)
 if params.get("seccion","").isdigit():tareas=tareas.filter(seccion_id=params["seccion"])
 if params.get("curso","").isdigit():tareas=tareas.filter(curso_id=params["curso"])
 if asignaciones is not None:tareas=tareas.filter(asignacion_docente__in=asignaciones)
 entregas=EntregaTarea.objects.filter(institucion=institucion,tarea__in=tareas)
 agg=entregas.aggregate(pendientes=Count("id",filter=Q(estado="PENDIENTE")),entregadas=Count("id",filter=Q(estado="ENTREGADA")),tarde=Count("id",filter=Q(estado="ENTREGADA_TARDE")))
 return {"tareas":tareas.select_related("curso","seccion","asignacion_docente__docente"),"publicadas":tareas.filter(estado="PUBLICADA").count(),"vencidas":tareas.filter(estado="PUBLICADA",fecha_limite__lt=timezone.now()).count(),**agg}
