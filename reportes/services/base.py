from academico.models import CicloEscolar
def ciclo_actual(institucion,valor=None):
 qs=CicloEscolar.objects.filter(institucion=institucion)
 if valor and str(valor).isdigit():
  item=qs.filter(pk=int(valor)).first()
  if item:return item
 return qs.filter(es_actual=True).first() or qs.filter(activo=True).order_by("-anio").first()
def int_param(params,nombre):
 value=params.get(nombre,"")
 return int(value) if value.isdigit() else None
def filtros_context(institucion,ciclo=None):
 from academico.models import OfertaAcademica,GradoInstitucion,Seccion
 return {"ciclos":institucion.ciclos_escolares.all(),"ofertas":OfertaAcademica.objects.filter(institucion=institucion,ciclo=ciclo) if ciclo else OfertaAcademica.objects.none(),"grados":GradoInstitucion.objects.filter(institucion=institucion,ciclo=ciclo) if ciclo else GradoInstitucion.objects.none(),"secciones":Seccion.objects.filter(institucion=institucion,ciclo=ciclo) if ciclo else Seccion.objects.none(),"ciclo_seleccionado":ciclo}
def aplicar_estructura(qs,params,prefix="inscripcion"):
 lead=f"{prefix}__" if prefix else ""
 for key,field in (("oferta",f"{lead}oferta_academica_id"),("grado",f"{lead}grado_id"),("seccion",f"{lead}seccion_id")):
  value=int_param(params,key)
  if value:qs=qs.filter(**{field:value})
 return qs
