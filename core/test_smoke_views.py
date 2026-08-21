from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from instituciones.models import Institucion, UsuarioInstitucion


class VistasPrincipalesSmokeTests(TestCase):
    """Detecta rutas desconectadas, templates ausentes y errores de render básicos."""

    def setUp(self):
        self.institucion = Institucion.objects.create(nombre="Colegio Smoke", codigo="SMOKE")
        self.usuario = get_user_model().objects.create_user(username="smoke-admin", password="segura-123")
        self.asignacion = UsuarioInstitucion.objects.create(
            usuario=self.usuario,
            institucion=self.institucion,
            rol=UsuarioInstitucion.Rol.ADMINISTRADOR,
        )
        self.client.force_login(self.usuario)
        session = self.client.session
        session["asignacion_institucion_id"] = self.asignacion.pk
        session.save()

    def test_rutas_institucionales_principales_renderizan(self):
        rutas = (
            "core:institucion_dashboard",
            "academico:landing", "academico:ciclos", "academico:jornadas", "academico:ofertas",
            "academico:grados_secciones", "academico:cursos",
            "alumnos:landing", "alumnos:lista", "alumnos:inscripciones", "alumnos:familias",
            "alumnos:encargados", "alumnos:importaciones",
            "docentes:lista", "docentes:asignaciones", "docentes:carga",
        )
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(reverse(ruta)).status_code, 200)

    def test_landings_futuras_renderizan_sin_admin(self):
        for modulo in ("asistencia", "calificaciones", "tareas", "finanzas", "reportes", "comunicacion"):
            with self.subTest(modulo=modulo):
                response = self.client.get(reverse("core:modulo", args=[modulo]))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "/admin/")

    def test_rutas_protegidas_redirigen_sin_autenticacion(self):
        self.client.logout()
        for ruta in ("academico:ciclos", "alumnos:lista", "docentes:lista"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(reverse(ruta)).status_code, 302)
