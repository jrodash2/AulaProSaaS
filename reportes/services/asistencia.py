from django.db.models import Count,Q
from asistencia.models import RegistroAsistencia
def registros(institucion,ciclo,params,asignaciones=None):
 qs=RegistroAsistencia.objects.filter(institucion=institucion,sesion__tipo="GENERAL",sesion__estado="CERRADA").select_related("alumno","sesion")
 if ciclo:qs=qs.filter(sesion__ciclo=ciclo)
 if params.get("desde"):qs=qs.filter(sesion__fecha__gte=params["desde"])
 if params.get("hasta"):qs=qs.filter(sesion__fecha__lte=params["hasta"])
 if params.get("grado","").isdigit():qs=qs.filter(sesion__grado_id=params["grado"])
 if params.get("seccion","").isdigit():qs=qs.filter(sesion__seccion_id=params["seccion"])
 if asignaciones is not None:qs=qs.filter(sesion__seccion_id__in=asignaciones.values("seccion_id"))
 return qs.exclude(estado="SIN_MARCAR")
def resumen(qs):
 agg=qs.aggregate(total=Count("id"),presentes=Count("id",filter=Q(estado="PRESENTE")),ausentes=Count("id",filter=Q(estado="AUSENTE")),tardes=Count("id",filter=Q(estado="TARDE")),justificadas=Count("id",filter=Q(estado="AUSENTE",justificada=True)))
 agg["porcentaje"]=round((agg["presentes"]+agg["tardes"])*100/agg["total"],2) if agg["total"] else None
 return agg
def por_alumno(qs,umbral=80):
 rows=qs.values("alumno_id","alumno__primer_nombre","alumno__primer_apellido").annotate(total=Count("id"),presentes=Count("id",filter=Q(estado="PRESENTE")),ausentes=Count("id",filter=Q(estado="AUSENTE")),tardes=Count("id",filter=Q(estado="TARDE")),justificadas=Count("id",filter=Q(estado="AUSENTE",justificada=True))).order_by("alumno__primer_apellido")
 result=[]
 for r in rows:r["porcentaje"]=round((r["presentes"]+r["tardes"])*100/r["total"],2) if r["total"] else None;r["alerta"]=r["porcentaje"] is not None and r["porcentaje"]<umbral;result.append(r)
 return result
