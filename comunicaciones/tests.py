from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from alumnos.models import AlumnoEncargado,Encargado
from instituciones.models import UsuarioInstitucion
from tareas.services import cambiar_estado
from tareas.tests import Base
from .models import AdjuntoComunicacion,Comunicacion,ComunicacionAudiencia,ComunicacionDestino,Notificacion
from .services import crear_notificacion,notificar_tarea,publicar,resolver_destinatarios,sincronizar_notificaciones
class ComunicacionBase(Base):
 def setUp(self):
  super().setUp();self.padre=get_user_model().objects.create_user("cpadre",password="x");self.au=get_user_model().objects.create_user("calumno",password="x");UsuarioInstitucion.objects.create(usuario=self.padre,institucion=self.a,rol="PADRE");UsuarioInstitucion.objects.create(usuario=self.au,institucion=self.a,rol="ALUMNO");e=Encargado.objects.create(institucion=self.a,usuario=self.padre,nombres="P",apellidos="P",telefono="1");AlumnoEncargado.objects.create(institucion=self.a,alumno=self.al,encargado=e,parentesco="PADRE");self.al.usuario=self.au;self.al.save()
 def com(self,**kw):
  data={"institucion":self.a,"titulo":"Circular","contenido":"Contenido","creada_por":self.u["ADMINISTRADOR"],"fecha_publicacion":timezone.now()};data.update(kw);return Comunicacion.objects.create(**data)
 def destino(self,c,tipo="INSTITUCION",**kw):return ComunicacionDestino.objects.create(institucion=self.a,comunicacion=c,tipo_destino=tipo,**kw)
class ModeloTests(ComunicacionBase):
 def test_fechas_validas(self):
  c=self.com();c.fecha_expiracion=c.fecha_publicacion-timedelta(days=1);self.assertRaises(ValidationError,c.save)
 def test_programada_requiere_futuro(self):self.assertRaises(ValidationError,self.com,estado="PROGRAMADA",fecha_publicacion=timezone.now()-timedelta(days=1))
 def test_anulada_historica(self):
  c=self.com();c.estado="ANULADA";c.motivo_anulacion="Error";c.save();self.assertTrue(Comunicacion.objects.filter(pk=c.pk).exists())
 def test_destino_otro_tenant_rechazado(self):
  c=self.com();self.s.__class__.objects.filter(pk=self.s.pk).update(institucion=self.b);self.s.refresh_from_db();self.assertRaises(ValidationError,ComunicacionDestino.objects.create,institucion=self.a,comunicacion=c,tipo_destino="SECCION",seccion=self.s)
 def test_notificacion_unica(self):
  c=self.com();Notificacion.objects.create(institucion=self.a,comunicacion=c,usuario=self.padre,titulo="x",origen_id=str(c.pk));self.assertRaises((ValidationError,IntegrityError),Notificacion.objects.create,institucion=self.a,comunicacion=c,usuario=self.padre,titulo="x",origen_id=str(c.pk))
class ResolucionTests(ComunicacionBase):
 def usuarios(self,c):return set(resolver_destinatarios(c))
 def test_institucion(self):
  c=self.com();self.destino(c);self.assertIn(self.padre.pk,self.usuarios(c))
 def test_rol(self):
  c=self.com();self.destino(c,"ROL",rol="PADRE");self.assertEqual(self.usuarios(c),{self.padre.pk})
 def test_grado_padres(self):
  c=self.com();ComunicacionAudiencia.objects.create(comunicacion=c,rol="PADRE");self.destino(c,"GRADO",grado=self.g,ciclo=self.c);self.assertIn(self.padre.pk,self.usuarios(c))
 def test_seccion_alumnos(self):
  c=self.com();ComunicacionAudiencia.objects.create(comunicacion=c,rol="ALUMNO");self.destino(c,"SECCION",seccion=self.s,ciclo=self.c);self.assertIn(self.au.pk,self.usuarios(c))
 def test_curso_docente(self):
  c=self.com();ComunicacionAudiencia.objects.create(comunicacion=c,rol="DOCENTE");self.destino(c,"CURSO",curso=self.curso,ciclo=self.c);self.assertIn(self.u["DOCENTE"].pk,self.usuarios(c))
 def test_usuario(self):
  c=self.com();self.destino(c,"USUARIO",usuario=self.padre);self.assertEqual(self.usuarios(c),{self.padre.pk})
class FlujoTests(ComunicacionBase):
 def test_admin_publica_y_sincroniza(self):
  c=self.com();self.destino(c,"ROL",rol="PADRE");publicar(self.req(),c);self.assertTrue(c.notificaciones.filter(usuario=self.padre).exists())
 def test_secretaria_publica(self):
  c=self.com();self.destino(c,"ROL",rol="PADRE");publicar(self.req("SECRETARIA"),c);self.assertEqual(c.estado,"PUBLICADA")
 def test_docente_publica_su_seccion(self):
  c=self.com(creada_por=self.u["DOCENTE"]);ComunicacionAudiencia.objects.create(comunicacion=c,rol="ALUMNO");self.destino(c,"SECCION",seccion=self.s,ciclo=self.c);publicar(self.req("DOCENTE"),c);self.assertEqual(c.estado,"PUBLICADA")
 def test_docente_no_publica_global(self):
  c=self.com(creada_por=self.u["DOCENTE"]);self.destino(c);self.assertRaises(PermissionDenied,publicar,self.req("DOCENTE"),c)
 def test_programacion_command(self):
  c=self.com(estado="PROGRAMADA",fecha_publicacion=timezone.now()+timedelta(days=1));self.destino(c,"ROL",rol="PADRE");Comunicacion.objects.filter(pk=c.pk).update(fecha_publicacion=timezone.now()-timedelta(minutes=1));call_command("publicar_comunicaciones_programadas");c.refresh_from_db();self.assertEqual(c.estado,"PUBLICADA")
 def test_padre_solo_abre_suya(self):
  c=self.com(estado="PUBLICADA");n=Notificacion.objects.create(institucion=self.a,comunicacion=c,usuario=self.padre,titulo="x",origen_id=str(c.pk));self.client.force_login(self.padre);self.client.get(reverse("comunicaciones:abrir_notificacion",args=[n.pk]));n.refresh_from_db();self.assertTrue(n.leida)
 def test_usuario_no_marca_ajena(self):
  n=Notificacion.objects.create(institucion=self.a,usuario=self.padre,titulo="x",tipo_origen="X",origen_id="1");self.client.force_login(self.au);self.assertEqual(self.client.get(reverse("comunicaciones:abrir_notificacion",args=[n.pk])).status_code,404)
 def test_adjunto_exe_rechazado(self):
  c=self.com();a=AdjuntoComunicacion(institucion=self.a,comunicacion=c,archivo=SimpleUploadedFile("x.exe",b"MZ"),nombre_original="x.exe");self.assertRaises(ValidationError,a.save)
 def test_tarea_notifica_y_no_duplica(self):
  t=self.tarea();cambiar_estado(self.req("DOCENTE"),t,"PUBLICADA");notificar_tarea(t);self.assertEqual(Notificacion.objects.filter(tipo_origen="TAREA",origen_id=str(t.pk),usuario=self.au).count(),1);self.assertEqual(Notificacion.objects.filter(tipo_origen="TAREA",origen_id=str(t.pk),usuario=self.padre).count(),1)
