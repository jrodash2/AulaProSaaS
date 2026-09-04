from datetime import date,timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from tareas.tests import Base
from alumnos.models import Alumno,AlumnoEncargado,Encargado,Inscripcion
from instituciones.models import UsuarioInstitucion
from .models import *
from .services import registros_visibles_para_usuario,cerrar_registro,notificar_encargados
class SeguimientoBase(Base):
 def setUp(self):
  super().setUp();self.users=self.u
  self.users["DIRECTOR"]=get_user_model().objects.create_user(username="tdir",password="x");UsuarioInstitucion.objects.create(usuario=self.users["DIRECTOR"],institucion=self.a,rol="DIRECTOR")
  self.padre=get_user_model().objects.create_user(username="tpad",password="x");UsuarioInstitucion.objects.create(usuario=self.padre,institucion=self.a,rol="PADRE");self.enc=Encargado.objects.create(institucion=self.a,usuario=self.padre,nombres="P",apellidos="P",telefono="1");AlumnoEncargado.objects.create(institucion=self.a,alumno=self.al,encargado=self.enc,parentesco="PADRE")
  self.cat=CategoriaSeguimiento.objects.create(institucion=self.a,codigo="PUNT",nombre="Puntualidad",tipo="INCIDENCIA")
 def reg(self,**kw):
  d=dict(institucion=self.a,alumno=self.al,inscripcion=self.ins,ciclo=self.c,categoria=self.cat,tipo="INCIDENCIA",fecha=date.today(),titulo="Llegadas tarde",descripcion="Seguimiento",gravedad="MEDIA",confidencialidad="DOCENTES",registrado_por=self.users["ADMINISTRADOR"]);d.update(kw);return RegistroSeguimiento.objects.create(**d)
 def request(self,user):
  r=RequestFactory().post('/');r.user=user;r.institucion=self.a;r.asignacion_institucion=UsuarioInstitucion.objects.get(usuario=user,institucion=self.a);return r
class ModelosTests(SeguimientoBase):
 def test_categoria_tenant_codigo(self):
  self.assertRaises(ValidationError,CategoriaSeguimiento.objects.create,institucion=self.a,codigo="PUNT",nombre="Otra",tipo="OTRO")
 def test_registro_tenant(self):self.assertRaises(ValidationError,self.reg,institucion=self.b)
 def test_reconocimiento_sin_gravedad(self):self.assertTrue(self.reg(tipo="POSITIVO",gravedad="NO_APLICA").pk)
 def test_reconocimiento_con_gravedad_rechazado(self):self.assertRaises(ValidationError,self.reg,tipo="POSITIVO",gravedad="MEDIA")
 def test_compromiso_y_vencimiento(self):
  c=CompromisoSeguimiento.objects.create(institucion=self.a,registro=self.reg(),descripcion="Mejorar",responsable="ALUMNO",fecha_limite=date.today()-timedelta(days=1),creado_por=self.users["ADMINISTRADOR"]);self.assertEqual(c.estado_vigente,"VENCIDO")
 def test_nota_no_sobrescribe(self):
  r=self.reg();NotaSeguimiento.objects.create(institucion=self.a,registro=r,comentario="Uno",autor=self.users["ADMINISTRADOR"]);NotaSeguimiento.objects.create(institucion=self.a,registro=r,comentario="Dos",autor=self.users["ADMINISTRADOR"]);self.assertEqual(r.notas.count(),2)
 def test_reunion(self):self.assertTrue(ReunionSeguimiento.objects.create(institucion=self.a,alumno=self.al,registro=self.reg(),fecha=timezone.now(),encargado=self.enc,motivo="Conversar",creado_por=self.users["ADMINISTRADOR"]).pk)
 def test_cierre_requiere_conclusion(self):self.assertRaises(ValidationError,self.reg,estado="CERRADO")
 def test_cerrar_preserva_historico(self):
  r=self.reg();cerrar_registro(self.request(self.users["DIRECTOR"]),r,"Acuerdos cumplidos");self.assertEqual((r.estado,r.conclusion),("CERRADO","Acuerdos cumplidos"))
 def test_archivo_peligroso(self):
  a=AdjuntoSeguimiento(institucion=self.a,registro=self.reg(),archivo=SimpleUploadedFile("x.exe",b"MZ"),nombre_original="x.exe",cargado_por=self.users["ADMINISTRADOR"]);self.assertRaises(ValidationError,a.save)
class PermisosTests(SeguimientoBase):
 def test_director_ve_todo(self):self.reg();self.assertEqual(registros_visibles_para_usuario(self.request(self.users["DIRECTOR"])).count(),1)
 def test_docente_ve_alumno_propio(self):self.reg();self.assertEqual(registros_visibles_para_usuario(self.request(self.users["DOCENTE"])).count(),1)
 def test_docente_no_ve_interno(self):self.reg(confidencialidad="INTERNO");self.assertFalse(registros_visibles_para_usuario(self.request(self.users["DOCENTE"])).exists())
 def test_contabilidad_bloqueada(self):self.client.force_login(self.users["CONTABILIDAD"]);self.assertEqual(self.client.get(reverse("seguimiento:dashboard")).status_code,403)
 def test_padre_no_ve_interno(self):
  self.reg(confidencialidad="INTERNO");self.client.force_login(self.padre);self.assertNotContains(self.client.get(reverse("seguimiento:portal",args=[self.al.pk])),"Llegadas tarde")
 def test_padre_ve_autorizado(self):
  self.reg(confidencialidad="PADRES");self.client.force_login(self.padre);self.assertContains(self.client.get(reverse("seguimiento:portal",args=[self.al.pk])),"Llegadas tarde")
 def test_padre_no_ve_otro_alumno(self):
  otro=Alumno.objects.create(institucion=self.a,primer_nombre="X",primer_apellido="Y",fecha_nacimiento=date(2015,1,1),sexo="F",fecha_ingreso=date.today());self.client.force_login(self.padre);self.assertEqual(self.client.get(reverse("seguimiento:portal",args=[otro.pk])).status_code,404)
 def test_notificacion_explicita_idempotente(self):
  r=self.reg(confidencialidad="PADRES");req=self.request(self.users["DIRECTOR"]);notificar_encargados(req,r);notificar_encargados(req,r);self.assertEqual(self.padre.notificaciones.filter(tipo_origen="SEGUIMIENTO",origen_id=str(r.pk)).count(),1)
 def test_accion_cerrar_solo_post(self):
  r=self.reg();self.client.force_login(self.users["DIRECTOR"]);self.assertEqual(self.client.get(reverse("seguimiento:cerrar",args=[r.pk])).status_code,405)

class FormularioSeguimientoQATests(SeguimientoBase):
 def test_nuevo_seguimiento_no_usa_campo_docente_inexistente(self):
  self.client.force_login(self.users["DIRECTOR"])
  response=self.client.get(reverse("seguimiento:nuevo"))
  self.assertEqual(response.status_code,200)

 def test_docentes_del_selector_son_activos_y_del_tenant(self):
  from seguimiento.forms import RegistroForm
  from docentes.models import Docente
  docente_activo=Docente.objects.get(institucion=self.a,usuario=self.users["DOCENTE"])
  docente_inactivo=Docente.objects.create(institucion=self.a,primer_nombre="Inactivo",primer_apellido="Local",telefono="1",fecha_ingreso=date.today(),estado=Docente.Estado.INACTIVO)
  externo=Docente.objects.create(institucion=self.b,primer_nombre="Activo",primer_apellido="Externo",telefono="1",fecha_ingreso=date.today(),estado=Docente.Estado.ACTIVO)
  form=RegistroForm(institucion=self.a,alumnos=Alumno.objects.filter(pk=self.al.pk))
  self.assertIn(docente_activo,form.fields["docente"].queryset)
  self.assertNotIn(docente_inactivo,form.fields["docente"].queryset)
  self.assertNotIn(externo,form.fields["docente"].queryset)
