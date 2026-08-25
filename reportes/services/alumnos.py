from django.db.models import Count,Q,Prefetch
from alumnos.models import Alumno,Inscripcion
from .base import aplicar_estructura
def queryset(institucion,ciclo,params):
 ins_qs=Inscripcion.objects.select_related("grado","seccion","oferta_academica")
 if ciclo:ins_qs=ins_qs.filter(ciclo=ciclo)
 qs=Alumno.objects.filter(institucion=institucion).prefetch_related("vinculos_encargados__encargado",Prefetch("inscripciones",queryset=ins_qs,to_attr="inscripciones_reporte")).select_related("familia")
 if ciclo:qs=qs.filter(inscripciones__ciclo=ciclo).distinct()
 qs=aplicar_estructura(qs,params,"inscripciones")
 if params.get("estado"):qs=qs.filter(estado=params["estado"])
 if params.get("sexo"):qs=qs.filter(sexo=params["sexo"])
 return qs.order_by("primer_apellido","primer_nombre")
def filas(qs,ciclo):
 result=[]
 for a in qs:
  ins=next(iter(a.inscripciones_reporte),None)
  v=next((v for v in a.vinculos_encargados.all() if v.es_principal),None) or next(iter(a.vinculos_encargados.all()),None)
  result.append({"alumno":a,"inscripcion":ins,"encargado":v.encargado if v else None})
 return result
def estadisticas(institucion,qs):
 return {"total":qs.count(),"activos":qs.filter(estado="ACTIVO").count(),"retirados":qs.filter(estado="RETIRADO").count(),"egresados":qs.filter(estado="EGRESADO").count()}
def inscripciones(institucion,ciclo,params):
 qs=Inscripcion.objects.filter(institucion=institucion).select_related("alumno","oferta_academica","grado","seccion")
 if ciclo:qs=qs.filter(ciclo=ciclo)
 return aplicar_estructura(qs,params,"").order_by("alumno__primer_apellido")
