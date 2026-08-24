from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied,ValidationError
from django.test import Client,RequestFactory,TestCase
from django.urls import reverse
from academico.models import CicloEscolar,CursoInstitucion,GradoInstitucion,OfertaAcademica,Seccion
from alumnos.models import Alumno,Inscripcion
from auditoria.models import EventoAuditoria
from catalogos.models import NivelEducativo
from docentes.models import AsignacionDocente,Docente
from instituciones.models import Institucion,UsuarioInstitucion
from .models import *
from .services import *
class Base(TestCase):
 def setUp(self):
  self.a=Institucion.objects.create(nombre="A",codigo="CA");self.b=Institucion.objects.create(nombre="B",codigo="CB");self.u={}
  for rolx in ("ADMINISTRADOR","DOCENTE","SECRETARIA","CONTABILIDAD"):
   u=get_user_model().objects.create_user(username="c"+rolx,password="x");UsuarioInstitucion.objects.create(usuario=u,institucion=self.a,rol=rolx);self.u[rolx]=u
  self.c=CicloEscolar.objects.create(institucion=self.a,nombre="2026",anio=2026,fecha_inicio=date(2026,1,1),fecha_fin=date(2026,12,1));n=NivelEducativo.objects.create(codigo="CN",nombre="N");self.o=OfertaAcademica.objects.create(institucion=self.a,ciclo=self.c,nivel=n,nombre_mostrado="O",codigo_interno="O",origen="PERSONALIZADA");self.g=GradoInstitucion.objects.create(institucion=self.a,ciclo=self.c,oferta=self.o,codigo="G",nombre="G");self.s=Seccion.objects.create(institucion=self.a,ciclo=self.c,grado=self.g,codigo="S",nombre="S");self.curso=CursoInstitucion.objects.create(institucion=self.a,ciclo=self.c,oferta=self.o,grado=self.g,nombre_personalizado="Mate",nombre_mostrado="Mate",origen="INSTITUCIONAL")
  self.d=Docente.objects.create(institucion=self.a,usuario=self.u["DOCENTE"],primer_nombre="D",primer_apellido="D",telefono="1",fecha_ingreso=date(2026,1,1));self.asig=AsignacionDocente.objects.create(institucion=self.a,ciclo=self.c,docente=self.d,oferta_academica=self.o,grado=self.g,seccion=self.s,curso=self.curso,fecha_inicio=date(2026,1,1));self.al=Alumno.objects.create(institucion=self.a,cui="1234567890123",primer_nombre="A",primer_apellido="A",fecha_nacimiento=date(2015,1,1),sexo="F",fecha_ingreso=date(2026,1,1));self.ins=Inscripcion.objects.create(institucion=self.a,alumno=self.al,ciclo=self.c,oferta_academica=self.o,grado=self.g,seccion=self.s,fecha_inscripcion=date(2026,1,1));self.p=PeriodoAcademico.objects.create(institucion=self.a,ciclo=self.c,nombre="P1",codigo="P1",numero_orden=1,fecha_inicio=date(2026,1,1),fecha_fin=date(2026,3,31));self.t=TipoEvaluacion.objects.create(institucion=self.a,nombre="Examen",codigo="EX")
 def req(self,rolx="ADMINISTRADOR"):
  r=RequestFactory().post("/");r.user=self.u[rolx];r.institucion=self.a;r.asignacion_institucion=UsuarioInstitucion.objects.get(usuario=r.user,institucion=self.a);r.META["REMOTE_ADDR"]="127.0.0.1";return r
 def act(self,pond="100.00"):
  return crear_actividad(self.req(),periodo=self.p,asignacion_docente=self.asig,tipo_evaluacion=self.t,nombre="E",descripcion="",fecha=date(2026,2,1),fecha_entrega=None,punteo_maximo=Decimal("100"),ponderacion=Decimal(pond),es_recuperacion=False,ciclo=self.c,curso=self.curso,grado=self.g,seccion=self.s)
class PeriodosTests(Base):
 def test_periodo_tenant(self):
  x=PeriodoAcademico(institucion=self.b,ciclo=self.c,nombre="x",codigo="x",numero_orden=2,fecha_inicio=date(2026,1,1),fecha_fin=date(2026,2,1));self.assertRaises(ValidationError,x.save)
 def test_codigo_duplicado(self):self.assertRaises(ValidationError,PeriodoAcademico.objects.create,institucion=self.a,ciclo=self.c,nombre="x",codigo="P1",numero_orden=2,fecha_inicio=date(2026,4,1),fecha_fin=date(2026,5,1))
 def test_fechas(self):self.p.fecha_fin=date(2025,1,1);self.assertRaises(ValidationError,self.p.save)
 def test_docente_no_administra(self):self.client.force_login(self.u["DOCENTE"]);self.assertEqual(self.client.get(reverse("calificaciones:periodo_nuevo")).status_code,403)
 def test_tenant_no_ve_otro(self):self.client.force_login(self.u["ADMINISTRADOR"]);self.assertEqual(self.client.get(reverse("calificaciones:periodo_detalle",args=[999])).status_code,404)
class ActividadNotaTests(Base):
 def test_inicializa_alumnos(self):self.assertEqual(self.act().calificaciones.count(),1)
 def test_ponderacion_no_excede(self):self.act("80");self.assertRaises(ValidationError,crear_actividad,self.req(),periodo=self.p,asignacion_docente=self.asig,tipo_evaluacion=self.t,nombre="X",descripcion="",fecha=date(2026,2,2),fecha_entrega=None,punteo_maximo=Decimal("20"),ponderacion=Decimal("21"),es_recuperacion=False,ciclo=self.c,curso=self.curso,grado=self.g,seccion=self.s)
 def test_cerrado_bloquea(self):self.p.cerrado=True;self.p.save();self.assertRaises(ValidationError,self.act)
 def test_nota_unica(self):
  a=self.act();c=a.calificaciones.get();self.assertRaises(ValidationError,Calificacion.objects.create,institucion=self.a,actividad=a,alumno=self.al,inscripcion=self.ins,registrado_por=self.u["ADMINISTRADOR"])
 def test_rango(self):
  c=self.act().calificaciones.get();c.estado="CALIFICADO";c.punteo_obtenido=Decimal("101");self.assertRaises(ValidationError,c.save)
 def test_negativa(self):
  c=self.act().calificaciones.get();c.estado="CALIFICADO";c.punteo_obtenido=Decimal("-1");self.assertRaises(ValidationError,c.save)
 def test_decimal_ponderado(self):
  c=self.act("30").calificaciones.get();c.estado="CALIFICADO";c.punteo_obtenido=Decimal("80");c.save();self.assertEqual(c.aporte,Decimal("24"))
 def test_pendiente_no_es_cero(self):self.assertIsNone(self.act().calificaciones.get().aporte)
 def test_docente_externo_no_guarda(self):
  c=self.act().calificaciones.get();self.assertRaises(PermissionDenied,guardar_calificacion,self.req("SECRETARIA"),c,"CALIFICADO","80")
 def test_cambio_audita_detalles(self):
  c=self.act().calificaciones.get();guardar_calificacion(self.req(),c,"CALIFICADO","80");e=EventoAuditoria.objects.get(accion="REGISTRAR_CALIFICACION");self.assertEqual(e.detalles["nuevo"]["punteo"],"80")
class CierreBoletinAutosaveTests(Base):
 def test_no_cierra_ponderacion_incompleta(self):self.act("50");self.assertRaises(ValidationError,cerrar_periodo,self.req(),self.p)
 def test_no_cierra_pendientes(self):self.act();self.assertRaises(ValidationError,cerrar_periodo,self.req(),self.p)
 def test_admin_cierra(self):
  c=self.act().calificaciones.get();c.estado="CALIFICADO";c.punteo_obtenido=80;c.save();cerrar_periodo(self.req(),self.p);self.assertTrue(self.p.cerrado)
 def test_reabrir_audita(self):
  self.p.cerrado=True;self.p.save();reabrir_periodo(self.req(),self.p,"Corrección");self.assertTrue(EventoAuditoria.objects.filter(accion="REABRIR_PERIODO").exists())
 def test_resultado_configurable(self):cfg=config(self.a);cfg.nota_minima_aprobacion=Decimal("70");cfg.save();self.assertEqual(resultado(Decimal("65"),cfg),"NO APROBADO")
 def test_boletin_otro_tenant_404(self):self.client.force_login(self.u["ADMINISTRADOR"]);self.assertEqual(self.client.get(reverse("calificaciones:boletin",args=[999,self.p.pk])).status_code,404)
 def test_autosave_get_no_permitido(self):
  c=self.act().calificaciones.get();self.client.force_login(self.u["ADMINISTRADOR"]);self.assertEqual(self.client.get(reverse("calificaciones:autosave",args=[c.pk])).status_code,405)
 def test_autosave_json(self):
  c=self.act().calificaciones.get();self.client.force_login(self.u["DOCENTE"]);x=self.client.post(reverse("calificaciones:autosave",args=[c.pk]),{"estado":"CALIFICADO","punteo":"85"});self.assertTrue(x.json()["ok"])
 def test_autosave_csrf(self):
  c=self.act().calificaciones.get();cl=Client(enforce_csrf_checks=True);cl.force_login(self.u["DOCENTE"]);self.assertEqual(cl.post(reverse("calificaciones:autosave",args=[c.pk]),{"punteo":"80"}).status_code,403)
