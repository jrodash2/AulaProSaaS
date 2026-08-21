from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from auditoria.models import EventoAuditoria
from instituciones.models import Institucion, UsuarioInstitucion

from .models import (
    CarreraCatalogo,
    CursoCatalogo,
    CursoPensum,
    GradoPensum,
    NivelEducativo,
    TipoCarrera,
    VersionPensum,
)
from .services import duplicar_version_pensum


class CatalogoModelosTests(TestCase):
    def setUp(self):
        self.nivel = NivelEducativo.objects.create(
            codigo="DIVERSIFICADO",
            nombre="Diversificado",
            orden=4,
        )
        self.tipo = TipoCarrera.objects.create(
            codigo="BACH",
            nombre="Bachillerato",
        )
        self.carrera = CarreraCatalogo.objects.create(
            codigo_interno="CAR-001",
            nombre="Carrera temporal de prueba",
            nivel=self.nivel,
            tipo_carrera=self.tipo,
            duracion_anios=2,
        )
        self.pensum = VersionPensum.objects.create(
            carrera=self.carrera,
            codigo_version="2026",
            nombre="Pensum 2026",
            fecha_inicio_vigencia=date(2026, 1, 1),
        )
        self.grado = GradoPensum.objects.create(
            pensum=self.pensum,
            codigo="G1",
            nombre="Primer grado de carrera",
            numero_orden=1,
        )
        self.curso = CursoCatalogo.objects.create(
            codigo_interno="CUR-001",
            nombre="Curso temporal de prueba",
        )

    def test_codigo_nivel_es_unico(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            NivelEducativo.objects.create(
                codigo=self.nivel.codigo,
                nombre="Duplicado",
            )

    def test_codigo_carrera_es_unico(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CarreraCatalogo.objects.create(
                codigo_interno=self.carrera.codigo_interno,
                nombre="Duplicada",
                nivel=self.nivel,
                duracion_anios=3,
            )

    def test_carrera_admite_multiples_versiones(self):
        VersionPensum.objects.create(
            carrera=self.carrera,
            codigo_version="2027",
            nombre="Pensum 2027",
            fecha_inicio_vigencia=date(2027, 1, 1),
        )
        self.assertEqual(self.carrera.versiones_pensum.count(), 2)

    def test_no_duplica_grado_en_version(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            GradoPensum.objects.create(
                pensum=self.pensum,
                codigo=self.grado.codigo,
                nombre="Grado duplicado",
                numero_orden=2,
            )

    def test_no_duplica_curso_en_grado_y_pensum(self):
        CursoPensum.objects.create(
            pensum=self.pensum,
            grado=self.grado,
            curso=self.curso,
        )
        with self.assertRaises(ValidationError):
            CursoPensum.objects.create(
                pensum=self.pensum,
                grado=self.grado,
                curso=self.curso,
            )

    def test_rechaza_grado_de_otro_pensum(self):
        otro_pensum = VersionPensum.objects.create(
            carrera=self.carrera,
            codigo_version="OTRO",
            nombre="Otro pensum",
            fecha_inicio_vigencia=date(2028, 1, 1),
        )
        otro_grado = GradoPensum.objects.create(
            pensum=otro_pensum,
            codigo="G1",
            nombre="Otro grado",
            numero_orden=1,
        )
        with self.assertRaises(ValidationError):
            CursoPensum.objects.create(
                pensum=self.pensum,
                grado=otro_grado,
                curso=self.curso,
            )

    def test_duplicar_pensum_copia_estructura_no_curso_catalogo(self):
        CursoPensum.objects.create(
            pensum=self.pensum,
            grado=self.grado,
            curso=self.curso,
            orden=2,
            periodos_semanales=5,
            obligatorio=True,
        )
        cursos_antes = CursoCatalogo.objects.count()
        copia = duplicar_version_pensum(
            self.pensum,
            codigo_version="2027",
            nombre="Pensum 2027",
            fecha_inicio_vigencia=date(2027, 1, 1),
        )
        self.assertEqual(copia.grados.count(), 1)
        self.assertEqual(copia.cursos_pensum.count(), 1)
        self.assertEqual(CursoCatalogo.objects.count(), cursos_antes)
        item_copiado = copia.cursos_pensum.get()
        self.assertEqual(item_copiado.curso, self.curso)
        self.assertEqual(item_copiado.periodos_semanales, 5)
        self.assertEqual(item_copiado.orden, 2)

    def test_version_duplicada_siempre_es_borrador(self):
        self.pensum.estado = VersionPensum.Estado.VIGENTE
        self.pensum.save()
        copia = duplicar_version_pensum(
            self.pensum,
            codigo_version="COPIA",
            nombre="Copia",
            fecha_inicio_vigencia=date(2029, 1, 1),
        )
        self.assertEqual(copia.estado, VersionPensum.Estado.BORRADOR)


class CatalogoSeguridadVistasTests(TestCase):
    def setUp(self):
        self.nivel = NivelEducativo.objects.create(
            codigo="NIVEL-TEST",
            nombre="Nivel temporal",
        )
        self.carrera = CarreraCatalogo.objects.create(
            codigo_interno="CARRERA-TEST",
            nombre="Carrera temporal",
            nivel=self.nivel,
            duracion_anios=2,
        )
        self.superusuario = get_user_model().objects.create_superuser(
            username="supercatalogo",
            email="super@example.com",
            password="clave-segura-123",
        )
        self.usuario_colegio = get_user_model().objects.create_user(
            username="admincolegio",
            password="clave-segura-123",
        )
        institucion = Institucion.objects.create(
            codigo="COLEGIO-TEST",
            nombre="Colegio temporal",
        )
        UsuarioInstitucion.objects.create(
            usuario=self.usuario_colegio,
            institucion=institucion,
            rol=UsuarioInstitucion.Rol.ADMINISTRADOR,
        )

    def test_administrador_colegio_no_accede_catalogo_global(self):
        self.client.force_login(self.usuario_colegio)
        response = self.client.get(reverse("catalogos:carrera_lista"))
        self.assertEqual(response.status_code, 403)

    def test_superusuario_puede_administrar_catalogo(self):
        self.client.force_login(self.superusuario)
        response = self.client.get(reverse("catalogos:carrera_lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.carrera.nombre)

    def test_modificar_carrera_registra_auditoria_global(self):
        self.client.force_login(self.superusuario)
        response = self.client.post(
            reverse("catalogos:carrera_editar", args=(self.carrera.uuid,)),
            {
                "codigo_interno": self.carrera.codigo_interno,
                "codigo_mineduc": "",
                "nombre": "Carrera modificada",
                "nombre_corto": "",
                "nivel": self.nivel.pk,
                "tipo_carrera": "",
                "duracion_anios": 2,
                "descripcion": "",
                "modalidad": CarreraCatalogo.Modalidad.PRESENCIAL,
                "jornada_referencia": "",
                "acuerdo_ministerial": "",
                "fecha_acuerdo": "",
                "fuente_oficial": "",
                "url_fuente": "",
                "activa": "on",
            },
        )
        self.assertRedirects(
            response,
            reverse("catalogos:carrera_detalle", args=(self.carrera.uuid,)),
        )
        evento = EventoAuditoria.objects.get(
            modelo="catalogos.CarreraCatalogo",
            objeto_id=str(self.carrera.pk),
        )
        self.assertEqual(evento.accion, "ACTUALIZAR")
        self.assertIsNone(evento.institucion)

    def test_referencias_tienen_lista_detalle_crear_editar_y_estado(self):
        self.client.force_login(self.superusuario)
        for tipo in ("niveles", "tipos-carrera", "areas", "cursos"):
            with self.subTest(tipo=tipo):
                self.assertEqual(self.client.get(reverse("catalogos:referencia_lista", args=[tipo])).status_code, 200)
                self.assertEqual(self.client.get(reverse("catalogos:referencia_crear", args=[tipo])).status_code, 200)
        self.assertEqual(self.client.get(reverse("catalogos:referencia_detalle", args=["niveles", self.nivel.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("catalogos:referencia_editar", args=["niveles", self.nivel.pk])).status_code, 200)
        response = self.client.post(reverse("catalogos:referencia_estado", args=["niveles", self.nivel.pk]))
        self.assertRedirects(response, reverse("catalogos:referencia_detalle", args=["niveles", self.nivel.pk]))
        self.nivel.refresh_from_db()
        self.assertFalse(self.nivel.activo)

    def test_carrera_se_desactiva_sin_eliminarse(self):
        self.client.force_login(self.superusuario)
        self.client.post(reverse("catalogos:carrera_estado", args=[self.carrera.uuid]))
        self.carrera.refresh_from_db()
        self.assertFalse(self.carrera.activa)
        self.assertTrue(CarreraCatalogo.objects.filter(pk=self.carrera.pk).exists())
