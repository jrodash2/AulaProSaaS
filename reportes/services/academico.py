from django.db.models import Count,Q
from academico.models import OfertaAcademica,Seccion,CursoInstitucion
def datos(institucion,ciclo):
 ofertas=OfertaAcademica.objects.filter(institucion=institucion,ciclo=ciclo).annotate(grados_total=Count("grados",distinct=True),cursos_total=Count("cursos",distinct=True),inscritos=Count("inscripciones",filter=Q(inscripciones__estado="ACTIVA"),distinct=True))
 secciones=Seccion.objects.filter(institucion=institucion,ciclo=ciclo,activa=True).select_related("grado").annotate(inscritos=Count("inscripciones",filter=Q(inscripciones__estado="ACTIVA")))
 for s in secciones:s.disponibilidad=None if s.capacidad is None else max(s.capacidad-s.inscritos,0)
 cursos=CursoInstitucion.objects.filter(institucion=institucion,ciclo=ciclo,activo=True).annotate(docentes=Count("asignaciones_docentes",filter=Q(asignaciones_docentes__activa=True)))
 return {"ofertas":ofertas,"secciones":secciones,"cursos":cursos,"con_docente":cursos.filter(docentes__gt=0).count(),"sin_docente":cursos.filter(docentes=0).count()}
