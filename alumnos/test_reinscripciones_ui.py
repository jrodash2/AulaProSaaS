from django.urls import reverse
from .tests import Base

class ReinscripcionesUITests(Base):
 def test_admin_abre_selector(self):
  self.client.force_login(self.users["ADMINISTRADOR"]);self.assertEqual(self.client.get(reverse("alumnos:reinscripciones"),follow=True).status_code,200)
 def test_procesar_es_post(self):
  self.client.force_login(self.users["ADMINISTRADOR"]);self.assertEqual(self.client.get(reverse("alumnos:reinscripciones_procesar",args=[self.ca.pk])).status_code,405)
 def test_no_acepta_ciclo_otro_tenant(self):
  self.client.force_login(self.users["ADMINISTRADOR"]);self.assertEqual(self.client.get(reverse("alumnos:reinscripciones_detalle",args=[self.cb.pk])).status_code,404)
