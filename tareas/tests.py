from datetime import date,timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import RequestFactory,TestCase
from django.urls import reverse
from django.utils import timezone
from academico.models import CicloEscolar,CursoInstitucion,GradoInstitucion,OfertaAcademica,Seccion
from alumnos.models import Alumno,Inscripcion
from catalogos.models import NivelEducativo
from docentes.models import AsignacionDocente,Docente
from instituciones.models import Institucion,UsuarioInstitucion
from .models import AdjuntoTarea,EntregaTarea,Tarea
from .services import agregar_adjunto,cambiar_estado,crear_tarea,sincronizar_entregas_tarea
class Base(TestCase):
 def setUp(self):
  self.a=Institucion.objects.create(nombre="A",codigo="TA");self.b=Institucion.objects.create(nombre="B",codigo="TB");self.u={}
  for rol in ("ADMINISTRADOR","DOCENTE","SECRETARIA","CONTABILIDAD"):
   u=get_user_model().objects.create_user(username="t"+rol,password="x");UsuarioInstitucion.objects.create(usuario=u,institucion=self.a,rol=rol);self.u[rol]=u
  self.c=CicloEscolar.objects.create(institucion=self.a,nombre="2026",anio=2026,fecha_inicio=date(2026,1,1),fecha_fin=date(2026,12,1));n=NivelEducativo.objects.create(codigo="TN",nombre="N");self.o=OfertaAcademica.objects.create(institucion=self.a,ciclo=self.c,nivel=n,nombre_mostrado="O",codigo_interno="O",origen="PERSONALIZADA");self.g=GradoInstitucion.objects.create(institucion=self.a,ciclo=self.c,oferta=self.o,codigo="G",nombre="G");self.s=Seccion.objects.create(institucion=self.a,ciclo=self.c,grado=self.g,codigo="S",nombre="S");self.curso=CursoInstitucion.objects.create(institucion=self.a,ciclo=self.c,oferta=self.o,grado=self.g,nombre_personalizado="Mate",nombre_mostrado="Mate",origen="INSTITUCIONAL");self.d=Docente.objects.create(institucion=self.a,usuario=self.u["DOCENTE"],primer_nombre="D",primer_apellido="D",telefono="1",fecha_ingreso=date(2026,1,1));self.asig=AsignacionDocente.objects.create(institucion=self.a,ciclo=self.c,docente=self.d,oferta_academica=self.o,grado=self.g,seccion=self.s,curso=self.curso,fecha_inicio=date(2026,1,1));self.al=Alumno.objects.create(institucion=self.a,cui="1234567890123",primer_nombre="A",primer_apellido="A",fecha_nacimiento=date(2015,1,1),sexo="F",fecha_ingreso=date(2026,1,1));self.ins=Inscripcion.objects.create(institucion=self.a,alumno=self.al,ciclo=self.c,oferta_academica=self.o,grado=self.g,seccion=self.s,fecha_inscripcion=date(2026,1,1));self.now=timezone.now()
 def req(self,rol="ADMINISTRADOR"):
  r=RequestFactory().post("/");r.user=self.u[rol];r.institucion=self.a;r.asignacion_institucion=UsuarioInstitucion.objects.get(usuario=r.user,institucion=self.a);r.META["REMOTE_ADDR"]="127.0.0.1";return r
 def tarea(self,estado="BORRADOR"):return Tarea.objects.create(institucion=self.a,ciclo=self.c,asignacion_docente=self.asig,curso=self.curso,grado=self.g,seccion=self.s,titulo="Guía",descripcion="",instrucciones="Resolver",fecha_publicacion=self.now,fecha_limite=self.now+timedelta(days=2),estado=estado,creada_por=self.u["DOCENTE"])
class ModeloTests(Base):
 def test_tarea_institucion(self):
  t=self.tarea();t.institucion=self.b;self.assertRaises(ValidationError,t.save)
 def test_asignacion_consistente(self):
  t=self.tarea();t.curso_id=999;self.assertRaises(Exception,t.save)
 def test_fechas_validas(self):
  t=self.tarea();t.fecha_limite=t.fecha_publicacion-timedelta(days=1);self.assertRaises(ValidationError,t.save)
 def test_publicada_visible_alumno(self):
  t=self.tarea("PUBLICADA");self.client.force_login(self.u["ADMINISTRADOR"]);self.assertContains(self.client.get(reverse("tareas:alumno",args=[self.al.pk])),t.titulo)
 def test_borrador_no_visible_alumno(self):
  t=self.tarea();self.client.force_login(self.u["ADMINISTRADOR"]);self.assertNotContains(self.client.get(reverse("tareas:alumno",args=[self.al.pk])),t.titulo)
 def test_tenant_no_ve_tarea(self):
  t=self.tarea();self.client.force_login(self.u["ADMINISTRADOR"]);self.assertEqual(self.client.get(reverse("tareas:detalle",args=[t.pk+999])).status_code,404)
class DocenteEntregaTests(Base):
 def test_docente_crea_propia(self):self.assertEqual(crear_tarea(self.req("DOCENTE"),self.asig,titulo="X",descripcion="",instrucciones="x",fecha_publicacion=self.now,fecha_limite=self.now+timedelta(days=1)).asignacion_docente,self.asig)
 def test_secretaria_no_crea(self):self.assertRaises(PermissionDenied,crear_tarea,self.req("SECRETARIA"),self.asig,titulo="X",descripcion="",instrucciones="x",fecha_publicacion=self.now,fecha_limite=self.now+timedelta(days=1))
 def test_docente_publica_propia(self):
  t=self.tarea();cambiar_estado(self.req("DOCENTE"),t,"PUBLICADA");self.assertEqual(t.estado,"PUBLICADA")
 def test_publicar_genera_entrega(self):
  t=self.tarea();cambiar_estado(self.req("DOCENTE"),t,"PUBLICADA");self.assertEqual(t.entregas.count(),1)
 def test_entrega_unica(self):
  t=self.tarea("PUBLICADA");sincronizar_entregas_tarea(t);self.assertRaises(ValidationError,EntregaTarea.objects.create,institucion=self.a,tarea=t,alumno=self.al,inscripcion=self.ins)
 def test_sincronizar_no_duplica(self):
  t=self.tarea("PUBLICADA");sincronizar_entregas_tarea(t);sincronizar_entregas_tarea(t);self.assertEqual(t.entregas.count(),1)
 def test_retirado_no_se_agrega(self):
  self.ins.estado="RETIRADA";self.ins.fecha_retiro=date.today();self.ins.motivo_retiro="x";self.ins.save();t=self.tarea("PUBLICADA");sincronizar_entregas_tarea(t);self.assertFalse(t.entregas.exists())
 def test_secretaria_no_anula(self):self.assertRaises(PermissionDenied,cambiar_estado,self.req("SECRETARIA"),self.tarea(),"ANULADA","x")
class ArchivosTenantDemoTests(Base):
 def test_pdf_valido(self):
  f=SimpleUploadedFile("guia.pdf",b"%PDF-1.4",content_type="application/pdf");self.assertTrue(agregar_adjunto(self.req(),self.tarea(),f).pk)
 def test_exe_rechazado(self):
  f=SimpleUploadedFile("virus.exe",b"MZ",content_type="application/octet-stream");self.assertRaises(ValidationError,agregar_adjunto,self.req(),self.tarea(),f)
 def test_mime_falso_rechazado(self):
  f=SimpleUploadedFile("guia.pdf",b"evil",content_type="application/x-php");self.assertRaises(ValidationError,agregar_adjunto,self.req(),self.tarea(),f)
 def test_tamano_rechazado(self):
  f=SimpleUploadedFile("grande.pdf",b"x"*(10*1024*1024+1),content_type="application/pdf");self.assertRaises(ValidationError,agregar_adjunto,self.req(),self.tarea(),f)
 def test_descarga_otro_tenant_404(self):
  t=self.tarea();a=AdjuntoTarea.objects.create(institucion=self.a,tarea=t,archivo=SimpleUploadedFile("x.pdf",b"%PDF",content_type="application/pdf"),nombre_original="x.pdf");self.client.force_login(self.u["ADMINISTRADOR"]);self.assertEqual(self.client.get(reverse("tareas:descargar",args=[t.pk+999,a.pk])).status_code,404)
 def test_demo_idempotente(self):
  call_command("crear_demo_aulapro");call_command("crear_demo_aulapro");self.assertEqual(Tarea.objects.filter(institucion__codigo="DEMO").count(),3)
