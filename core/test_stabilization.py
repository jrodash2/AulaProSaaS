from django.core.management import call_command,CommandError
from django.test import Client,RequestFactory,TestCase,override_settings
from django.urls import reverse
from tareas.tests import Base
from core import views
class HealthAndErrorsTests(TestCase):
 def test_health_publico_sin_secretos(self):
  r=self.client.get("/health/");self.assertEqual(r.status_code,200);self.assertEqual(r.json()["status"],"ok");self.assertNotIn("SECRET_KEY",r.content.decode());self.assertNotIn("database",r.content.decode().lower())
 def test_health_db(self):self.assertEqual(self.client.get("/health/db/").status_code,200)
 @override_settings(DEBUG=False)
 def test_paginas_error_profesionales(self):
  self.assertContains(self.client.get("/ruta-inexistente-sprint13/"),"No encontramos esta página",status_code=404);request=RequestFactory().get("/");request.user=__import__("django.contrib.auth.models",fromlist=["AnonymousUser"]).AnonymousUser();r=views.error_500(request);self.assertEqual(r.status_code,500);self.assertNotIn(b"Traceback",r.content)
 @override_settings(DEBUG=False)
 def test_demo_bloqueado_en_produccion(self):
  with self.assertRaises(CommandError):call_command("crear_demo_aulapro")
class MetodosYRolesTests(Base):
 def test_get_acciones_criticas_devuelve_405(self):
  self.client.force_login(self.u["ADMINISTRADOR"])
  urls=(reverse("academico:ciclo_actual",args=[self.c.pk]),reverse("academico:seccion_estado",args=[self.s.pk]),reverse("docentes:asignacion_estado",args=[self.asig.pk]))
  for url in urls:self.assertEqual(self.client.get(url).status_code,405,url)
 def test_portal_no_abre_modulos_administrativos(self):
  from alumnos.models import Encargado,AlumnoEncargado
  from instituciones.models import UsuarioInstitucion
  from django.contrib.auth import get_user_model
  padre=get_user_model().objects.create_user("qa_padre",password="x");UsuarioInstitucion.objects.create(usuario=padre,institucion=self.a,rol="PADRE");e=Encargado.objects.create(institucion=self.a,usuario=padre,nombres="QA",apellidos="Padre",telefono="1");AlumnoEncargado.objects.create(institucion=self.a,encargado=e,alumno=self.al,parentesco="PADRE");self.client.force_login(padre)
  for name in ("asistencia:dashboard","calificaciones:dashboard","tareas:dashboard","reportes:dashboard"):self.assertEqual(self.client.get(reverse(name)).status_code,403,name)
 def test_contabilidad_no_abre_academico(self):
  self.client.force_login(self.u["CONTABILIDAD"])
  for name in ("asistencia:dashboard","calificaciones:dashboard","tareas:dashboard","docentes:lista"):self.assertEqual(self.client.get(reverse(name)).status_code,403,name)
 def test_csrf_protege_cambio_estado(self):
  client=Client(enforce_csrf_checks=True);client.force_login(self.u["ADMINISTRADOR"]);self.assertEqual(client.post(reverse("academico:ciclo_actual",args=[self.c.pk])).status_code,403)
