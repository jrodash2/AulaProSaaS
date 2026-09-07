from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from academico.models import *
from catalogos.models import NivelEducativo
from instituciones.models import Institucion,UsuarioInstitucion
from alumnos.models import Alumno,Inscripcion
from .models import *
from .services import *
class Base(TestCase):
 def setUp(self):
  self.i=Institucion.objects.create(nombre='Colegio',codigo='ADMTEST');self.otro=Institucion.objects.create(nombre='Otro',codigo='ADMOTRO');self.u={}
  for rol in ('DIRECTOR','SECRETARIA','DOCENTE','CONTABILIDAD'):
   u=get_user_model().objects.create_user(username='a'+rol,password='x');UsuarioInstitucion.objects.create(usuario=u,institucion=self.i,rol=rol);self.u[rol]=u
  self.c=CicloEscolar.objects.create(institucion=self.i,nombre='2027',anio=2027,fecha_inicio=date(2027,1,1),fecha_fin=date(2027,11,1));n=NivelEducativo.objects.create(codigo='AN',nombre='Nivel');self.o=OfertaAcademica.objects.create(institucion=self.i,ciclo=self.c,nivel=n,nombre_mostrado='Oferta',codigo_interno='O',origen='PERSONALIZADA');self.g=GradoInstitucion.objects.create(institucion=self.i,ciclo=self.c,oferta=self.o,codigo='G',nombre='Primero');self.s=Seccion.objects.create(institucion=self.i,ciclo=self.c,grado=self.g,codigo='A',nombre='A');self.cfg=ConfiguracionAdmision.objects.create(institucion=self.i,admisiones_abiertas=True,ciclo_predeterminado=self.c);self.a=Aspirante.objects.create(institucion=self.i,nombres='María',apellidos='López',fecha_nacimiento=date(2018,1,1),sexo='F',cui='1234567890123');self.e=EncargadoAspirante.objects.create(institucion=self.i,aspirante=self.a,nombres='Ana',apellidos='López',telefono='555',correo='ana@example.com');self.sol=SolicitudAdmision.objects.create(institucion=self.i,aspirante=self.a,ciclo_solicitado=self.c,oferta_solicitada=self.o,grado_solicitado=self.g,creada_por=self.u['DIRECTOR'])
 def post_publico(self,**extra):
  d={'nombres':'Pedro','apellidos':'Pérez','fecha_nacimiento':'2018-01-01','cui':'','encargado_nombres':'Pablo','encargado_apellidos':'Pérez','telefono':'555','correo':'p@example.com','ciclo':self.c.pk,'oferta':self.o.pk,'grado':self.g.pk,'observaciones':'','website':''};d.update(extra);return self.client.post(reverse('admisiones:publica',args=[self.i.codigo]),d)
class ModeloPublicoTests(Base):
 def test_aspirante_no_crea_alumno(self):self.assertEqual(Alumno.objects.count(),0)
 def test_correlativo(self):self.assertEqual(self.sol.numero_solicitud,'ADM-2027-00001')
 def test_correlativo_tenant(self):
  self.assertTrue(self.sol.numero_solicitud.startswith('ADM-2027-'))
 def test_tenant_solicitud(self):
  self.sol.institucion=self.otro;self.assertRaises(ValidationError,self.sol.save)
 def test_fecha_futura(self):self.assertRaises(ValidationError,Aspirante.objects.create,institucion=self.i,nombres='X',apellidos='Y',fecha_nacimiento=date(2030,1,1))
 def test_publica_valida(self):self.assertContains(self.post_publico(),'Tu solicitud fue recibida')
 def test_publica_cerrada(self):self.cfg.admisiones_abiertas=False;self.cfg.save();self.assertEqual(self.client.get(reverse('admisiones:publica',args=[self.i.codigo])).status_code,404)
 def test_honeypot(self):self.post_publico(website='spam');self.assertEqual(Aspirante.objects.count(),1)
 def test_token_invalido(self):self.assertEqual(self.client.get('/admisiones/estado/00000000-0000-0000-0000-000000000000/').status_code,404)
 def test_posible_duplicado(self):self.assertTrue(posibles_duplicados(self.i,'Otra','Persona',date(2010,1,1),self.a.cui,''))
 def test_documento_peligroso(self):
  t=TipoDocumentoAdmision.objects.create(institucion=self.i,codigo='P',nombre='Partida');d=DocumentoAdmision(institucion=self.i,solicitud=self.sol,tipo=t,archivo=SimpleUploadedFile('x.exe',b'MZ'),nombre_original='x.exe');self.assertRaises(ValidationError,d.save)
class ProcesoTests(Base):
 def test_evaluacion_maximo(self):
  t=TipoEvaluacionAdmision.objects.create(institucion=self.i,nombre='Mate',punteo_maximo=Decimal('100'));self.assertRaises(ValidationError,EvaluacionAdmision.objects.create,institucion=self.i,solicitud=self.sol,tipo_evaluacion=t,punteo=101,evaluado_por=self.u['DIRECTOR'])
 def test_evaluacion_no_aprueba(self):
  t=TipoEvaluacionAdmision.objects.create(institucion=self.i,nombre='Mate',punteo_maximo=100);EvaluacionAdmision.objects.create(institucion=self.i,solicitud=self.sol,tipo_evaluacion=t,punteo=100,evaluado_por=self.u['DIRECTOR']);self.sol.refresh_from_db();self.assertEqual(self.sol.estado,'NUEVA')
 def test_rechazo_requiere_motivo(self):self.assertRaises(ValidationError,cambiar_estado,self.sol,'RECHAZADA','')
 def test_cancelada_no_convierte(self):self.sol.estado='CANCELADA';self.sol.save();self.assertRaises(ValidationError,convertir_solicitud_a_alumno,self.sol,self.s)
 def test_conversion_completa(self):
  self.sol.estado='APROBADA';self.sol.save();a,ins=convertir_solicitud_a_alumno(self.sol,self.s,self.u['DIRECTOR']);self.assertTrue(a.familia_id);self.assertEqual(ins.estado,'ACTIVA');self.sol.refresh_from_db();self.assertEqual(self.sol.estado,'INSCRITA')
 def test_conversion_no_duplica_alumno(self):
  existente=Alumno.objects.create(institucion=self.i,cui=self.a.cui,primer_nombre='María',primer_apellido='López',fecha_nacimiento=self.a.fecha_nacimiento,sexo='F',fecha_ingreso=date.today());self.sol.estado='APROBADA';self.sol.save();a,_=convertir_solicitud_a_alumno(self.sol,self.s,self.u['DIRECTOR']);self.assertEqual(a,existente)
 def test_no_duplica_inscripcion(self):
  self.sol.estado='APROBADA';self.sol.save();convertir_solicitud_a_alumno(self.sol,self.s,self.u['DIRECTOR']);self.assertRaises(ValidationError,convertir_solicitud_a_alumno,self.sol,self.s,self.u['DIRECTOR'])
 def test_director_accede(self):self.client.force_login(self.u['DIRECTOR']);self.assertEqual(self.client.get(reverse('admisiones:dashboard')).status_code,200)
 def test_docente_bloqueado(self):self.client.force_login(self.u['DOCENTE']);self.assertEqual(self.client.get(reverse('admisiones:dashboard')).status_code,403)
 def test_estado_solo_post(self):self.client.force_login(self.u['DIRECTOR']);self.assertEqual(self.client.get(reverse('admisiones:estado',args=[self.sol.pk])).status_code,405)
