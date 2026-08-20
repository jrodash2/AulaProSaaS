from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from pathlib import Path

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

    def test_usuario_solamente_visualiza_usuarios_de_su_institucion(self):
        self.client.force_login(self.usuario_a)
        response = self.client.get(reverse("instituciones:usuarios"))
        self.assertContains(response, self.usuario_a.username)
        self.assertNotContains(response, self.usuario_b.username)

    def test_detalle_y_edicion_de_usuario_externo_son_404(self):
        self.client.force_login(self.usuario_a)
        self.assertEqual(self.client.get(reverse("instituciones:usuario_detalle", args=[self.asignacion_b.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("instituciones:usuario_editar", args=[self.asignacion_b.pk]), {}).status_code, 404)

    def test_nuevo_usuario_solo_se_asocia_a_institucion_activa(self):
        self.client.force_login(self.usuario_a)
        response = self.client.post(reverse("instituciones:usuario_crear"), {
            "first_name": "Nueva", "last_name": "Persona", "username": "nueva",
            "email": "nueva@example.com", "rol": UsuarioInstitucion.Rol.DOCENTE,
            "password1": "Una-clave-segura-2026", "password2": "Una-clave-segura-2026",
        })
        self.assertEqual(response.status_code, 302)
        nueva = UsuarioInstitucion.objects.get(usuario__username="nueva")
        self.assertEqual(nueva.institucion, self.institucion_a)

    def test_cambio_institucion_rechaza_asignacion_ajena(self):
        self.client.force_login(self.usuario_a)
        response = self.client.post(reverse("core:cambiar_institucion", args=[self.asignacion_b.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(self.client.session.get("asignacion_institucion_id"), self.asignacion_b.pk)

    def test_cambio_institucion_permite_asignacion_propia_activa(self):
        otra = UsuarioInstitucion.objects.create(usuario=self.usuario_a, institucion=self.institucion_b, rol=UsuarioInstitucion.Rol.DIRECTOR)
        self.client.force_login(self.usuario_a)
        response = self.client.post(reverse("core:cambiar_institucion", args=[otra.pk]))
        self.assertRedirects(response, reverse("core:institucion_dashboard"))
        self.assertEqual(self.client.session["asignacion_institucion_id"], otra.pk)

    def test_superusuario_lista_instituciones(self):
        superusuario = get_user_model().objects.create_superuser(username="global", password="segura-123")
        self.client.force_login(superusuario)
        response = self.client.get(reverse("instituciones:lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.institucion_a.nombre)

    def test_administrador_institucional_no_accede_auditoria_global(self):
        self.client.force_login(self.usuario_a)
        self.assertEqual(self.client.get(reverse("core:auditoria")).status_code, 403)

    def test_paginas_nuevas_requieren_autenticacion(self):
        for route in ("core:perfil", "core:mis_instituciones", "instituciones:usuarios", "instituciones:usuario_crear"):
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 302, route)
            self.assertIn(reverse("login"), response.url)

    def test_rutas_principales_institucionales_responden(self):
        self.client.force_login(self.usuario_a)
        rutas = [
            reverse("core:institucion_dashboard"), reverse("core:perfil"),
            reverse("core:mis_instituciones"), reverse("instituciones:configuracion"),
            reverse("instituciones:usuarios"), reverse("core:modulo", args=["academico"]),
            reverse("core:modulo", args=["alumnos"]), reverse("core:modulo", args=["finanzas"]),
        ]
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_rutas_principales_globales_responden(self):
        superusuario = get_user_model().objects.create_superuser(username="rutas", password="segura-123")
        self.client.force_login(superusuario)
        for nombre in ("core:global_dashboard", "instituciones:lista", "core:usuarios_globales", "core:auditoria", "core:sistema", "catalogos:landing"):
            with self.subTest(nombre=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)

    def test_templates_de_usuario_no_enlazan_django_admin(self):
        templates = Path(settings.BASE_DIR, "templates")
        for archivo in templates.rglob("*.html"):
            contenido = archivo.read_text(encoding="utf-8").lower()
            with self.subTest(template=str(archivo.relative_to(templates))):
                self.assertNotIn("/admin/", contenido)
                self.assertNotIn("url 'admin:", contenido)

    def test_cambio_password_conserva_sesion(self):
        self.client.force_login(self.usuario_a)
        response = self.client.post(reverse("core:cambiar_password"), {
            "old_password": "segura-123", "new_password1": "Nueva-clave-segura-2026",
            "new_password2": "Nueva-clave-segura-2026",
        })
        self.assertRedirects(response, reverse("core:perfil"))
        self.assertIn("_auth_user_id", self.client.session)
