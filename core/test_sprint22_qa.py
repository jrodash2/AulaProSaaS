from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.db import models

from academico.models import ResultadoAnualAlumno
from admisiones.models import SolicitudAdmision
from alumnos.models import Alumno, Inscripcion, RequisitoDocumentoAlumno, TipoDocumentoAlumno
from asistencia.models import RegistroAsistencia, SesionAsistencia
from calificaciones.models import ActividadEvaluacion, Calificacion
from docentes.models import AsignacionDocente, Docente
from finanzas.models import AplicacionPago, Cargo, Pago
from horarios.models import HorarioClase
from instituciones.models import Institucion
from rrhh.models import Empleado
from seguimiento.models import RegistroSeguimiento
from tareas.models import EntregaTarea, Tarea


class DemoPilotoQATests(TestCase):
    @classmethod
    def setUpTestData(cls):
        output = StringIO()
        call_command("crear_demo_aulapro", permitir_produccion=True, stdout=output)
        cls.institucion = Institucion.objects.get(codigo="AULAPRO-DEMO")
        cls.primera_ejecucion = cls._conteos(cls.institucion)
        call_command("crear_demo_aulapro", permitir_produccion=True, stdout=output)
        cls.segunda_ejecucion = cls._conteos(cls.institucion)
        call_command("crear_demo_aulapro", permitir_produccion=True, stdout=output)
        cls.tercera_ejecucion = cls._conteos(cls.institucion)

    @staticmethod
    def _conteos(institucion):
        return (
            Alumno.objects.filter(institucion=institucion).count(),
            HorarioClase.objects.filter(institucion=institucion).count(),
            RegistroSeguimiento.objects.filter(institucion=institucion).count(),
            SolicitudAdmision.objects.filter(institucion=institucion).count(),
            Empleado.objects.filter(institucion=institucion).count(),
            TipoDocumentoAlumno.objects.filter(institucion=institucion).count(),
            RequisitoDocumentoAlumno.objects.filter(institucion=institucion).count(),
        )

    def test_demo_completo_es_idempotente(self):
        self.assertEqual(self.segunda_ejecucion, self.primera_ejecucion)
        self.assertEqual(self.tercera_ejecucion, self.primera_ejecucion)
        self.assertEqual(self.primera_ejecucion, (30, 100, 7, 14, 11, 6, 6))

    def test_crea_roles_piloto(self):
        usuarios = get_user_model().objects
        for username in (
            "demo_superadmin", "demo_propietario", "demo_director",
            "demo_admin", "demo_secretaria", "demo_contabilidad",
            "demo_docente", "demo_padre", "demo_alumno",
        ):
            self.assertTrue(usuarios.filter(username=username).exists(), username)

    def test_integridad_academica(self):
        alumno = Alumno.objects.get(institucion=self.institucion, cui="1000000000001")
        self.assertTrue(alumno.inscripciones.filter(ciclo__anio=2026).exists())
        self.assertTrue(ActividadEvaluacion.objects.filter(institucion=self.institucion).exists())
        self.assertTrue(Calificacion.objects.filter(institucion=self.institucion, actividad__isnull=False).exists())
        self.assertGreaterEqual(SesionAsistencia.objects.filter(institucion=self.institucion).count(), 20)
        self.assertTrue(RegistroAsistencia.objects.filter(institucion=self.institucion, inscripcion__isnull=False).exists())

    def test_integridad_docentes_horarios_y_tareas(self):
        docente = Docente.objects.get(institucion=self.institucion, usuario__username="demo_docente")
        self.assertTrue(AsignacionDocente.objects.filter(institucion=self.institucion, docente=docente, activa=True).exists())
        self.assertTrue(HorarioClase.objects.filter(institucion=self.institucion, asignacion_docente__docente=docente).exists())
        self.assertGreaterEqual(Tarea.objects.filter(institucion=self.institucion).count(), 10)
        self.assertTrue(EntregaTarea.objects.filter(institucion=self.institucion, inscripcion__isnull=False).exists())

    def test_integridad_finanzas(self):
        self.assertGreaterEqual(Cargo.objects.filter(institucion=self.institucion).count(), 40)
        self.assertTrue(Pago.objects.filter(institucion=self.institucion, estado=Pago.Estado.CONFIRMADO).exists())
        self.assertFalse(AplicacionPago.objects.filter(institucion=self.institucion).exclude(pago__alumno_id=models.F("cargo__alumno_id")).exists())

    def test_portales_tienen_relaciones_completas(self):
        padre = get_user_model().objects.get(username="demo_padre")
        alumno_usuario = get_user_model().objects.get(username="demo_alumno")
        hijos = Alumno.objects.filter(vinculos_encargados__encargado__usuario=padre, vinculos_encargados__activo=True).distinct()
        self.assertGreaterEqual(hijos.count(), 2)
        alumno = Alumno.objects.get(usuario=alumno_usuario)
        self.assertTrue(alumno.inscripciones.filter(ciclo__anio=2026, estado=Inscripcion.Estado.ACTIVA).exists())
        self.assertTrue(alumno.calificaciones.exists())
        self.assertTrue(alumno.cargos.exists())

    def test_admision_convertida_y_resultados_historicos(self):
        solicitud = SolicitudAdmision.objects.get(institucion=self.institucion, estado=SolicitudAdmision.Estado.INSCRITA)
        alumno = Alumno.objects.get(institucion=self.institucion, cui=solicitud.aspirante.cui)
        self.assertTrue(alumno.inscripciones.filter(ciclo=solicitud.ciclo_solicitado).exists())
        self.assertTrue(ResultadoAnualAlumno.objects.filter(institucion=self.institucion, ciclo__anio=2025).exists())

    def test_empleados_docentes_conservan_identidad(self):
        for docente in Docente.objects.filter(institucion=self.institucion, estado=Docente.Estado.ACTIVO):
            self.assertTrue(Empleado.objects.filter(institucion=self.institucion, docente=docente).exists())

    def test_smoke_vistas_principales_con_datos_demo(self):
        recorridos = {
            "demo_propietario": (
                "/inicio/", "/academico/", "/alumnos/", "/docentes/",
                "/asistencia/", "/calificaciones/", "/tareas/", "/finanzas/",
                "/alumnos/expedientes/", "/horarios/", "/seguimiento/", "/admisiones/", "/rrhh/", "/reportes/",
            ),
            "demo_docente": ("/inicio/", "/docentes/mis-clases/", "/asistencia/", "/calificaciones/", "/tareas/", "/horarios/mi-horario/", "/seguimiento/casos/", "/rrhh/mi-perfil/"),
            "demo_padre": ("/portal/",),
            "demo_alumno": ("/portal/",),
        }
        for username, urls in recorridos.items():
            self.client.logout()
            self.assertTrue(self.client.login(username=username, password="AulaProDemo2026!"))
            for url in urls:
                with self.subTest(username=username, url=url):
                    self.assertLess(self.client.get(url).status_code, 500)

    def test_centro_demo_acceso_y_conteos_tenant_safe(self):
        from django.urls import reverse
        from core.demo.services import obtener_resumen_demo
        from instituciones.models import UsuarioInstitucion

        for username in ("demo_propietario", "demo_docente"):
            self.client.logout()
            self.assertTrue(self.client.login(username=username, password="AulaProDemo2026!"))
            response = self.client.get(reverse("core:demo_guia"))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["resumen_demo"]["alumnos"]["alumnos"], 30)

        otra = Institucion.objects.create(nombre="Institución ajena", codigo="NO-DEMO")
        otro = get_user_model().objects.create_user(username="usuario-real", password="segura-123")
        asignacion = UsuarioInstitucion.objects.create(usuario=otro, institucion=otra, rol=UsuarioInstitucion.Rol.PROPIETARIO)
        Alumno.objects.create(institucion=otra, cui="9999999999999", primer_nombre="DatoAjeno", primer_apellido="Privado", fecha_nacimiento="2012-01-01", sexo="F", fecha_ingreso="2026-01-01")
        self.client.force_login(otro)
        session = self.client.session
        session["asignacion_institucion_id"] = asignacion.pk
        session.save()
        response = self.client.get(reverse("core:demo_guia"))
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "AulaProDemo2026!", status_code=404)
        self.assertEqual(obtener_resumen_demo(self.institucion)["alumnos"]["alumnos"], 30)

    def test_centro_demo_respeta_modulos_y_links_por_rol(self):
        from django.urls import reverse
        from suscripciones.models import PlanModulo

        self.client.login(username="demo_propietario", password="AulaProDemo2026!")
        response = self.client.get(reverse("core:demo_guia"))
        self.assertContains(response, reverse("academico:landing"))
        self.assertContains(response, reverse("rrhh:dashboard"))
        PlanModulo.objects.filter(plan__suscripciones__institucion=self.institucion, modulo__codigo="RRHH").update(habilitado=False)
        response = self.client.get(reverse("core:demo_guia"))
        self.assertNotContains(response, 'data-module="RRHH"')
        self.assertNotContains(response, reverse("rrhh:dashboard"))

    def test_centro_demo_sin_contexto_no_asume_tenant(self):
        from django.urls import reverse

        superadmin = get_user_model().objects.get(username="demo_superadmin")
        self.client.force_login(superadmin)
        self.assertEqual(self.client.get(reverse("core:demo_guia")).status_code, 404)

    def test_banner_y_sidebar_solo_en_demo(self):
        from django.urls import reverse
        from instituciones.models import UsuarioInstitucion

        self.client.login(username="demo_propietario", password="AulaProDemo2026!")
        response = self.client.get(reverse("core:institucion_dashboard"))
        self.assertContains(response, "Estás usando el entorno de demostración de AulaPro")
        self.assertContains(response, "Guía del Demo")

        otra = Institucion.objects.create(nombre="Colegio Real", codigo="REAL-BANNER")
        usuario = get_user_model().objects.create_user(username="propietario-real", password="segura-123")
        asignacion = UsuarioInstitucion.objects.create(usuario=usuario, institucion=otra, rol=UsuarioInstitucion.Rol.PROPIETARIO)
        self.client.force_login(usuario)
        session = self.client.session
        session["asignacion_institucion_id"] = asignacion.pk
        session.save()
        response = self.client.get(reverse("core:institucion_dashboard"))
        self.assertNotContains(response, "Estás usando el entorno de demostración de AulaPro")
        self.assertNotContains(response, "Guía del Demo")
        self.assertNotContains(response, "AulaProDemo2026!")

    def test_demo_consolida_aliases_documentales_sin_perder_documentos(self):
        from django.core.management import call_command
        from alumnos.models import DocumentoAlumno, RequisitoDocumentoAlumno, TipoDocumentoAlumno

        alumno = Alumno.objects.filter(institucion=self.institucion).first()
        alias = TipoDocumentoAlumno.objects.create(institucion=self.institucion, codigo="FOTO", nombre="Fotografía duplicada")
        RequisitoDocumentoAlumno.objects.create(institucion=self.institucion, tipo_documento=alias)
        documento = DocumentoAlumno.objects.create(institucion=self.institucion, alumno=alumno, tipo_documento=alias, estado=DocumentoAlumno.Estado.ENTREGADO, cargado_por=get_user_model().objects.get(username="demo_admin"))
        call_command("crear_demo_aulapro", permitir_produccion=True, stdout=StringIO())
        documento.refresh_from_db()
        self.assertEqual(documento.tipo_documento.codigo, "FOTOGRAFIA")
        self.assertFalse(TipoDocumentoAlumno.objects.filter(institucion=self.institucion, codigo="FOTO").exists())
        self.assertEqual(RequisitoDocumentoAlumno.objects.filter(institucion=self.institucion, tipo_documento__codigo="FOTOGRAFIA").count(), 1)
