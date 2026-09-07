from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from pathlib import Path

from .tests import AcademicoBase


class ModalGlobalHotfixTests(AcademicoBase):
    def setUp(self):
        super().setUp()
        self.oferta = self.crear_oferta()
        self.curso = self.oferta.cursos.first()
        self.client.force_login(self.admin)

    def test_modal_global_es_hijo_externo_al_shell_animado(self):
        response = self.client.get(reverse("academico:oferta_detalle", args=[self.oferta.pk]))
        html = response.content.decode()
        self.assertEqual(html.count('id="confirmModal"'), 1)
        self.assertGreater(html.index('id="confirmModal"'), html.index('</div>\n  <div class="sidebar-backdrop"'))
        self.assertGreater(html.index('id="confirmModal"'), html.index('</main>'))

    def test_trigger_curso_incluye_url_copy_boton_y_accesibilidad(self):
        response = self.client.get(reverse("academico:oferta_detalle", args=[self.oferta.pk]))
        self.assertContains(response, f'data-confirm-url="{reverse("academico:curso_estado", args=[self.curso.pk])}"')
        self.assertContains(response, 'data-confirm-copy=')
        self.assertContains(response, 'data-confirm-button=')
        self.assertContains(response, 'aria-label="Desactivar')
        self.assertContains(response, 'bi-toggle-on')

    def test_oferta_tambien_renderiza_metadatos_completos(self):
        response = self.client.get(reverse("academico:oferta_detalle", args=[self.oferta.pk]))
        self.assertContains(response, f'data-confirm-url="{reverse("academico:oferta_estado", args=[self.oferta.pk])}"')
        for atributo in ("data-confirm-title", "data-confirm-copy", "data-confirm-button", "data-confirm-variant"):
            self.assertContains(response, atributo)

    def test_endpoint_estado_curso_requiere_post(self):
        self.assertEqual(self.client.get(reverse("academico:curso_estado", args=[self.curso.pk])).status_code, 405)

    def test_formulario_modal_tiene_csrf_y_submit_explicito(self):
        response = self.client.get(reverse("academico:oferta_detalle", args=[self.oferta.pk]))
        self.assertContains(response, 'id="confirmModalForm"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'type="submit" class="btn btn-danger" id="confirmModalSubmit"')

    def test_javascript_inicializa_modal_y_usa_atributos_html(self):
        javascript = (Path(settings.BASE_DIR) / "static/js/aulapro.js").read_text()
        self.assertIn("function initConfirmModal()", javascript)
        self.assertIn('getAttribute("data-confirm-url")', javascript)
        self.assertIn('getAttribute("data-confirm-button")', javascript)
        self.assertEqual(javascript.count('addEventListener("show.bs.modal"'), 1)

    def test_assets_llevan_version_para_invalidar_cache(self):
        response = self.client.get(reverse("academico:oferta_detalle", args=[self.oferta.pk]))
        self.assertContains(response, f"aulapro.js?v={settings.STATIC_ASSET_VERSION}")
        self.assertContains(response, f"aulapro.css?v={settings.STATIC_ASSET_VERSION}")

    def test_confirmacion_post_cambia_estado_del_curso(self):
        self.assertTrue(self.curso.activo)
        response = self.client.post(reverse("academico:curso_estado", args=[self.curso.pk]))
        self.assertEqual(response.status_code, 302)
        self.curso.refresh_from_db()
        self.assertFalse(self.curso.activo)
