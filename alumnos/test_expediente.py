import shutil,tempfile
from datetime import date,timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from instituciones.models import UsuarioInstitucion
from .models import DocumentoAlumno,RequisitoDocumentoAlumno,TipoDocumentoAlumno
from .services import documentos_por_vencer,resumen_expediente
from .tests import Base

class ExpedienteTests(Base):
 def setUp(self):
  super().setUp();self.tmp=tempfile.mkdtemp();self.override=override_settings(MEDIA_ROOT=self.tmp);self.override.enable();self.al=self.alumno();self.ins=self.inscribir(self.al)
  self.tipo=TipoDocumentoAlumno.objects.create(institucion=self.a,codigo='PARTIDA',nombre='Partida',obligatorio=True,visible_portal=True)
  self.req=RequisitoDocumentoAlumno.objects.create(institucion=self.a,tipo_documento=self.tipo,obligatorio=True)
 def tearDown(self):self.override.disable();shutil.rmtree(self.tmp,ignore_errors=True);super().tearDown()
 def archivo(self,nombre='doc.pdf',contenido=b'%PDF-1.4 test'):return SimpleUploadedFile(nombre,contenido,content_type='application/pdf')
 def documento(self,estado='APROBADO',**kw):return DocumentoAlumno.objects.create(institucion=self.a,alumno=self.al,tipo_documento=self.tipo,archivo=self.archivo(),nombre_original='partida.pdf',estado=estado,cargado_por=self.users['ADMINISTRADOR'],**kw)
 def test_tipo_documento_es_tenant(self):
  with self.assertRaises(ValidationError):RequisitoDocumentoAlumno.objects.create(institucion=self.b,tipo_documento=self.tipo)
 def test_documento_rechaza_alumno_otro_tenant(self):
  with self.assertRaises(ValidationError):DocumentoAlumno.objects.create(institucion=self.a,alumno=self.alumno(self.b,cui='9999999999999'),tipo_documento=self.tipo,archivo=self.archivo(),cargado_por=self.users['ADMINISTRADOR'])
 def test_archivo_permitido(self):self.assertTrue(self.documento().archivo.name.endswith('.pdf'))
 def test_archivo_peligroso_rechazado(self):
  with self.assertRaises(ValidationError):DocumentoAlumno.objects.create(institucion=self.a,alumno=self.al,tipo_documento=self.tipo,archivo=self.archivo('evil.js',b'alert(1)'),cargado_por=self.users['ADMINISTRADOR'])
 def test_vencimiento_derivado(self):self.assertEqual(self.documento(fecha_vencimiento=date.today()-timedelta(days=1)).estado_vigente,'VENCIDO')
 def test_pendiente_cero_por_ciento(self):self.assertEqual(resumen_expediente(self.al)['porcentaje'],0)
 def test_aprobado_completa(self):self.documento();self.assertEqual(resumen_expediente(self.al)['porcentaje'],100)
 def test_opcional_no_reduce_porcentaje(self):
  t=TipoDocumentoAlumno.objects.create(institucion=self.a,codigo='FOTO',nombre='Foto',obligatorio=False);RequisitoDocumentoAlumno.objects.create(institucion=self.a,tipo_documento=t,obligatorio=False);self.documento();self.assertEqual(resumen_expediente(self.al)['porcentaje'],100)
 def test_no_aplica_excluye_denominador(self):
  DocumentoAlumno.objects.create(institucion=self.a,alumno=self.al,tipo_documento=self.tipo,estado='NO_APLICA',observaciones='No corresponde',cargado_por=self.users['ADMINISTRADOR']);self.assertEqual(resumen_expediente(self.al)['total'],0)
 def test_rechazado_no_suma(self):self.documento(estado='RECHAZADO',motivo_rechazo='Ilegible');self.assertEqual(resumen_expediente(self.al)['porcentaje'],0)
 def test_permanente_aprobado_sigue_valido(self):self.documento();self.assertEqual(resumen_expediente(self.al)['aprobados'],1)
 def test_requisito_por_grado(self):
  t=TipoDocumentoAlumno.objects.create(institucion=self.a,codigo='GRADO',nombre='Grado');RequisitoDocumentoAlumno.objects.create(institucion=self.a,tipo_documento=t,aplica_a_grado=self.ga);self.assertEqual(len(resumen_expediente(self.al)['items']),2)
 def test_documentos_por_vencer(self):self.documento(fecha_vencimiento=date.today()+timedelta(days=10));self.assertEqual(documentos_por_vencer(self.a).count(),1)
 def test_descarga_admin_y_tenant(self):
  d=self.documento();self.client.force_login(self.users['ADMINISTRADOR']);self.assertEqual(self.client.get(reverse('alumnos:documento_descargar',args=[d.pk])).status_code,200)
 def test_docente_y_contabilidad_bloqueados(self):
  for rol in ('DOCENTE','CONTABILIDAD'):
   self.client.force_login(self.users[rol]);self.assertEqual(self.client.get(reverse('alumnos:expediente_alumno',args=[self.al.pk])).status_code,403)
 def test_endpoint_revision_es_post(self):
  d=self.documento(estado='ENTREGADO');self.client.force_login(self.users['SECRETARIA']);self.assertEqual(self.client.get(reverse('alumnos:documento_revisar',args=[d.pk])).status_code,405);self.client.post(reverse('alumnos:documento_revisar',args=[d.pk]),{'estado':'APROBADO'});d.refresh_from_db();self.assertEqual(d.estado,'APROBADO')
 def test_reemplazo_conserva_anterior(self):
  viejo=self.documento(estado='RECHAZADO',motivo_rechazo='Ilegible');nuevo=DocumentoAlumno.objects.create(institucion=self.a,alumno=self.al,tipo_documento=self.tipo,archivo=self.archivo('nuevo.pdf'),reemplaza_a=viejo,cargado_por=self.users['ADMINISTRADOR']);self.assertTrue(DocumentoAlumno.objects.filter(pk=viejo.pk).exists());self.assertEqual(nuevo.reemplaza_a,viejo)
 def test_exportacion_xlsx(self):
  self.client.force_login(self.users['ADMINISTRADOR']);r=self.client.get(reverse('alumnos:expedientes_exportar'));self.assertEqual(r.status_code,200);self.assertIn('spreadsheet',r.headers['Content-Type'])
