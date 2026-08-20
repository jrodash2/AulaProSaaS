from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from instituciones.models import Institucion, UsuarioInstitucion


class SeguridadMultiinstitucionTests(TestCase):
    def setUp(self):
        self.institucion_a = Institucion.objects.create(nombre="Colegio A", codigo="A")
        self.institucion_b = Institucion.objects.create(nombre="Colegio B", codigo="B")
        self.usuario_a = get_user_model().objects.create_user(username="admina", password="segura-123")
        self.usuario_b = get_user_model().objects.create_user(username="adminb", password="segura-123")
        self.asignacion_a = UsuarioInstitucion.objects.create(
            usuario=self.usuario_a, institucion=self.institucion_a,
            rol=UsuarioInstitucion.Rol.ADMINISTRADOR,
        )
        self.asignacion_b = UsuarioInstitucion.objects.create(
            usuario=self.usuario_b, institucion=self.institucion_b,
            rol=UsuarioInstitucion.Rol.ADMINISTRADOR,
        )

    def test_usuario_normal_no_accede_area_global(self):
        self.client.force_login(self.usuario_a)
        response = self.client.get(reverse("core:global_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_usuario_a_no_puede_forzar_institucion_b(self):
        self.client.force_login(self.usuario_a)
        session = self.client.session
        session["asignacion_institucion_id"] = self.asignacion_b.pk
        session.save()
        response = self.client.get(reverse("instituciones:configuracion"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].instance, self.institucion_a)
        self.assertNotContains(response, self.institucion_b.nombre)

    def test_asignacion_duplicada_no_es_permitida(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            UsuarioInstitucion.objects.create(
                usuario=self.usuario_a, institucion=self.institucion_a,
                rol=UsuarioInstitucion.Rol.DIRECTOR,
            )

    def test_usuario_no_autenticado_es_redirigido_al_login(self):
        response = self.client.get(reverse("core:institucion_dashboard"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('core:institucion_dashboard')}",
        )

    def test_superusuario_accede_panel_global(self):
        superusuario = get_user_model().objects.create_superuser(
            username="root", email="root@example.com", password="segura-123",
        )
        self.client.force_login(superusuario)
        response = self.client.get(reverse("core:global_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_instituciones"], 2)

    def test_actualizacion_respeta_institucion_activa(self):
        self.client.force_login(self.usuario_a)
        response = self.client.post(
            reverse("instituciones:configuracion"),
            {"nombre": "Colegio A actualizado", "nombre_corto": "A", "direccion": "Zona 1", "departamento": "Guatemala", "municipio": "Guatemala", "telefono": "", "email": "", "sitio_web": "", "color_primario": "#1F4E5F", "color_secundario": "#3B8C88"},
        )
        self.assertRedirects(response, reverse("instituciones:configuracion"))
        self.institucion_a.refresh_from_db()
        self.institucion_b.refresh_from_db()
        self.assertEqual(self.institucion_a.nombre, "Colegio A actualizado")
        self.assertEqual(self.institucion_b.nombre, "Colegio B")
        self.assertEqual(self.institucion_a.eventos_auditoria.count(), 1)
