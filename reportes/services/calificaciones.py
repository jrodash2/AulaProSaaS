from collections import defaultdict
from decimal import Decimal
from calificaciones.models import Calificacion,ConfiguracionCalificaciones
def queryset(institucion,ciclo,params,asignaciones=None):
 qs=Calificacion.objects.filter(institucion=institucion,actividad__activa=True).select_related("alumno","actividad__curso","actividad__periodo")
 if ciclo:qs=qs.filter(actividad__ciclo=ciclo)
 for key,field in (("periodo","actividad__periodo_id"),("grado","actividad__grado_id"),("seccion","actividad__seccion_id"),("curso","actividad__curso_id")):
  if params.get(key,"").isdigit():qs=qs.filter(**{field:params[key]})
 if asignaciones is not None:qs=qs.filter(actividad__asignacion_docente__in=asignaciones)
 return qs
def filas(qs,institucion):
 grouped=defaultdict(list)
 for n in qs:grouped[(n.alumno_id,n.actividad.curso_id,n.alumno.nombre_completo,str(n.actividad.curso))].append(n)
 minimum=ConfiguracionCalificaciones.objects.get_or_create(institucion=institucion)[0].nota_minima_aprobacion;rows=[]
 for (_,_,alumno,curso),notas in grouped.items():
  pendientes=sum(n.estado=="PENDIENTE" for n in notas);aportes=[n.aporte for n in notas if n.aporte is not None];promedio=sum(aportes,Decimal("0")) if aportes and not pendientes else None
  rows.append({"alumno":alumno,"curso":curso,"promedio":promedio,"pendientes":pendientes,"estado":"PENDIENTE" if promedio is None else ("APROBADO" if promedio>=minimum else "BAJO MÍNIMO")})
 return rows
def resumen(rows):
 vals=[r["promedio"] for r in rows if r["promedio"] is not None]
 return {"evaluados":len(vals),"promedio":sum(vals,Decimal("0"))/len(vals) if vals else None,"maxima":max(vals) if vals else None,"minima":min(vals) if vals else None,"pendientes":sum(r["pendientes"] for r in rows)}
