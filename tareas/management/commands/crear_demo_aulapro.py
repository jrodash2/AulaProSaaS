from datetime import date,timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from academico.models import CicloEscolar,CursoInstitucion,GradoInstitucion,OfertaAcademica,Seccion
from alumnos.models import Alumno,Inscripcion
from catalogos.models import NivelEducativo
from docentes.models import AsignacionDocente,Docente
from instituciones.models import Institucion,UsuarioInstitucion
from tareas.models import Tarea
from tareas.services import sincronizar_entregas_tarea
class Command(BaseCommand):
 help="Crea un entorno demo idempotente por roles, incluyendo tareas."
 def handle(self,*args,**opts):
  inst,_=Institucion.objects.get_or_create(codigo="DEMO",defaults={"nombre":"Institución Demo AulaPro","nombre_corto":"AulaPro Demo"});U=get_user_model()
  users={}
  for rol in ("ADMINISTRADOR","DOCENTE"):
   u,_=U.objects.get_or_create(username="demo_"+("admin" if rol=="ADMINISTRADOR" else "docente"));u.set_password("AulaProDemo2026!");u.save();UsuarioInstitucion.objects.get_or_create(usuario=u,institucion=inst,defaults={"rol":rol});users[rol]=u
  ciclo,_=CicloEscolar.objects.get_or_create(institucion=inst,anio=2026,defaults={"nombre":"Ciclo 2026","fecha_inicio":date(2026,1,1),"fecha_fin":date(2026,11,30),"activo":True,"es_actual":True});nivel,_=NivelEducativo.objects.get_or_create(codigo="DEMO-BAS",defaults={"nombre":"Básico"});oferta,_=OfertaAcademica.objects.get_or_create(institucion=inst,ciclo=ciclo,codigo_interno="BAS",defaults={"nivel":nivel,"nombre_mostrado":"Nivel Básico","origen":"PERSONALIZADA"});grado,_=GradoInstitucion.objects.get_or_create(oferta=oferta,codigo="1B",defaults={"institucion":inst,"ciclo":ciclo,"nombre":"Primero Básico"});seccion,_=Seccion.objects.get_or_create(grado=grado,nombre="A",defaults={"institucion":inst,"ciclo":ciclo,"codigo":"A"});curso,_=CursoInstitucion.objects.get_or_create(grado=grado,nombre_personalizado="Matemática",defaults={"institucion":inst,"ciclo":ciclo,"oferta":oferta,"nombre_mostrado":"Matemática","origen":"INSTITUCIONAL"});doc,_=Docente.objects.get_or_create(institucion=inst,usuario=users["DOCENTE"],defaults={"primer_nombre":"Docente","primer_apellido":"Demo","telefono":"5555-0000","fecha_ingreso":date(2026,1,1)});asig,_=AsignacionDocente.objects.get_or_create(docente=doc,ciclo=ciclo,seccion=seccion,curso=curso,defaults={"institucion":inst,"oferta_academica":oferta,"grado":grado,"fecha_inicio":date(2026,1,1)})
  for n in range(1,3):
   al,_=Alumno.objects.get_or_create(institucion=inst,cui=f"100000000000{n}",defaults={"primer_nombre":f"Alumno {n}","primer_apellido":"Demo","fecha_nacimiento":date(2014,1,n),"sexo":"F" if n==1 else "M","fecha_ingreso":date(2026,1,1)});Inscripcion.objects.get_or_create(alumno=al,ciclo=ciclo,defaults={"institucion":inst,"oferta_academica":oferta,"grado":grado,"seccion":seccion,"fecha_inscripcion":date(2026,1,2)})
  ahora=timezone.now();datos=(("Guía de ejercicios 3","PUBLICADA",ahora+timedelta(days=3)),("Investigación de geometría","BORRADOR",ahora+timedelta(days=10)),("Práctica para mañana","PUBLICADA",ahora+timedelta(days=1)))
  for titulo,estado,limite in datos:
   t,_=Tarea.objects.get_or_create(institucion=inst,asignacion_docente=asig,titulo=titulo,defaults={"ciclo":ciclo,"curso":curso,"grado":grado,"seccion":seccion,"descripcion":"Actividad demostrativa de AulaPro.","instrucciones":"Lee las instrucciones y completa la actividad.","fecha_publicacion":ahora,"fecha_limite":limite,"estado":estado,"creada_por":users["DOCENTE"]})
   if t.estado=="PUBLICADA":sincronizar_entregas_tarea(t)
  self.stdout.write(self.style.SUCCESS("Demo AulaPro creado/actualizado: demo_admin y demo_docente."))
