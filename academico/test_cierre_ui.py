from django.test import TestCase
from django.urls import reverse

from .models import CicloEscolar
from .tests import AcademicoBase


class CierreUITests(AcademicoBase):
    def test_director_abre_asistente_y_resultados(self):
        self.client.force_login(self.director)
        self.assertEqual(self.client.get(reverse("academico:ciclo_cierre", args=[self.ciclo_a.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("academico:resultados_anuales", args=[self.ciclo_a.pk])).status_code, 200)

    def test_acciones_mutables_solo_aceptan_post(self):
        self.client.force_login(self.director)
        for nombre in ("ciclo_iniciar_cierre", "resultados_generar", "resultados_confirmar_sugerencias", "ciclo_cerrar"):
            self.assertEqual(self.client.get(reverse(f"academico:{nombre}", args=[self.ciclo_a.pk])).status_code, 405)

    def test_contabilidad_no_accede_al_cierre(self):
        self.client.force_login(self.contabilidad)
        self.assertEqual(self.client.get(reverse("academico:ciclo_cierre", args=[self.ciclo_a.pk])).status_code, 403)

    def test_tenant_no_accede_ciclo_externo(self):
        self.client.force_login(self.director)
        self.assertEqual(self.client.get(reverse("academico:ciclo_cierre", args=[self.ciclo_b.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("academico:ciclo_cerrar", args=[self.ciclo_b.pk])).status_code, 404)

    def test_iniciar_cierre_cambia_estado(self):
        self.client.force_login(self.director)
        response=self.client.post(reverse("academico:ciclo_iniciar_cierre", args=[self.ciclo_a.pk]))
        self.assertEqual(response.status_code,302);self.ciclo_a.refresh_from_db();self.assertEqual(self.ciclo_a.estado,CicloEscolar.Estado.EN_CIERRE)

    def test_detalle_muestra_progreso(self):
        self.client.force_login(self.admin)
        response=self.client.get(reverse("academico:ciclo_detalle",args=[self.ciclo_a.pk]))
        self.assertContains(response,"Resultados generados")
