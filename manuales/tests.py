from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from instituciones.models import Institucion, UsuarioInstitucion
from .registry import MANUALES


class ManualesAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.institucion = Institucion.objects.create(nombre="Colegio de Prueba", codigo="MAN-TEST")
        cls.users = {}
        for role in UsuarioInstitucion.Rol.values:
            user = get_user_model().objects.create_user(username=f"manual_{role.lower()}", password="test-pass")
            assignment = UsuarioInstitucion.objects.create(usuario=user, institucion=cls.institucion, rol=role)
            cls.users[role] = (user, assignment)
        cls.superuser = get_user_model().objects.create_superuser(username="manual_root", password="test-pass", email="root@example.test")

    def login_role(self, role):
        user, assignment = self.users[role]
        self.client.force_login(user)
        session = self.client.session
        session["asignacion_institucion_id"] = assignment.pk
        session.save()

    def test_each_role_can_open_own_manual_and_main_views(self):
        for role in UsuarioInstitucion.Rol.values:
            with self.subTest(role=role):
                self.client.logout(); self.login_role(role)
                self.assertEqual(self.client.get(reverse("manuales:inicio")).status_code, 200)
                self.assertEqual(self.client.get(reverse("manuales:mi_manual")).status_code, 302)
                response = self.client.get(reverse("manuales:manual", args=[role.lower()]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, MANUALES[role.lower()]["titulo"])

    def test_parent_and_student_cannot_open_another_manual(self):
        for role, forbidden in (("PADRE", "superadmin"), ("ALUMNO", "director")):
            with self.subTest(role=role):
                self.client.logout(); self.login_role(role)
                self.assertEqual(self.client.get(reverse("manuales:manual", args=[forbidden])).status_code, 403)

    def test_superadmin_can_open_every_manual(self):
        self.client.force_login(self.superuser)
        for role in MANUALES:
            with self.subTest(role=role):
                self.assertEqual(self.client.get(reverse("manuales:manual", args=[role])).status_code, 200)

    def test_every_chapter_link_resolves_and_renders(self):
        self.client.force_login(self.superuser)
        for role, manual in MANUALES.items():
            for chapter in manual["secciones"]:
                with self.subTest(role=role, chapter=chapter["slug"]):
                    response = self.client.get(reverse("manuales:seccion", args=[role, chapter["slug"]]))
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, chapter["titulo"])

    def test_sidebar_contains_manuals_for_every_role(self):
        for role in UsuarioInstitucion.Rol.values:
            with self.subTest(role=role):
                self.client.logout(); self.login_role(role)
                self.assertContains(self.client.get(reverse("manuales:inicio")), "Manuales")
        self.client.force_login(self.superuser)
        self.assertContains(self.client.get(reverse("manuales:inicio")), "Manuales")

    def test_unknown_or_unavailable_chapter_is_not_exposed(self):
        self.login_role("PADRE")
        self.assertEqual(self.client.get(reverse("manuales:seccion", args=["padre", "auditoria"])).status_code, 404)
