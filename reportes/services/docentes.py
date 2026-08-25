from django.db.models import Count,Q
from docentes.models import Docente,AsignacionDocente
from academico.models import CursoInstitucion
def datos(institucion,ciclo):
 docentes=Docente.objects.filter(institucion=institucion).annotate(cursos=Count("asignaciones",filter=Q(asignaciones__activa=True,asignaciones__ciclo=ciclo),distinct=True),secciones=Count("asignaciones__seccion",filter=Q(asignaciones__activa=True,asignaciones__ciclo=ciclo),distinct=True))
 cursos=CursoInstitucion.objects.filter(institucion=institucion,ciclo=ciclo,activo=True);asignados=cursos.filter(asignaciones_docentes__activa=True).distinct().count()
 return {"docentes":docentes,"cursos_total":cursos.count(),"cursos_asignados":asignados,"cursos_sin":cursos.count()-asignados}
