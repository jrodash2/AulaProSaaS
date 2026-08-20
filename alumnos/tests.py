from datetime import date
from io import BytesIO
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook
from academico.models import CicloEscolar,GradoInstitucion,OfertaAcademica,Seccion
from catalogos.models import NivelEducativo
from instituciones.models import Institucion,UsuarioInstitucion
from .models import Alumno,AlumnoEncargado,Encargado,Familia,ImportacionAlumnos,Inscripcion
from .services import HEADERS,ejecutar_importacion,prevalidar

class Base(TestCase):
 def setUp(self):
  self.a=Institucion.objects.create(nombre="A",codigo="AL-A"); self.b=Institucion.objects.create(nombre="B",codigo="AL-B")
  self.users={}
  for rol in ("ADMINISTRADOR","DIRECTOR","SECRETARIA","DOCENTE","CONTABILIDAD"):
   u=get_user_model().objects.create_user(username=rol.lower(),password="segura-123"); UsuarioInstitucion.objects.create(usuario=u,institucion=self.a,rol=rol); self.users[rol]=u
  self.ca=CicloEscolar.objects.create(institucion=self.a,nombre="2027",anio=2027,fecha_inicio=date(2027,1,1),fecha_fin=date(2027,11,1),es_actual=True); self.cb=CicloEscolar.objects.create(institucion=self.b,nombre="2027 B",anio=2027,fecha_inicio=date(2027,1,1),fecha_fin=date(2027,11,1))
  n=NivelEducativo.objects.create(codigo="N-AL",nombre="Básicos"); self.oa=OfertaAcademica.objects.create(institucion=self.a,ciclo=self.ca,nivel=n,nombre_mostrado="Básicos",codigo_interno="BAS",origen="PERSONALIZADA"); self.ob=OfertaAcademica.objects.create(institucion=self.b,ciclo=self.cb,nivel=n,nombre_mostrado="B B",codigo_interno="BAS",origen="PERSONALIZADA")
  self.ga=GradoInstitucion.objects.create(institucion=self.a,ciclo=self.ca,oferta=self.oa,codigo="G1",nombre="Primero"); self.gb=GradoInstitucion.objects.create(institucion=self.b,ciclo=self.cb,oferta=self.ob,codigo="G1",nombre="Primero")
  self.sa=Seccion.objects.create(institucion=self.a,ciclo=self.ca,grado=self.ga,codigo="A",nombre="A"); self.sb=Seccion.objects.create(institucion=self.b,ciclo=self.cb,grado=self.gb,codigo="A",nombre="A")
 def alumno(self,inst=None,cui="1234567890123",nombre="Ana"):
  return Alumno.objects.create(institucion=inst or self.a,cui=cui,primer_nombre=nombre,primer_apellido="López",fecha_nacimiento=date(2015,1,1),sexo="F",fecha_ingreso=date(2027,1,1))
 def inscribir(self,a=None,ciclo=None,oferta=None,grado=None,seccion=None):
  return Inscripcion.objects.create(institucion=(a or self.alumno()).institucion,alumno=a or self.alumno(),ciclo=ciclo or self.ca,oferta_academica=oferta or self.oa,grado=grado or self.ga,seccion=seccion or self.sa,fecha_inscripcion=date(2027,1,2))
 def xlsx(self,rows):
  wb=Workbook(); ws=wb.active; ws.title="ESTUDIANTES"; ws.append(HEADERS)
  for r in rows: ws.append([r.get(h) for h in HEADERS])
  out=BytesIO(); wb.save(out); out.seek(0); out.name="test.xlsx"; return out
 def row(self,cui="9999999999999",grado="G1",seccion="A"):
  return {"CUI":cui,"PRIMER_NOMBRE":"Juan","PRIMER_APELLIDO":"Pérez","FECHA_NACIMIENTO":date(2015,2,1),"SEXO":"M","CODIGO_OFERTA":"BAS","CODIGO_GRADO":grado,"CODIGO_SECCION":seccion}

class AlumnoTests(Base):
 def test_cui_opcional_marca_identificacion_pendiente(self):
  a=self.alumno(cui=None); self.assertEqual(a.estado_identificacion,"PENDIENTE")
 def test_codigo_familia_legible_y_unico(self):
  a=Familia.objects.create(institucion=self.a,nombre_referencia="A"); b=Familia.objects.create(institucion=self.a,nombre_referencia="B"); self.assertRegex(a.codigo,r"^FAM-\d{6}$"); self.assertNotEqual(a.codigo,b.codigo)
 def test_cui_unico_por_institucion(self):
  self.alumno()
  with self.assertRaises(ValidationError): self.alumno(nombre="Otra")
 def test_mismo_cui_en_otra_institucion(self): self.alumno(); self.assertEqual(self.alumno(self.b).institucion,self.b)
 def test_nombre_completo(self):
  a=Alumno(institucion=self.a,primer_nombre="Juan",segundo_nombre="Carlos",primer_apellido="Pérez",segundo_apellido="López",fecha_nacimiento=date.today(),sexo="M",fecha_ingreso=date.today()); self.assertEqual(a.nombre_completo,"Juan Carlos Pérez López")
 def test_alumno_multiples_encargados(self):
  a=self.alumno(); e1=Encargado.objects.create(institucion=self.a,nombres="M",apellidos="L",telefono="1"); e2=Encargado.objects.create(institucion=self.a,nombres="P",apellidos="L",telefono="2"); AlumnoEncargado.objects.create(institucion=self.a,alumno=a,encargado=e1,parentesco="MADRE"); AlumnoEncargado.objects.create(institucion=self.a,alumno=a,encargado=e2,parentesco="PADRE"); self.assertEqual(a.vinculos_encargados.count(),2)
 def test_familia_multiples_alumnos(self):
  f=Familia.objects.create(institucion=self.a,nombre_referencia="Familia"); self.alumno(cui="1111111111111").familia_id
  a1=self.alumno(cui="2222222222222"); a1.familia=f; a1.save(); a2=self.alumno(cui="3333333333333"); a2.familia=f;a2.save();self.assertEqual(f.alumnos.count(),2)
 def test_tenant_no_lista_ni_edita_otro(self):
  otro=self.alumno(self.b); self.client.force_login(self.users["ADMINISTRADOR"]); self.assertNotContains(self.client.get(reverse("alumnos:lista")),otro.nombre_completo); self.assertEqual(self.client.get(reverse("alumnos:editar",args=[otro.pk])).status_code,404)
 def test_endpoint_cui_no_revela_otro_tenant(self):
  self.alumno(self.b); self.client.force_login(self.users["ADMINISTRADOR"]); self.assertTrue(self.client.get(reverse("alumnos:cui_disponible"),{"cui":"1234567890123"}).json()["disponible"])
 def test_detalle_otro_tenant_es_404(self):
  otro=self.alumno(self.b); self.client.force_login(self.users["ADMINISTRADOR"]); self.assertEqual(self.client.get(reverse("alumnos:detalle",args=[otro.pk])).status_code,404)
 def test_opciones_academicas_no_exponen_otro_tenant(self):
  self.client.force_login(self.users["ADMINISTRADOR"]); datos=self.client.get(reverse("alumnos:opciones_inscripcion"),{"ciclo":self.cb.pk}).json(); self.assertEqual(datos["resultados"],[])

class InscripcionTests(Base):
 def test_rechaza_ciclo_otra_institucion(self):
  with self.assertRaises(ValidationError): self.inscribir(self.alumno(),self.cb,self.oa,self.ga,self.sa)
 def test_rechaza_grado_otra_oferta(self):
  with self.assertRaises(ValidationError): self.inscribir(self.alumno(),self.ca,self.oa,self.gb,self.sa)
 def test_rechaza_seccion_otro_grado(self):
  with self.assertRaises(ValidationError): self.inscribir(self.alumno(),self.ca,self.oa,self.ga,self.sb)
 def test_rechaza_alumno_otro_tenant(self):
  with self.assertRaises(ValidationError): Inscripcion.objects.create(institucion=self.a,alumno=self.alumno(self.b),ciclo=self.ca,oferta_academica=self.oa,grado=self.ga,seccion=self.sa,fecha_inscripcion=date.today())
 def test_historial_conserva_ciclos(self):
  a=self.alumno(); i=self.inscribir(a); i.estado="FINALIZADA"; i.save(); c2=CicloEscolar.objects.create(institucion=self.a,nombre="2028",anio=2028,fecha_inicio=date(2028,1,1),fecha_fin=date(2028,11,1)); o2=OfertaAcademica.objects.create(institucion=self.a,ciclo=c2,nivel=self.oa.nivel,nombre_mostrado="B",codigo_interno="B2",origen="PERSONALIZADA"); g2=GradoInstitucion.objects.create(institucion=self.a,ciclo=c2,oferta=o2,codigo="G2",nombre="Segundo"); s2=Seccion.objects.create(institucion=self.a,ciclo=c2,grado=g2,codigo="A",nombre="A"); self.inscribir(a,c2,o2,g2,s2); self.assertEqual(a.inscripciones.count(),2)
 def test_retirar_no_elimina_alumno(self):
  a=self.alumno(); i=self.inscribir(a); self.client.force_login(self.users["ADMINISTRADOR"]); self.client.post(reverse("alumnos:retirar",args=[i.pk]),{"fecha_retiro":"2027-03-01","motivo_retiro":"Traslado"}); self.assertTrue(Alumno.objects.filter(pk=a.pk).exists()); i.refresh_from_db(); self.assertEqual(i.estado,"RETIRADA")

class ImportacionTests(Base):
 def test_importacion_rechaza_ciclo_otro_tenant(self):
  with self.assertRaises(ValidationError): ImportacionAlumnos.objects.create(institucion=self.a,usuario=self.users["ADMINISTRADOR"],ciclo=self.cb,nombre_archivo="x.xlsx")
 def test_cui_nuevo_prevalida(self): self.assertFalse(prevalidar(self.xlsx([self.row()]),self.a,self.ca)["errores"])
 def test_cui_duplicado_archivo_error(self): self.assertTrue(prevalidar(self.xlsx([self.row(),self.row()]),self.a,self.ca)["errores"])
 def test_grado_inexistente_error(self): self.assertTrue(prevalidar(self.xlsx([self.row(grado="X")]),self.a,self.ca)["errores"])
 def test_seccion_otra_institucion_no_accesible(self): self.assertTrue(prevalidar(self.xlsx([self.row(seccion="B")]),self.a,self.ca)["errores"])
 def test_error_evade_importacion_parcial(self):
  f=self.xlsx([self.row(),self.row(grado="X",cui="8888888888888")]); reg=ImportacionAlumnos.objects.create(institucion=self.a,usuario=self.users["ADMINISTRADOR"],ciclo=self.ca,archivo_original=f,nombre_archivo="x.xlsx")
  with self.assertRaises(ValidationError): ejecutar_importacion(reg)
  self.assertEqual(Alumno.objects.count(),0)
 def test_valida_importacion_crea_y_reutiliza(self):
  existente=self.alumno(cui="7777777777777",nombre="Juan"); f=self.xlsx([self.row(cui="7777777777777")]); reg=ImportacionAlumnos.objects.create(institucion=self.a,usuario=self.users["ADMINISTRADOR"],ciclo=self.ca,archivo_original=f,nombre_archivo="x.xlsx"); ejecutar_importacion(reg); self.assertEqual(Alumno.objects.filter(cui="7777777777777").count(),1); self.assertEqual(existente.inscripciones.count(),1)
 def test_encargado_existente_reutilizado(self):
  Encargado.objects.create(institucion=self.a,cui="6666666666666",nombres="Madre",apellidos="P",telefono="1"); r=self.row(); r.update({"CUI_ENCARGADO":"6666666666666","NOMBRES_ENCARGADO":"Madre","APELLIDOS_ENCARGADO":"P","TELEFONO_ENCARGADO":"1","PARENTESCO":"MADRE"}); f=self.xlsx([r]); reg=ImportacionAlumnos.objects.create(institucion=self.a,usuario=self.users["ADMINISTRADOR"],ciclo=self.ca,archivo_original=f,nombre_archivo="x.xlsx"); ejecutar_importacion(reg); self.assertEqual(Encargado.objects.filter(cui="6666666666666").count(),1)

class PermisosTests(Base):
 def _status(self,rol): self.client.force_login(self.users[rol]); return self.client.get(reverse("alumnos:crear")).status_code
 def test_administrador_puede_crear(self): self.assertEqual(self._status("ADMINISTRADOR"),200)
 def test_director_puede_crear(self): self.assertEqual(self._status("DIRECTOR"),200)
 def test_secretaria_puede_crear(self): self.assertEqual(self._status("SECRETARIA"),200)
 def test_docente_no_modifica(self): self.assertEqual(self._status("DOCENTE"),403)
 def test_contabilidad_no_modifica(self): self.assertEqual(self._status("CONTABILIDAD"),403)
