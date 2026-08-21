from datetime import date
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from academico.models import CicloEscolar,CursoInstitucion,GradoInstitucion,OfertaAcademica,Seccion
from alumnos.models import Alumno,Inscripcion
from catalogos.models import NivelEducativo
from instituciones.models import Institucion,UsuarioInstitucion
from .models import AsignacionDocente,AsignacionGuia,Docente
from .services import crear_acceso_docente

class Base(TestCase):
 def setUp(self):
  self.a=Institucion.objects.create(nombre="A",codigo="DOC-A"); self.b=Institucion.objects.create(nombre="B",codigo="DOC-B")
  self.admin=get_user_model().objects.create_user(username="admin-doc",password="segura-123"); UsuarioInstitucion.objects.create(usuario=self.admin,institucion=self.a,rol="ADMINISTRADOR")
  self.ua=get_user_model().objects.create_user(username="prof-a",password="segura-123"); UsuarioInstitucion.objects.create(usuario=self.ua,institucion=self.a,rol="DOCENTE")
  self.ub=get_user_model().objects.create_user(username="prof-b",password="segura-123"); UsuarioInstitucion.objects.create(usuario=self.ub,institucion=self.b,rol="DOCENTE")
  self.ca=CicloEscolar.objects.create(institucion=self.a,nombre="2027",anio=2027,fecha_inicio=date(2027,1,1),fecha_fin=date(2027,11,1),es_actual=True); self.cb=CicloEscolar.objects.create(institucion=self.b,nombre="2027 B",anio=2027,fecha_inicio=date(2027,1,1),fecha_fin=date(2027,11,1))
  nivel=NivelEducativo.objects.create(codigo="N-DOC",nombre="Básicos")
  self.oa=OfertaAcademica.objects.create(institucion=self.a,ciclo=self.ca,nivel=nivel,nombre_mostrado="Básicos",codigo_interno="BAS",origen="PERSONALIZADA"); self.ob=OfertaAcademica.objects.create(institucion=self.b,ciclo=self.cb,nivel=nivel,nombre_mostrado="B",codigo_interno="B",origen="PERSONALIZADA")
  self.ga=GradoInstitucion.objects.create(institucion=self.a,ciclo=self.ca,oferta=self.oa,codigo="G1",nombre="Primero"); self.gb=GradoInstitucion.objects.create(institucion=self.b,ciclo=self.cb,oferta=self.ob,codigo="G1",nombre="Primero")
  self.sa=Seccion.objects.create(institucion=self.a,ciclo=self.ca,grado=self.ga,codigo="A",nombre="A"); self.sa2=Seccion.objects.create(institucion=self.a,ciclo=self.ca,grado=self.ga,codigo="B",nombre="B"); self.sb=Seccion.objects.create(institucion=self.b,ciclo=self.cb,grado=self.gb,codigo="A",nombre="A")
  self.curso=CursoInstitucion.objects.create(institucion=self.a,ciclo=self.ca,oferta=self.oa,grado=self.ga,nombre_personalizado="Matemática",origen="INSTITUCIONAL",periodos_semanales=5); self.curso2=CursoInstitucion.objects.create(institucion=self.a,ciclo=self.ca,oferta=self.oa,grado=self.ga,nombre_personalizado="Ciencias",origen="INSTITUCIONAL",periodos_semanales=4); self.curso_b=CursoInstitucion.objects.create(institucion=self.b,ciclo=self.cb,oferta=self.ob,grado=self.gb,nombre_personalizado="Mate B",origen="INSTITUCIONAL")
  self.da=Docente.objects.create(institucion=self.a,usuario=self.ua,cui="1111111111111",primer_nombre="Juan",primer_apellido="Pérez",telefono="1",fecha_ingreso=date(2027,1,1)); self.db=Docente.objects.create(institucion=self.b,usuario=self.ub,cui="1111111111111",primer_nombre="María",primer_apellido="López",telefono="2",fecha_ingreso=date(2027,1,1))
 def docente(self,**kw):
  data={"institucion":self.a,"primer_nombre":"Carlos","primer_apellido":"García","telefono":"3","fecha_ingreso":date(2027,1,1)}; data.update(kw); return Docente.objects.create(**data)
 def asignar(self,docente=None,seccion=None,curso=None,**kw):
  data={"institucion":self.a,"ciclo":self.ca,"docente":docente or self.da,"oferta_academica":self.oa,"grado":self.ga,"seccion":seccion or self.sa,"curso":curso or self.curso,"fecha_inicio":date(2027,1,1)}; data.update(kw); return AsignacionDocente.objects.create(**data)

class DocenteTests(Base):
 def test_codigo_unico(self):
  d=self.docente(); x=self.docente(); self.assertNotEqual(d.codigo,x.codigo)
 def test_cui_unico_institucion(self):
  with self.assertRaises(ValidationError): self.docente(cui=self.da.cui)
 def test_cui_mismo_otro_tenant(self): self.assertEqual(self.db.cui,self.da.cui)
 def test_usuario_debe_pertenecer_institucion(self):
  with self.assertRaises(ValidationError): self.docente(usuario=self.ub)
 def test_docente_sin_usuario_valido(self): self.assertIsNone(self.docente().usuario)
 def test_nombre_completo(self): self.assertEqual(self.da.nombre_completo,"Juan Pérez")
 def test_docente_b_no_visible_a(self):
  self.client.force_login(self.admin); self.assertNotContains(self.client.get(reverse("docentes:lista")),self.db.nombre_completo)
 def test_editar_pk_externo_404(self):
  self.client.force_login(self.admin); self.assertEqual(self.client.get(reverse("docentes:editar",args=[self.db.pk])).status_code,404)
 def test_crear_acceso_rol_docente(self):
  d=self.docente(); u=crear_acceso_docente(d,{"username":"nuevo-prof","email":"p@x.com","password":"Una-clave-segura-2027"}); self.assertTrue(UsuarioInstitucion.objects.filter(usuario=u,institucion=self.a,rol="DOCENTE").exists())

class AsignacionTests(Base):
 def test_detalle_asignacion_y_aislamiento(self):
  propia=self.asignar(); ajena=AsignacionDocente.objects.create(institucion=self.b,ciclo=self.cb,docente=self.db,oferta_academica=self.ob,grado=self.gb,seccion=self.sb,curso=self.curso_b,fecha_inicio=date(2027,1,1)); self.client.force_login(self.admin); self.assertEqual(self.client.get(reverse("docentes:asignacion_detalle",args=[propia.pk])).status_code,200); self.assertEqual(self.client.get(reverse("docentes:asignacion_detalle",args=[ajena.pk])).status_code,404)
 def test_docente_misma_institucion(self):
  with self.assertRaises(ValidationError): self.asignar(docente=self.db)
 def test_ciclo_misma_institucion(self):
  with self.assertRaises(ValidationError): self.asignar(ciclo=self.cb)
 def test_grado_oferta_consistente(self):
  with self.assertRaises(ValidationError): self.asignar(grado=self.gb)
 def test_seccion_pertenece_grado(self):
  with self.assertRaises(ValidationError): self.asignar(seccion=self.sb)
 def test_curso_pertenece_grado(self):
  with self.assertRaises(ValidationError): self.asignar(curso=self.curso_b)
 def test_duplicado_exacto_rechazado(self):
  self.asignar()
  with self.assertRaises(ValidationError): self.asignar(es_titular=False)
 def test_multiples_asignaciones_distintas(self): self.asignar(); self.asignar(seccion=self.sa2); self.assertEqual(self.da.asignaciones.count(),2)
 def test_multiples_docentes_auxiliares(self):
  self.asignar(); otro=self.docente(); self.asignar(docente=otro,es_titular=False); self.assertEqual(self.curso.asignaciones_docentes.count(),2)
 def test_unico_titular(self):
  self.asignar(); otro=self.docente()
  with self.assertRaises(ValidationError): self.asignar(docente=otro)
 def test_historial_permanece_inactivo(self):
  a=self.asignar(); a.activa=False;a.fecha_fin=date(2027,5,1);a.save();self.assertTrue(AsignacionDocente.objects.filter(pk=a.pk).exists())
 def test_fechas_invalidas(self):
  with self.assertRaises(ValidationError): self.asignar(fecha_inicio=date(2027,2,1),fecha_fin=date(2027,1,1))
 def test_asignaciones_b_no_visibles_a(self):
  AsignacionDocente.objects.create(institucion=self.b,ciclo=self.cb,docente=self.db,oferta_academica=self.ob,grado=self.gb,seccion=self.sb,curso=self.curso_b,fecha_inicio=date(2027,1,1)); self.client.force_login(self.admin); self.assertNotContains(self.client.get(reverse("docentes:asignaciones")),self.db.nombre_completo)

class GuiaPortalTests(Base):
 def test_sidebar_docente_no_muestra_administracion(self):
  self.client.force_login(self.ua); response=self.client.get(reverse("core:institucion_dashboard")); self.assertContains(response,"Mis clases"); self.assertNotContains(response,"Configuración</span>"); self.assertNotContains(response,"Usuarios</span>")
 def test_guia_misma_institucion(self): AsignacionGuia.objects.create(institucion=self.a,ciclo=self.ca,seccion=self.sa,docente=self.da,fecha_inicio=date(2027,1,1))
 def test_guia_externo_rechazado(self):
  with self.assertRaises(ValidationError): AsignacionGuia.objects.create(institucion=self.a,ciclo=self.ca,seccion=self.sa,docente=self.db,fecha_inicio=date(2027,1,1))
 def test_seccion_externa_rechazada(self):
  with self.assertRaises(ValidationError): AsignacionGuia.objects.create(institucion=self.a,ciclo=self.ca,seccion=self.sb,docente=self.da,fecha_inicio=date(2027,1,1))
 def test_docente_ve_sus_clases(self):
  a=self.asignar(); self.client.force_login(self.ua); self.assertContains(self.client.get(reverse("docentes:mis_clases")),a.curso.nombre)
 def test_docente_no_ve_clase_ajena(self):
  otro=self.docente(); a=self.asignar(docente=otro); self.client.force_login(self.ua); self.assertNotContains(self.client.get(reverse("docentes:mis_clases")),a.curso.nombre)
 def test_docente_no_configuracion(self): self.client.force_login(self.ua); self.assertEqual(self.client.get(reverse("instituciones:configuracion")).status_code,403)
 def test_docente_no_usuarios(self): self.client.force_login(self.ua); self.assertEqual(self.client.get(reverse("instituciones:usuarios")).status_code,403)
 def test_docente_ve_estudiantes_seccion(self):
  a=self.asignar(); alumno=Alumno.objects.create(institucion=self.a,cui="2222222222222",primer_nombre="Ana",primer_apellido="L",fecha_nacimiento=date(2015,1,1),sexo="F",fecha_ingreso=date(2027,1,1)); Inscripcion.objects.create(institucion=self.a,alumno=alumno,ciclo=self.ca,oferta_academica=self.oa,grado=self.ga,seccion=self.sa,fecha_inscripcion=date(2027,1,1)); self.client.force_login(self.ua); self.assertContains(self.client.get(reverse("docentes:mi_clase",args=[a.pk])),alumno.nombre_completo)
 def test_docente_no_abre_clase_ajena(self):
  otro=self.docente(); a=self.asignar(docente=otro); self.client.force_login(self.ua); self.assertEqual(self.client.get(reverse("docentes:mi_clase",args=[a.pk])).status_code,404)
