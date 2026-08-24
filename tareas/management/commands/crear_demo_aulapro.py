from datetime import date,timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from academico.models import CicloEscolar,CursoInstitucion,GradoInstitucion,OfertaAcademica,Seccion
from alumnos.models import Alumno,Inscripcion,Encargado,AlumnoEncargado
from catalogos.models import NivelEducativo
from docentes.models import AsignacionDocente,Docente
from instituciones.models import Institucion,UsuarioInstitucion
from finanzas.models import Cargo,ConceptoCobro,MetodoPago,Pago
from finanzas.services import config as config_financiera,registrar_pago
from django.test import RequestFactory
from tareas.models import Tarea
from tareas.services import sincronizar_entregas_tarea
class Command(BaseCommand):
 help="Crea un entorno demo idempotente por roles, incluyendo tareas."
 def handle(self,*args,**opts):
  inst,_=Institucion.objects.get_or_create(codigo="DEMO",defaults={"nombre":"Institución Demo AulaPro","nombre_corto":"AulaPro Demo"});U=get_user_model()
  users={}
  nombres={"ADMINISTRADOR":"admin","DOCENTE":"docente","CONTABILIDAD":"contabilidad","SECRETARIA":"secretaria"}
  for rol,sufijo in nombres.items():
   u,_=U.objects.get_or_create(username="demo_"+sufijo);u.set_password("AulaProDemo2026!");u.save();UsuarioInstitucion.objects.get_or_create(usuario=u,institucion=inst,defaults={"rol":rol});users[rol]=u
  ciclo,_=CicloEscolar.objects.get_or_create(institucion=inst,anio=2026,defaults={"nombre":"Ciclo 2026","fecha_inicio":date(2026,1,1),"fecha_fin":date(2026,11,30),"activo":True,"es_actual":True});nivel,_=NivelEducativo.objects.get_or_create(codigo="DEMO-BAS",defaults={"nombre":"Básico"});oferta,_=OfertaAcademica.objects.get_or_create(institucion=inst,ciclo=ciclo,codigo_interno="BAS",defaults={"nivel":nivel,"nombre_mostrado":"Nivel Básico","origen":"PERSONALIZADA"});grado,_=GradoInstitucion.objects.get_or_create(oferta=oferta,codigo="1B",defaults={"institucion":inst,"ciclo":ciclo,"nombre":"Primero Básico"});seccion,_=Seccion.objects.get_or_create(grado=grado,nombre="A",defaults={"institucion":inst,"ciclo":ciclo,"codigo":"A"});curso,_=CursoInstitucion.objects.get_or_create(grado=grado,nombre_personalizado="Matemática",defaults={"institucion":inst,"ciclo":ciclo,"oferta":oferta,"nombre_mostrado":"Matemática","origen":"INSTITUCIONAL"});doc,_=Docente.objects.get_or_create(institucion=inst,usuario=users["DOCENTE"],defaults={"primer_nombre":"Docente","primer_apellido":"Demo","telefono":"5555-0000","fecha_ingreso":date(2026,1,1)});asig,_=AsignacionDocente.objects.get_or_create(docente=doc,ciclo=ciclo,seccion=seccion,curso=curso,defaults={"institucion":inst,"oferta_academica":oferta,"grado":grado,"fecha_inicio":date(2026,1,1)})
  for n in range(1,5):
   al,_=Alumno.objects.get_or_create(institucion=inst,cui=f"100000000000{n}",defaults={"primer_nombre":f"Alumno {n}","primer_apellido":"Demo","fecha_nacimiento":date(2014,1,n),"sexo":"F" if n==1 else "M","fecha_ingreso":date(2026,1,1)});Inscripcion.objects.get_or_create(alumno=al,ciclo=ciclo,defaults={"institucion":inst,"oferta_academica":oferta,"grado":grado,"seccion":seccion,"fecha_inscripcion":date(2026,1,2)})
  ahora=timezone.now();datos=(("Guía de ejercicios 3","PUBLICADA",ahora+timedelta(days=3)),("Investigación de geometría","BORRADOR",ahora+timedelta(days=10)),("Práctica para mañana","PUBLICADA",ahora+timedelta(days=1)))
  for titulo,estado,limite in datos:
   t,_=Tarea.objects.get_or_create(institucion=inst,asignacion_docente=asig,titulo=titulo,defaults={"ciclo":ciclo,"curso":curso,"grado":grado,"seccion":seccion,"descripcion":"Actividad demostrativa de AulaPro.","instrucciones":"Lee las instrucciones y completa la actividad.","fecha_publicacion":ahora,"fecha_limite":limite,"estado":estado,"creada_por":users["DOCENTE"]})
   if t.estado=="PUBLICADA":
    if titulo=="Guía de ejercicios 3" and not t.permite_entrega_archivo: t.permite_entrega_archivo=True;t.save(update_fields=("permite_entrega_archivo","fecha_actualizacion"))
    sincronizar_entregas_tarea(t)
  config_financiera(inst);efectivo,_=MetodoPago.objects.get_or_create(institucion=inst,codigo="EFECTIVO",defaults={"nombre":"Efectivo"});inscripcion,_=ConceptoCobro.objects.get_or_create(institucion=inst,codigo="INS",defaults={"nombre":"Inscripción","tipo_general":"INSCRIPCION","monto_predeterminado":400});colegiatura,_=ConceptoCobro.objects.get_or_create(institucion=inst,codigo="COL",defaults={"nombre":"Colegiatura","tipo_general":"MENSUALIDAD","monto_predeterminado":500,"recurrente":True})
  alumnos=list(Alumno.objects.filter(institucion=inst).order_by("cui")[:4]);hoy=timezone.localdate()
  padre,_=U.objects.get_or_create(username="demo_padre",defaults={"first_name":"María","last_name":"Demo"});padre.set_password("AulaProDemo2026!");padre.save();UsuarioInstitucion.objects.update_or_create(usuario=padre,institucion=inst,defaults={"rol":"PADRE","activo":True})
  alumno_user,_=U.objects.get_or_create(username="demo_alumno",defaults={"first_name":"Alumno","last_name":"Demo"});alumno_user.set_password("AulaProDemo2026!");alumno_user.save();UsuarioInstitucion.objects.update_or_create(usuario=alumno_user,institucion=inst,defaults={"rol":"ALUMNO","activo":True})
  encargado,_=Encargado.objects.get_or_create(institucion=inst,usuario=padre,defaults={"nombres":"María","apellidos":"Demo","telefono":"5555-1000","email":"padre@demo.aulapro"})
  for al in alumnos[:2]: AlumnoEncargado.objects.get_or_create(institucion=inst,alumno=al,encargado=encargado,defaults={"parentesco":"MADRE","activo":True,"es_principal":True})
  if alumnos:
   alumnos[0].usuario=alumno_user;alumnos[0].save(update_fields=("usuario","fecha_actualizacion"))
  for al in alumnos:
   ins=al.inscripciones.filter(ciclo=ciclo).first()
   for concepto,periodo,monto,vence in ((inscripcion,"2026-I",400,date(2026,1,15)),(colegiatura,"2026-07",500,date(2026,7,10)),(colegiatura,"2026-08",500,date(2026,8,10))):Cargo.objects.get_or_create(institucion=inst,alumno=al,concepto=concepto,periodo_referencia=periodo,defaults={"familia":al.familia,"ciclo":ciclo,"inscripcion":ins,"descripcion":f"{concepto.nombre} {periodo}","fecha_emision":date(2026,1,1) if concepto==inscripcion else vence.replace(day=1),"fecha_vencimiento":vence,"monto_original":monto,"monto_total":monto,"creado_por":users["CONTABILIDAD"]})
  req=RequestFactory().post("/");req.user=users["CONTABILIDAD"];req.institucion=inst;req.asignacion_institucion=UsuarioInstitucion.objects.get(usuario=req.user,institucion=inst);req.META["REMOTE_ADDR"]="127.0.0.1"
  if alumnos and not Pago.objects.filter(institucion=inst,referencia="DEMO-PAGO-1").exists():
   cs=list(Cargo.objects.filter(institucion=inst,alumno=alumnos[0]));registrar_pago(req,alumno=alumnos[0],monto=sum(c.saldo for c in cs),metodo_pago=efectivo,referencia="DEMO-PAGO-1",aplicaciones={c.pk:c.saldo for c in cs})
  if len(alumnos)>1 and not Pago.objects.filter(institucion=inst,referencia="DEMO-PAGO-2").exists():
   c=Cargo.objects.filter(institucion=inst,alumno=alumnos[1],concepto=colegiatura).order_by("fecha_vencimiento").first();registrar_pago(req,alumno=alumnos[1],monto=200,metodo_pago=efectivo,referencia="DEMO-PAGO-2",aplicaciones={c.pk:200})
  self.stdout.write(self.style.SUCCESS("Demo AulaPro creado/actualizado con portal familiar, tareas y finanzas por roles."))
