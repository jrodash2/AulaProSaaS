from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from academico.models import CicloEscolar, CursoInstitucion, GradoInstitucion, JornadaInstitucion, OfertaAcademica, Seccion
from catalogos.models import NivelEducativo
from docentes.models import AsignacionDocente, Docente
from instituciones.models import Institucion, UsuarioInstitucion

from .models import Aula, BloqueHorario, HorarioClase
from .services import detectar_conflictos, validar_carga_semanal


class HorariosBase(TestCase):
    def setUp(self):
        self.inst = Institucion.objects.create(nombre="Colegio A", codigo="HORA")
        self.otra = Institucion.objects.create(nombre="Colegio B", codigo="HORB")
        self.users = {}
        for rol in ("ADMINISTRADOR", "DIRECTOR", "DOCENTE", "CONTABILIDAD"):
            user = get_user_model().objects.create_user(username=f"h-{rol.lower()}", password="x")
            UsuarioInstitucion.objects.create(usuario=user, institucion=self.inst, rol=rol)
            self.users[rol] = user
        self.ciclo = CicloEscolar.objects.create(institucion=self.inst, nombre="2026", anio=2026, fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 11, 30), estado="ACTIVO")
        self.jornada = JornadaInstitucion.objects.create(institucion=self.inst, codigo="MAT", nombre="Matutina")
        nivel = NivelEducativo.objects.create(codigo="HNB", nombre="Nivel horario")
        self.oferta = OfertaAcademica.objects.create(institucion=self.inst, ciclo=self.ciclo, nivel=nivel, nombre_mostrado="Básico", codigo_interno="HB", origen="PERSONALIZADA")
        self.grado = GradoInstitucion.objects.create(institucion=self.inst, ciclo=self.ciclo, oferta=self.oferta, codigo="G1", nombre="Primero")
        self.seccion = Seccion.objects.create(institucion=self.inst, ciclo=self.ciclo, grado=self.grado, jornada=self.jornada, codigo="A", nombre="A")
        self.seccion2 = Seccion.objects.create(institucion=self.inst, ciclo=self.ciclo, grado=self.grado, jornada=self.jornada, codigo="B", nombre="B")
        self.curso = CursoInstitucion.objects.create(institucion=self.inst, ciclo=self.ciclo, oferta=self.oferta, grado=self.grado, nombre_personalizado="Matemática", nombre_mostrado="Matemática", origen="INSTITUCIONAL", periodos_semanales=2)
        self.docente = Docente.objects.create(institucion=self.inst, usuario=self.users["DOCENTE"], primer_nombre="Carlos", primer_apellido="López", telefono="1", fecha_ingreso=date(2026, 1, 1))
        self.asig = AsignacionDocente.objects.create(institucion=self.inst, ciclo=self.ciclo, docente=self.docente, oferta_academica=self.oferta, grado=self.grado, seccion=self.seccion, curso=self.curso, fecha_inicio=date(2026, 1, 1))
        self.asig2 = AsignacionDocente.objects.create(institucion=self.inst, ciclo=self.ciclo, docente=self.docente, oferta_academica=self.oferta, grado=self.grado, seccion=self.seccion2, curso=self.curso, fecha_inicio=date(2026, 1, 1), es_titular=False)
        self.b1 = BloqueHorario.objects.create(institucion=self.inst, jornada=self.jornada, nombre="Período 1", orden=1, hora_inicio=time(7), hora_fin=time(7, 45))
        self.b2 = BloqueHorario.objects.create(institucion=self.inst, jornada=self.jornada, nombre="Período 2", orden=2, hora_inicio=time(7, 45), hora_fin=time(8, 30))
        self.aula = Aula.objects.create(institucion=self.inst, codigo="A-1", nombre="Aula 1", capacidad=30)

    def clase(self, **kwargs):
        data = dict(institucion=self.inst, ciclo=self.ciclo, jornada=self.jornada, seccion=self.seccion, asignacion_docente=self.asig, bloque=self.b1, dia_semana="LUNES", aula=self.aula)
        data.update(kwargs)
        return HorarioClase.objects.create(**data)


class ModeloConflictoTests(HorariosBase):
    def test_fin_debe_ser_posterior(self):
        with self.assertRaises(ValidationError):
            BloqueHorario.objects.create(institucion=self.inst, jornada=self.jornada, nombre="Mal", orden=3, hora_inicio=time(9), hora_fin=time(8))

    def test_traslape_bloques(self):
        with self.assertRaises(ValidationError):
            BloqueHorario.objects.create(institucion=self.inst, jornada=self.jornada, nombre="Cruce", orden=3, hora_inicio=time(7, 30), hora_fin=time(8))

    def test_conflicto_seccion(self):
        self.clase()
        candidato = HorarioClase(institucion=self.inst, ciclo=self.ciclo, jornada=self.jornada, seccion=self.seccion, asignacion_docente=self.asig, bloque=self.b1, dia_semana="LUNES")
        self.assertTrue(any("sección" in texto for texto in detectar_conflictos(candidato)))
        with self.assertRaises(ValidationError):
            candidato.save()

    def test_conflicto_docente(self):
        self.clase()
        with self.assertRaises(ValidationError):
            self.clase(seccion=self.seccion2, asignacion_docente=self.asig2, aula=None)

    def test_conflicto_aula(self):
        self.clase()
        otro_user = get_user_model().objects.create_user(username="h-otro", password="x")
        UsuarioInstitucion.objects.create(usuario=otro_user, institucion=self.inst, rol="DOCENTE")
        otro_doc = Docente.objects.create(institucion=self.inst, usuario=otro_user, primer_nombre="Ana", primer_apellido="Pérez", telefono="2", fecha_ingreso=date(2026, 1, 1))
        otra_asig = AsignacionDocente.objects.create(institucion=self.inst, ciclo=self.ciclo, docente=otro_doc, oferta_academica=self.oferta, grado=self.grado, seccion=self.seccion2, curso=self.curso, fecha_inicio=date(2026, 1, 1))
        with self.assertRaises(ValidationError):
            self.clase(seccion=self.seccion2, asignacion_docente=otra_asig)

    def test_otro_dia_y_bloque_permitidos(self):
        self.clase()
        self.clase(bloque=self.b2)
        self.clase(dia_semana="MARTES")
        self.assertEqual(HorarioClase.objects.count(), 3)

    def test_aula_otro_tenant_rechazada(self):
        aula = Aula.objects.create(institucion=self.otra, codigo="B-1", nombre="Ajena")
        with self.assertRaises(ValidationError):
            self.clase(aula=aula)

    def test_ciclo_cerrado_rechazado(self):
        self.ciclo.estado = "CERRADO"; self.ciclo.cerrado = True; self.ciclo.save()
        with self.assertRaises(ValidationError):
            self.clase()

    def test_carga_semanal(self):
        self.clase()
        carga = validar_carga_semanal(self.seccion)[0]
        self.assertEqual((carga["asignados"], carga["faltan"], carga["exceso"]), (1, 1, 0))


class VistaPermisoTests(HorariosBase):
    def test_admin_abre_y_crea(self):
        self.client.force_login(self.users["ADMINISTRADOR"])
        self.assertEqual(self.client.get(reverse("horarios:dashboard")).status_code, 200)
        response = self.client.post(reverse("horarios:aula_crear"), {"codigo": "LAB", "nombre": "Laboratorio", "capacidad": 20, "ubicacion": "", "descripcion": "", "activa": "on"})
        self.assertRedirects(response, reverse("horarios:aulas"))

    def test_director_gestiona(self):
        self.client.force_login(self.users["DIRECTOR"])
        self.assertEqual(self.client.get(reverse("horarios:bloque_crear")).status_code, 200)

    def test_docente_solo_consulta(self):
        self.client.force_login(self.users["DOCENTE"])
        self.assertEqual(self.client.get(reverse("horarios:mi_horario")).status_code, 200)
        self.assertEqual(self.client.get(reverse("horarios:aula_crear")).status_code, 403)

    def test_contabilidad_bloqueada(self):
        self.client.force_login(self.users["CONTABILIDAD"])
        self.assertEqual(self.client.get(reverse("horarios:dashboard")).status_code, 403)

    def test_tenant_no_edita_aula(self):
        ajena = Aula.objects.create(institucion=self.otra, codigo="AJ", nombre="Ajena")
        self.client.force_login(self.users["ADMINISTRADOR"])
        self.assertEqual(self.client.get(reverse("horarios:aula_editar", args=[ajena.pk])).status_code, 404)

    def test_estado_requiere_post(self):
        clase = self.clase()
        self.client.force_login(self.users["ADMINISTRADOR"])
        self.assertEqual(self.client.get(reverse("horarios:clase_estado", args=[clase.pk])).status_code, 405)

    def test_exportacion_xlsx(self):
        self.clase()
        self.client.force_login(self.users["ADMINISTRADOR"])
        response = self.client.get(reverse("horarios:exportar", args=[self.seccion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response.headers["Content-Type"])
