from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from admisiones.models import SolicitudAdmision
from alumnos.models import Alumno
from horarios.models import HorarioClase
from instituciones.models import Institucion
from rrhh.models import Empleado
from seguimiento.models import RegistroSeguimiento


class DemoPilotoQATests(TestCase):
    def _conteos(self, institucion):
        return (
            Alumno.objects.filter(institucion=institucion).count(),
            HorarioClase.objects.filter(institucion=institucion).count(),
            RegistroSeguimiento.objects.filter(institucion=institucion).count(),
            SolicitudAdmision.objects.filter(institucion=institucion).count(),
            Empleado.objects.filter(institucion=institucion).count(),
        )

    def test_demo_completo_es_idempotente_y_crea_roles_piloto(self):
        output = StringIO()
        call_command("crear_demo_aulapro", permitir_produccion=True, stdout=output)
        institucion = Institucion.objects.get(codigo="AULAPRO-DEMO")
        primera_ejecucion = self._conteos(institucion)

        call_command("crear_demo_aulapro", permitir_produccion=True, stdout=output)

        self.assertEqual(self._conteos(institucion), primera_ejecucion)
        self.assertEqual(primera_ejecucion, (12, 3, 4, 10, 5))
        usuarios = get_user_model().objects
        for username in (
            "demo_superadmin",
            "demo_propietario",
            "demo_director",
            "demo_admin",
            "demo_secretaria",
            "demo_contabilidad",
            "demo_docente",
            "demo_padre",
            "demo_alumno",
        ):
            self.assertTrue(usuarios.filter(username=username).exists(), username)
