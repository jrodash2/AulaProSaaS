from datetime import date
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase
from django.urls import reverse
from academico.models import CicloEscolar, CursoInstitucion, GradoInstitucion, OfertaAcademica, Seccion
from alumnos.models import Alumno, Inscripcion
from auditoria.models import EventoAuditoria
from catalogos.models import NivelEducativo
from docentes.models import AsignacionDocente, AsignacionGuia, Docente
from instituciones.models import Institucion, UsuarioInstitucion
from .models import RegistroAsistencia, SesionAsistencia
from .services import anular_sesion, cerrar_sesion, crear_sesion, guardar_registros, justificar, puede_crear, reabrir_sesion, resumen_alumno

class AsistenciaBase(TestCase):
    def setUp(self):
        self.a=Institucion.objects.create(nombre="A",codigo="AS-A"); self.b=Institucion.objects.create(nombre="B",codigo="AS-B")
        self.users={}
        for rol in ("ADMINISTRADOR","DIRECTOR","SECRETARIA","DOCENTE","CONTABILIDAD"):
            u=get_user_model().objects.create_user(username=f"as-{rol.lower()}",password="segura-123"); self.users[rol]=u; UsuarioInstitucion.objects.create(usuario=u,institucion=self.a,rol=rol)
        self.ciclo=CicloEscolar.objects.create(institucion=self.a,nombre="2026",anio=2026,fecha_inicio=date(2026,1,1),fecha_fin=date(2026,11,30),es_actual=True)
        self.ciclo_b=CicloEscolar.objects.create(institucion=self.b,nombre="2026",anio=2026,fecha_inicio=date(2026,1,1),fecha_fin=date(2026,11,30))
        nivel=NivelEducativo.objects.create(codigo="AS-N",nombre="Básico")
        self.oferta=OfertaAcademica.objects.create(institucion=self.a,ciclo=self.ciclo,nivel=nivel,nombre_mostrado="Básico",codigo_interno="BAS",origen="PERSONALIZADA")
        self.oferta_b=OfertaAcademica.objects.create(institucion=self.b,ciclo=self.ciclo_b,nivel=nivel,nombre_mostrado="B",codigo_interno="B",origen="PERSONALIZADA")
        self.grado=GradoInstitucion.objects.create(institucion=self.a,ciclo=self.ciclo,oferta=self.oferta,codigo="1",nombre="Primero")
        self.grado_b=GradoInstitucion.objects.create(institucion=self.b,ciclo=self.ciclo_b,oferta=self.oferta_b,codigo="1",nombre="Primero")
        self.seccion=Seccion.objects.create(institucion=self.a,ciclo=self.ciclo,grado=self.grado,codigo="A",nombre="A")
        self.seccion_b=Seccion.objects.create(institucion=self.b,ciclo=self.ciclo_b,grado=self.grado_b,codigo="A",nombre="A")
        self.curso=CursoInstitucion.objects.create(institucion=self.a,ciclo=self.ciclo,oferta=self.oferta,grado=self.grado,nombre_personalizado="Matemática",nombre_mostrado="Matemática",origen="INSTITUCIONAL")
        self.alumno=Alumno.objects.create(institucion=self.a,cui="1234567890123",primer_nombre="Ana",primer_apellido="López",fecha_nacimiento=date(2015,1,1),sexo="F",fecha_ingreso=date(2026,1,2))
        self.inscripcion=Inscripcion.objects.create(institucion=self.a,alumno=self.alumno,ciclo=self.ciclo,oferta_academica=self.oferta,grado=self.grado,seccion=self.seccion,fecha_inscripcion=date(2026,1,3))
        self.docente=Docente.objects.create(institucion=self.a,usuario=self.users["DOCENTE"],primer_nombre="Dora",primer_apellido="Docente",telefono="1",fecha_ingreso=date(2026,1,1))
        self.asignacion=AsignacionDocente.objects.create(institucion=self.a,ciclo=self.ciclo,docente=self.docente,oferta_academica=self.oferta,grado=self.grado,seccion=self.seccion,curso=self.curso,fecha_inicio=date(2026,1,1))
        self.factory=RequestFactory()
    def request(self,rol="ADMINISTRADOR"):
        req=self.factory.post("/"); req.user=self.users[rol]; req.institucion=self.a; req.asignacion_institucion=UsuarioInstitucion.objects.get(usuario=req.user,institucion=self.a); req.META["REMOTE_ADDR"]="127.0.0.1"; return req
    def sesion(self,tipo="GENERAL",estado="ABIERTA",fecha=date(2026,8,24)):
        kwargs={"institucion":self.a,"ciclo":self.ciclo,"fecha":fecha,"tipo":tipo,"oferta_academica":self.oferta,"grado":self.grado,"seccion":self.seccion,"creada_por":self.users["ADMINISTRADOR"],"estado":estado}
        if tipo=="CURSO": kwargs.update(curso=self.curso,asignacion_docente=self.asignacion,docente=self.docente)
        return SesionAsistencia.objects.create(**kwargs)
    def registro(self,sesion=None,estado="SIN_MARCAR"):
        return RegistroAsistencia.objects.create(institucion=self.a,sesion=sesion or self.sesion(),alumno=self.alumno,inscripcion=self.inscripcion,estado=estado,registrado_por=self.users["ADMINISTRADOR"])

class ModeloTests(AsistenciaBase):
    def test_registro_unico_alumno_sesion(self):
        s=self.sesion(); self.registro(s)
        with self.assertRaises(ValidationError): self.registro(s)
    def test_sesion_general_unica_fecha_seccion(self):
        self.sesion()
        with self.assertRaises(ValidationError): self.sesion()
    def test_sesion_curso_consistente(self):
        s=self.sesion("CURSO"); self.assertEqual(s.curso,self.curso)
        s.curso=None
        with self.assertRaises(ValidationError): s.save()
    def test_general_rechaza_curso(self):
        s=self.sesion(); s.curso=self.curso
        with self.assertRaises(ValidationError): s.save()
    def test_alumno_debe_pertenecer_institucion(self):
        otro=Alumno.objects.create(institucion=self.b,cui="9999999999999",primer_nombre="B",primer_apellido="B",fecha_nacimiento=date(2015,1,1),sexo="F",fecha_ingreso=date(2026,1,1))
        with self.assertRaises(ValidationError): RegistroAsistencia.objects.create(institucion=self.a,sesion=self.sesion(),alumno=otro,inscripcion=self.inscripcion,registrado_por=self.users["ADMINISTRADOR"])
    def test_inscripcion_debe_coincidir(self):
        otro=Alumno.objects.create(institucion=self.a,cui="8888888888888",primer_nombre="B",primer_apellido="B",fecha_nacimiento=date(2015,1,1),sexo="F",fecha_ingreso=date(2026,1,1))
        with self.assertRaises(ValidationError): RegistroAsistencia.objects.create(institucion=self.a,sesion=self.sesion(),alumno=otro,inscripcion=self.inscripcion,registrado_por=self.users["ADMINISTRADOR"])
    def test_no_cierra_con_sin_marcar(self):
        s=self.sesion(); self.registro(s)
        with self.assertRaises(ValidationError): cerrar_sesion(s,self.users["ADMINISTRADOR"])
    def test_cerrar_cambia_estado(self):
        s=self.sesion(); self.registro(s,"PRESENTE"); cerrar_sesion(s,self.users["ADMINISTRADOR"]); self.assertEqual(s.estado,"CERRADA")
    def test_cerrada_bloquea_edicion(self):
        s=self.sesion(estado="CERRADA"); r=self.registro(s,"PRESENTE")
        with self.assertRaises(ValidationError): guardar_registros(s,{str(r.pk):"AUSENTE"},self.users["DOCENTE"])
    def test_anular_conserva_registros(self):
        s=self.sesion(); self.registro(s); anular_sesion(s,self.users["ADMINISTRADOR"],"Duplicada"); self.assertEqual(s.registros.count(),1); self.assertEqual(s.estado,"ANULADA")

class PermisosYTenantTests(AsistenciaBase):
    def test_docente_puede_curso_asignado(self): self.assertTrue(puede_crear(self.request("DOCENTE"),tipo="CURSO",seccion=self.seccion,curso=self.curso))
    def test_docente_no_puede_otra_asignacion(self):
        otro=CursoInstitucion.objects.create(institucion=self.a,ciclo=self.ciclo,oferta=self.oferta,grado=self.grado,nombre_personalizado="Idioma",nombre_mostrado="Idioma",origen="INSTITUCIONAL")
        self.assertFalse(puede_crear(self.request("DOCENTE"),tipo="CURSO",seccion=self.seccion,curso=otro))
    def test_docente_guia_puede_general(self):
        AsignacionGuia.objects.create(institucion=self.a,ciclo=self.ciclo,seccion=self.seccion,docente=self.docente,fecha_inicio=date(2026,1,1)); self.assertTrue(puede_crear(self.request("DOCENTE"),tipo="GENERAL",seccion=self.seccion))
    def test_docente_no_guia_no_general(self): self.assertFalse(puede_crear(self.request("DOCENTE"),tipo="GENERAL",seccion=self.seccion))
    def test_docente_no_reabre(self):
        s=self.sesion(estado="CERRADA"); self.client.force_login(self.users["DOCENTE"]); self.assertEqual(self.client.post(reverse("asistencia:reabrir",args=[s.pk]),{"motivo":"x"}).status_code,403)
    def test_administrador_reabre_y_audita(self):
        s=self.sesion(estado="CERRADA"); req=self.request(); reabrir_sesion(s,req.user,"Corrección",req); self.assertTrue(EventoAuditoria.objects.filter(accion="REABRIR_ASISTENCIA",objeto_id=s.pk).exists())
    def test_listado_aisla_tenant(self):
        self.sesion(); self.client.force_login(self.users["ADMINISTRADOR"]); response=self.client.get(reverse("asistencia:sesiones")); self.assertNotContains(response,self.seccion_b.nombre+" imposible")
    def test_detalle_otro_tenant_404(self):
        otro=SesionAsistencia.objects.create(institucion=self.b,ciclo=self.ciclo_b,fecha=date(2026,8,24),tipo="GENERAL",oferta_academica=self.oferta_b,grado=self.grado_b,seccion=self.seccion_b,creada_por=self.users["ADMINISTRADOR"])
        self.client.force_login(self.users["ADMINISTRADOR"]); self.assertEqual(self.client.get(reverse("asistencia:detalle",args=[otro.pk])).status_code,404)
    def test_contabilidad_sin_acceso(self):
        self.client.force_login(self.users["CONTABILIDAD"]); self.assertEqual(self.client.get(reverse("asistencia:dashboard")).status_code,403)
    def test_secretaria_no_modifica_sesion_curso(self):
        s=self.sesion("CURSO"); self.client.force_login(self.users["SECRETARIA"]); self.assertEqual(self.client.get(reverse("asistencia:tomar",args=[s.pk])).status_code,403)

class FlujoYCalculosTests(AsistenciaBase):
    def test_crear_genera_registros_sin_marcar(self):
        s,creada=crear_sesion(request=self.request(),ciclo=self.ciclo,oferta=self.oferta,grado=self.grado,seccion=self.seccion,tipo="GENERAL",fecha=date(2026,8,23)); self.assertTrue(creada); self.assertEqual(s.registros.get().estado,"SIN_MARCAR")
    def test_no_crea_sesion_vacia(self):
        self.inscripcion.estado="RETIRADA"; self.inscripcion.fecha_retiro=date(2026,8,1); self.inscripcion.motivo_retiro="x"; self.inscripcion.save()
        with self.assertRaises(ValidationError): crear_sesion(request=self.request(),ciclo=self.ciclo,oferta=self.oferta,grado=self.grado,seccion=self.seccion,tipo="GENERAL",fecha=date(2026,8,23))
    def test_justificacion_guarda_trazabilidad(self):
        r=self.registro(estado="AUSENTE"); justificar(r,self.users["SECRETARIA"],"Cita médica"); self.assertTrue(r.justificada); self.assertEqual(r.justificada_por,self.users["SECRETARIA"]); self.assertIsNotNone(r.fecha_justificacion)
    def test_justificar_no_convierte_presencia(self):
        r=self.registro(estado="AUSENTE"); justificar(r,self.users["SECRETARIA"],"Cita"); self.assertEqual(r.estado,"AUSENTE")
    def test_porcentaje_presente_y_tarde_cuentan(self):
        s1=self.sesion(estado="CERRADA"); self.registro(s1,"PRESENTE"); s2=self.sesion(estado="CERRADA",fecha=date(2026,8,25)); self.registro(s2,"TARDE"); self.assertEqual(resumen_alumno(self.alumno,self.ciclo)["porcentaje"],100)
    def test_ausente_no_cuenta(self):
        s=self.sesion(estado="CERRADA"); self.registro(s,"AUSENTE"); self.assertEqual(resumen_alumno(self.alumno,self.ciclo)["porcentaje"],0)
    def test_anulada_no_cuenta(self):
        s=self.sesion(estado="ANULADA"); self.registro(s,"AUSENTE"); self.assertEqual(resumen_alumno(self.alumno,self.ciclo)["total"],0)
    def test_excel_respeta_tenant(self):
        self.sesion(); self.client.force_login(self.users["ADMINISTRADOR"]); response=self.client.get(reverse("asistencia:exportar_sesiones")); self.assertEqual(response.status_code,200); self.assertIn("spreadsheet",response["Content-Type"])
