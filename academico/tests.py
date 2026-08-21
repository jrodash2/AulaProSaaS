from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from catalogos.models import CarreraCatalogo, CursoCatalogo, CursoPensum, GradoPensum, NivelEducativo, VersionPensum
from instituciones.models import Institucion, UsuarioInstitucion

from .models import CicloEscolar, CursoInstitucion, GradoInstitucion, JornadaInstitucion, OfertaAcademica, Seccion
from .services import crear_oferta_desde_pensum, establecer_ciclo_actual


class AcademicoBase(TestCase):
    def setUp(self):
        self.a = Institucion.objects.create(nombre="Colegio A", codigo="ACA-A")
        self.b = Institucion.objects.create(nombre="Colegio B", codigo="ACA-B")
        self.admin = get_user_model().objects.create_user(username="academico-admin", password="segura-123")
        self.director = get_user_model().objects.create_user(username="academico-director", password="segura-123")
        self.docente = get_user_model().objects.create_user(username="academico-docente", password="segura-123")
        self.contabilidad = get_user_model().objects.create_user(username="academico-conta", password="segura-123")
        UsuarioInstitucion.objects.create(usuario=self.admin, institucion=self.a, rol=UsuarioInstitucion.Rol.ADMINISTRADOR)
        UsuarioInstitucion.objects.create(usuario=self.director, institucion=self.a, rol=UsuarioInstitucion.Rol.DIRECTOR)
        UsuarioInstitucion.objects.create(usuario=self.docente, institucion=self.a, rol=UsuarioInstitucion.Rol.DOCENTE)
        UsuarioInstitucion.objects.create(usuario=self.contabilidad, institucion=self.a, rol=UsuarioInstitucion.Rol.CONTABILIDAD)
        self.ciclo_a = CicloEscolar.objects.create(institucion=self.a, nombre="Ciclo 2027", anio=2027, fecha_inicio=date(2027, 1, 10), fecha_fin=date(2027, 10, 30), es_actual=True)
        self.ciclo_b = CicloEscolar.objects.create(institucion=self.b, nombre="Ciclo B 2027", anio=2027, fecha_inicio=date(2027, 1, 10), fecha_fin=date(2027, 10, 30), es_actual=True)
        self.nivel = NivelEducativo.objects.create(codigo="DIV-ACA", nombre="Diversificado", orden=4)
        self.carrera = CarreraCatalogo.objects.create(codigo_interno="BAC-ACA", nombre="Bachillerato de prueba", nivel=self.nivel, duracion_anios=2)
        self.pensum = VersionPensum.objects.create(carrera=self.carrera, codigo_version="2027", nombre="Pensum 2027", fecha_inicio_vigencia=date(2027, 1, 1), estado=VersionPensum.Estado.VIGENTE)
        self.g1 = GradoPensum.objects.create(pensum=self.pensum, codigo="G1", nombre="Cuarto", numero_orden=1)
        self.g2 = GradoPensum.objects.create(pensum=self.pensum, codigo="G2", nombre="Quinto", numero_orden=2)
        self.mate = CursoCatalogo.objects.create(codigo_interno="MAT-ACA", nombre="Matemática")
        self.fisica = CursoCatalogo.objects.create(codigo_interno="FIS-ACA", nombre="Física")
        self.cp1 = CursoPensum.objects.create(pensum=self.pensum, grado=self.g1, curso=self.mate, orden=1, periodos_semanales=5)
        self.cp2 = CursoPensum.objects.create(pensum=self.pensum, grado=self.g2, curso=self.fisica, orden=1, periodos_semanales=4)

    def crear_oferta(self, institucion=None, ciclo=None):
        return crear_oferta_desde_pensum(institucion=institucion or self.a, ciclo=ciclo or self.ciclo_a, nivel=self.nivel, carrera=self.carrera, pensum=self.pensum)


class CicloEscolarTests(AcademicoBase):
    def test_detalle_ciclo_y_aislamiento(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("academico:ciclo_detalle", args=[self.ciclo_a.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("academico:ciclo_detalle", args=[self.ciclo_b.pk])).status_code, 404)

    def test_institucion_a_no_ve_ciclos_b(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("academico:ciclos"))
        self.assertContains(response, self.ciclo_a.nombre)
        self.assertNotContains(response, self.ciclo_b.nombre)

    def test_selector_rechaza_ciclo_de_otra_institucion(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("academico:ofertas"), {"ciclo": self.ciclo_b.pk}).status_code, 404)

    def test_anio_no_se_duplica_en_misma_institucion(self):
        with self.assertRaises(ValidationError):
            CicloEscolar.objects.create(institucion=self.a, nombre="Otro", anio=2027, fecha_inicio=date(2027, 2, 1), fecha_fin=date(2027, 11, 1))

    def test_dos_instituciones_pueden_usar_mismo_anio(self):
        self.assertEqual(CicloEscolar.objects.filter(anio=2027).count(), 2)

    def test_solo_un_actual_y_cambiar_desactiva_anterior(self):
        nuevo = CicloEscolar.objects.create(institucion=self.a, nombre="Ciclo 2028", anio=2028, fecha_inicio=date(2028, 1, 1), fecha_fin=date(2028, 10, 1))
        establecer_ciclo_actual(nuevo)
        self.ciclo_a.refresh_from_db(); nuevo.refresh_from_db()
        self.assertFalse(self.ciclo_a.es_actual)
        self.assertTrue(nuevo.es_actual)
        self.assertEqual(CicloEscolar.objects.filter(institucion=self.a, es_actual=True).count(), 1)

    def test_fechas_invalidas_rechazadas(self):
        with self.assertRaises(ValidationError):
            CicloEscolar.objects.create(institucion=self.a, nombre="Inválido", anio=2029, fecha_inicio=date(2029, 10, 1), fecha_fin=date(2029, 1, 1))


class DetallesAcademicosTests(AcademicoBase):
    def setUp(self):
        super().setUp()
        self.oferta = self.crear_oferta()
        self.grado = self.oferta.grados.first()
        self.curso = self.grado.cursos.first()
        self.jornada = JornadaInstitucion.objects.create(institucion=self.a, codigo="MAT", nombre="Matutina")
        self.seccion = Seccion.objects.create(institucion=self.a, ciclo=self.ciclo_a, grado=self.grado, jornada=self.jornada, codigo="A", nombre="A")
        self.client.force_login(self.admin)

    def test_detalles_principales_responden(self):
        for name, pk in (("jornada_detalle", self.jornada.pk), ("grado_detalle", self.grado.pk), ("seccion_detalle", self.seccion.pk), ("curso_detalle", self.curso.pk)):
            self.assertEqual(self.client.get(reverse(f"academico:{name}", args=[pk])).status_code, 200)

    def test_detalles_externos_son_404(self):
        jornada = JornadaInstitucion.objects.create(institucion=self.b, codigo="MAT", nombre="Matutina B")
        oferta = self.crear_oferta(institucion=self.b, ciclo=self.ciclo_b)
        grado = oferta.grados.first(); curso = grado.cursos.first()
        seccion = Seccion.objects.create(institucion=self.b, ciclo=self.ciclo_b, grado=grado, jornada=jornada, codigo="B", nombre="B")
        for name, pk in (("jornada_detalle", jornada.pk), ("grado_detalle", grado.pk), ("seccion_detalle", seccion.pk), ("curso_detalle", curso.pk)):
            self.assertEqual(self.client.get(reverse(f"academico:{name}", args=[pk])).status_code, 404)


class OfertaAcademicaTests(AcademicoBase):
    def test_genera_grados_cursos_y_referencias_sin_modificar_catalogo(self):
        grados_globales, cursos_globales, items_globales = GradoPensum.objects.count(), CursoCatalogo.objects.count(), CursoPensum.objects.count()
        oferta = self.crear_oferta()
        self.assertEqual(oferta.grados.count(), 2)
        self.assertEqual(oferta.cursos.count(), 2)
        self.assertEqual(oferta.version_pensum, self.pensum)
        self.assertEqual(oferta.grados.get(codigo="G1").grado_pensum_origen, self.g1)
        self.assertEqual(oferta.cursos.get(curso_catalogo=self.mate).curso_pensum_origen, self.cp1)
        self.assertEqual((GradoPensum.objects.count(), CursoCatalogo.objects.count(), CursoPensum.objects.count()), (grados_globales, cursos_globales, items_globales))

    def test_pensum_debe_pertenecer_a_carrera(self):
        otra = CarreraCatalogo.objects.create(codigo_interno="OTRA-ACA", nombre="Otra", nivel=self.nivel, duracion_anios=2)
        with self.assertRaises(ValidationError):
            crear_oferta_desde_pensum(institucion=self.a, ciclo=self.ciclo_a, nivel=self.nivel, carrera=otra, pensum=self.pensum)

    def test_no_duplica_oferta(self):
        self.crear_oferta()
        with self.assertRaises(ValidationError):
            self.crear_oferta()

    def test_colegio_a_no_ve_ni_accede_oferta_b(self):
        oferta_b = self.crear_oferta(self.b, self.ciclo_b)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("academico:ofertas"))
        self.assertNotContains(response, oferta_b.nombre_mostrado)
        self.assertEqual(self.client.get(reverse("academico:oferta_detalle", args=[oferta_b.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("academico:oferta_estado", args=[oferta_b.pk])).status_code, 404)

    def test_ciclo_cerrado_no_admite_oferta(self):
        self.ciclo_a.cerrado = True; self.ciclo_a.save()
        with self.assertRaises(ValidationError):
            self.crear_oferta()


class CursosYSeccionesTests(AcademicoBase):
    def setUp(self):
        super().setUp(); self.oferta = self.crear_oferta(); self.grado = self.oferta.grados.get(codigo="G1")
        self.jornada = JornadaInstitucion.objects.create(institucion=self.a, codigo="MAT", nombre="Matutina", hora_inicio=time(7), hora_fin=time(12))

    def test_oficial_exige_catalogo(self):
        with self.assertRaises(ValidationError):
            CursoInstitucion.objects.create(institucion=self.a, ciclo=self.ciclo_a, oferta=self.oferta, grado=self.grado, origen=CursoInstitucion.Origen.OFICIAL)

    def test_institucional_exige_nombre_y_no_crea_catalogo(self):
        antes = CursoCatalogo.objects.count()
        with self.assertRaises(ValidationError):
            CursoInstitucion.objects.create(institucion=self.a, ciclo=self.ciclo_a, oferta=self.oferta, grado=self.grado, origen=CursoInstitucion.Origen.INSTITUCIONAL)
        propio = CursoInstitucion.objects.create(institucion=self.a, ciclo=self.ciclo_a, oferta=self.oferta, grado=self.grado, origen=CursoInstitucion.Origen.INSTITUCIONAL, nombre_personalizado="Robótica")
        self.assertEqual(propio.nombre, "Robótica")
        self.assertEqual(CursoCatalogo.objects.count(), antes)

    def test_desactivar_oficial_no_elimina_pensum(self):
        curso = self.oferta.cursos.get(curso_pensum_origen=self.cp1)
        self.client.force_login(self.admin); self.client.post(reverse("academico:curso_estado", args=[curso.pk]))
        curso.refresh_from_db()
        self.assertFalse(curso.activo)
        self.assertTrue(CursoPensum.objects.filter(pk=self.cp1.pk).exists())

    def test_no_duplica_seccion_y_permite_mismo_nombre_otro_grado(self):
        Seccion.objects.create(institucion=self.a, ciclo=self.ciclo_a, grado=self.grado, jornada=self.jornada, codigo="A", nombre="A")
        with self.assertRaises(ValidationError):
            Seccion.objects.create(institucion=self.a, ciclo=self.ciclo_a, grado=self.grado, jornada=self.jornada, codigo="A2", nombre="A")
        otro = self.oferta.grados.get(codigo="G2")
        Seccion.objects.create(institucion=self.a, ciclo=self.ciclo_a, grado=otro, jornada=self.jornada, codigo="A", nombre="A")

    def test_jornada_y_entidades_externas_son_rechazadas(self):
        jornada_b = JornadaInstitucion.objects.create(institucion=self.b, codigo="MAT", nombre="Matutina")
        with self.assertRaises(ValidationError):
            Seccion.objects.create(institucion=self.a, ciclo=self.ciclo_a, grado=self.grado, jornada=jornada_b, codigo="B", nombre="B")
        oferta_b = self.crear_oferta(self.b, self.ciclo_b); grado_b = oferta_b.grados.first(); curso_b = oferta_b.cursos.first()
        seccion_b = Seccion.objects.create(institucion=self.b, ciclo=self.ciclo_b, grado=grado_b, codigo="A", nombre="A")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("academico:seccion_crear", args=[grado_b.pk]) + f"?ciclo={self.ciclo_a.pk}").status_code, 404)
        self.assertEqual(self.client.get(reverse("academico:curso_editar", args=[grado_b.pk, curso_b.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("academico:seccion_editar", args=[seccion_b.pk]) + f"?ciclo={self.ciclo_a.pk}").status_code, 404)


class PermisosAcademicosTests(AcademicoBase):
    def test_administrador_y_director_pueden_configurar(self):
        for usuario in (self.admin, self.director):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("academico:ciclo_crear")).status_code, 200)

    def test_docente_y_contabilidad_no_pueden_modificar(self):
        for usuario in (self.docente, self.contabilidad):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse("academico:landing")).status_code, 200)
            self.assertEqual(self.client.get(reverse("academico:ciclo_crear")).status_code, 403)
