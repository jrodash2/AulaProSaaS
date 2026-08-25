from datetime import date,timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from alumnos.models import Alumno,AlumnoEncargado,Encargado
from asistencia.models import SesionAsistencia,RegistroAsistencia
from instituciones.models import UsuarioInstitucion
from tareas.tests import Base
from finanzas.models import Cargo,ConceptoCobro,MetodoPago,Pago
from comunicaciones.models import Comunicacion,Notificacion
from .services import alumnos as salumnos,asistencia as sasistencia,finanzas as sfinanzas,comunicaciones as scom
class ReporteBase(Base):
 def setUp(self):
  super().setUp();self.director=get_user_model().objects.create_user("rdirector",password="x");self.padre=get_user_model().objects.create_user("rpadre",password="x");self.au=get_user_model().objects.create_user("ralumno",password="x");UsuarioInstitucion.objects.create(usuario=self.director,institucion=self.a,rol="DIRECTOR");UsuarioInstitucion.objects.create(usuario=self.padre,institucion=self.a,rol="PADRE");UsuarioInstitucion.objects.create(usuario=self.au,institucion=self.a,rol="ALUMNO")
 def login(self,user=None):self.client.force_login(user or self.director)
class SeguridadSmokeTests(ReporteBase):
 def test_padre_y_alumno_bloqueados(self):
  for u in (self.padre,self.au):self.login(u);self.assertEqual(self.client.get(reverse("reportes:dashboard")).status_code,403)
 def test_contabilidad_solo_finanzas(self):
  self.login(self.u["CONTABILIDAD"]);self.assertEqual(self.client.get(reverse("reportes:dashboard")).status_code,302);self.assertEqual(self.client.get(reverse("reportes:finanzas")).status_code,200);self.assertEqual(self.client.get(reverse("reportes:alumnos")).status_code,403)
 def test_docente_solo_operativos(self):
  self.login(self.u["DOCENTE"]);self.assertEqual(self.client.get(reverse("reportes:asistencia")).status_code,200);self.assertEqual(self.client.get(reverse("reportes:finanzas")).status_code,403);self.assertEqual(self.client.get(reverse("reportes:docentes")).status_code,403)
 def test_smoke_director(self):
  self.login()
  for name in ("dashboard","alumnos","academico","asistencia","calificaciones","docentes","tareas","finanzas","comunicacion"):self.assertEqual(self.client.get(reverse("reportes:"+name)).status_code,200,name)
 def test_tenant_no_filtra_por_cliente(self):
  externo=Alumno.objects.create(institucion=self.b,primer_nombre="Externo",primer_apellido="B",fecha_nacimiento=date(2015,1,1),sexo="M",fecha_ingreso=date(2026,1,1));qs=salumnos.queryset(self.a,self.c,{});self.assertNotIn(externo,qs)
class DatosTests(ReporteBase):
 def test_alumnos_totales_y_filtros(self):
  qs=salumnos.queryset(self.a,self.c,{"grado":str(self.g.pk),"seccion":str(self.s.pk)});self.assertEqual(qs.count(),1);self.assertEqual(salumnos.estadisticas(self.a,qs)["activos"],1)
 def test_asistencia_solo_general_cerrada(self):
  sg=SesionAsistencia.objects.create(institucion=self.a,ciclo=self.c,fecha=date.today(),tipo="GENERAL",oferta_academica=self.o,grado=self.g,seccion=self.s,estado="CERRADA",creada_por=self.u["ADMINISTRADOR"]);RegistroAsistencia.objects.create(institucion=self.a,sesion=sg,alumno=self.al,inscripcion=self.ins,estado="PRESENTE",registrado_por=self.u["ADMINISTRADOR"]);sc=SesionAsistencia.objects.create(institucion=self.a,ciclo=self.c,fecha=date.today(),tipo="CURSO",oferta_academica=self.o,grado=self.g,seccion=self.s,curso=self.curso,estado="CERRADA",creada_por=self.u["ADMINISTRADOR"]);RegistroAsistencia.objects.create(institucion=self.a,sesion=sc,alumno=self.al,inscripcion=self.ins,estado="AUSENTE",registrado_por=self.u["ADMINISTRADOR"]);r=sasistencia.resumen(sasistencia.registros(self.a,self.c,{}));self.assertEqual(r["porcentaje"],100)
 def test_asistencia_anulada_excluida(self):
  s=SesionAsistencia.objects.create(institucion=self.a,ciclo=self.c,fecha=date.today(),tipo="GENERAL",oferta_academica=self.o,grado=self.g,seccion=self.s,estado="ANULADA",creada_por=self.u["ADMINISTRADOR"]);RegistroAsistencia.objects.create(institucion=self.a,sesion=s,alumno=self.al,inscripcion=self.ins,estado="AUSENTE",registrado_por=self.u["ADMINISTRADOR"]);self.assertEqual(sasistencia.registros(self.a,self.c,{}).count(),0)
 def test_finanzas_confirmados_y_anulados(self):
  metodo=MetodoPago.objects.create(institucion=self.a,codigo="E",nombre="Efectivo");Pago.objects.create(institucion=self.a,alumno=self.al,monto=Decimal("100"),metodo_pago=metodo,estado="CONFIRMADO",registrado_por=self.u["ADMINISTRADOR"]);Pago.objects.create(institucion=self.a,alumno=self.al,monto=Decimal("50"),metodo_pago=metodo,estado="ANULADO",registrado_por=self.u["ADMINISTRADOR"]);d=sfinanzas.datos(self.a,{});self.assertEqual(d["ingresos"],Decimal("100"));self.assertEqual(d["pagos_anulados"],1)
 def test_comunicacion_tasa_y_tenant(self):
  c=Comunicacion.objects.create(institucion=self.a,titulo="A",contenido="x",creada_por=self.director);Notificacion.objects.create(institucion=self.a,comunicacion=c,usuario=self.director,titulo="A",leida=True,origen_id=str(c.pk));rows=scom.datos(self.a);self.assertEqual(rows[0].tasa,100);self.assertEqual(len(rows),1)
class ExportTests(ReporteBase):
 def test_excel_alumnos_valido_y_encabezados(self):
  self.login();r=self.client.get(reverse("reportes:exportar_alumnos"),{"ciclo":self.c.pk,"seccion":self.s.pk});self.assertEqual(r.status_code,200);self.assertTrue(r.content.startswith(b"PK"));self.assertIn("aulapro_alumnos",r["Content-Disposition"])
 def test_excel_asistencia_valido(self):
  self.login();r=self.client.get(reverse("reportes:exportar_asistencia"),{"ciclo":self.c.pk});self.assertEqual(r.status_code,200);self.assertTrue(r.content.startswith(b"PK"))
 def test_excel_finanzas_permiso(self):
  self.login(self.u["CONTABILIDAD"]);r=self.client.get(reverse("reportes:exportar_finanzas"));self.assertEqual(r.status_code,200);self.assertTrue(r.content.startswith(b"PK"))
