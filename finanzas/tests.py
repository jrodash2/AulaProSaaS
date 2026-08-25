from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied,ValidationError
from django.test import RequestFactory,TestCase,TransactionTestCase
from django.urls import reverse
from academico.models import CicloEscolar,GradoInstitucion,OfertaAcademica,Seccion
from alumnos.models import Alumno,Familia,Inscripcion
from auditoria.models import EventoAuditoria
from catalogos.models import NivelEducativo
from instituciones.models import Institucion,UsuarioInstitucion
from .models import *
from .services import *
class BaseMixin:
 def build(self):
  self.a=Institucion.objects.create(nombre="A",codigo="FA");self.b=Institucion.objects.create(nombre="B",codigo="FB");self.u={}
  for x in ("ADMINISTRADOR","CONTABILIDAD","SECRETARIA","DIRECTOR","DOCENTE"):
   u=get_user_model().objects.create_user(username="f"+x,password="x");UsuarioInstitucion.objects.create(usuario=u,institucion=self.a,rol=x);self.u[x]=u
  self.c=CicloEscolar.objects.create(institucion=self.a,nombre="2026",anio=2026,fecha_inicio=date(2026,1,1),fecha_fin=date(2026,12,1));n=NivelEducativo.objects.create(codigo="FN",nombre="N");o=OfertaAcademica.objects.create(institucion=self.a,ciclo=self.c,nivel=n,nombre_mostrado="O",codigo_interno="O",origen="PERSONALIZADA");g=GradoInstitucion.objects.create(institucion=self.a,ciclo=self.c,oferta=o,codigo="G",nombre="G");self.s=Seccion.objects.create(institucion=self.a,ciclo=self.c,grado=g,codigo="S",nombre="S");self.f=Familia.objects.create(institucion=self.a,nombre_referencia="Familia");self.al=Alumno.objects.create(institucion=self.a,familia=self.f,cui="1234567890123",primer_nombre="Ana",primer_apellido="A",fecha_nacimiento=date(2015,1,1),sexo="F",fecha_ingreso=date(2026,1,1));self.ins=Inscripcion.objects.create(institucion=self.a,alumno=self.al,ciclo=self.c,oferta_academica=o,grado=g,seccion=self.s,fecha_inscripcion=date(2026,1,1));self.con=ConceptoCobro.objects.create(institucion=self.a,codigo="COL",nombre="Colegiatura",tipo_general="MENSUALIDAD",monto_predeterminado=500,recurrente=True);self.met=MetodoPago.objects.create(institucion=self.a,codigo="EFE",nombre="Efectivo")
 def req(self,rolx="CONTABILIDAD"):
  r=RequestFactory().post("/");r.user=self.u[rolx];r.institucion=self.a;r.asignacion_institucion=UsuarioInstitucion.objects.get(usuario=r.user,institucion=self.a);r.META["REMOTE_ADDR"]="127.0.0.1";return r
 def cargo(self,monto=500,periodo=""):
  return Cargo.objects.create(institucion=self.a,alumno=self.al,familia=self.f,ciclo=self.c,inscripcion=self.ins,concepto=self.con,descripcion="Colegiatura",fecha_emision=date(2026,8,1),fecha_vencimiento=date(2026,8,10),monto_original=Decimal(str(monto)),periodo_referencia=periodo,creado_por=self.u["CONTABILIDAD"])
class FinanzasTests(BaseMixin,TestCase):
 def setUp(self):self.build()
 def test_concepto_unico(self):self.assertRaises(ValidationError,ConceptoCobro.objects.create,institucion=self.a,codigo="COL",nombre="Otro",monto_predeterminado=1)
 def test_monto_decimal(self):self.assertIsInstance(self.cargo().monto_total,Decimal)
 def test_total(self):
  c=Cargo(institucion=self.a,alumno=self.al,ciclo=self.c,concepto=self.con,descripcion="x",fecha_emision=date.today(),fecha_vencimiento=date.today(),monto_original=Decimal("500"),descuento=Decimal("50"),recargo=Decimal("10"),motivo_descuento="Beca",autorizado_por=self.u["ADMINISTRADOR"],creado_por=self.u["ADMINISTRADOR"]);c.save();self.assertEqual(c.monto_total,Decimal("460"))
 def test_descuento_no_negativo(self):
  c=self.cargo();c.descuento=600;c.motivo_descuento="x";c.autorizado_por=self.u["ADMINISTRADOR"];self.assertRaises(ValidationError,c.save)
 def test_pago_positivo(self):self.assertRaises(ValidationError,Pago.objects.create,institucion=self.a,alumno=self.al,monto=0,metodo_pago=self.met,registrado_por=self.u["CONTABILIDAD"])
 def test_parcial(self):
  c=self.cargo();p=registrar_pago(self.req(),alumno=self.al,monto=200,metodo_pago=self.met,aplicaciones={c.pk:200});c.refresh_from_db();self.assertEqual(c.saldo,Decimal("300"));self.assertEqual(c.estado,"PARCIAL")
 def test_completo(self):
  c=self.cargo();registrar_pago(self.req(),alumno=self.al,monto=500,metodo_pago=self.met,aplicaciones={c.pk:500});c.refresh_from_db();self.assertEqual(c.saldo,0);self.assertEqual(c.estado,"PAGADO")
 def test_multiples_cargos(self):
  a=self.cargo(500,"2026-07");b=self.cargo(300,"2026-08");p=registrar_pago(self.req(),alumno=self.al,monto=800,metodo_pago=self.met,aplicaciones={a.pk:500,b.pk:300});self.assertEqual(p.aplicado,800)
 def test_exceso_rechazado(self):
  c=self.cargo();self.assertRaises(ValidationError,registrar_pago,self.req(),alumno=self.al,monto=600,metodo_pago=self.met,aplicaciones={c.pk:600})
 def test_total_aplicado_igual(self):
  c=self.cargo();self.assertRaises(ValidationError,registrar_pago,self.req(),alumno=self.al,monto=300,metodo_pago=self.met,aplicaciones={c.pk:200})
 def test_anular_restaura(self):
  c=self.cargo();p=registrar_pago(self.req(),alumno=self.al,monto=500,metodo_pago=self.met,aplicaciones={c.pk:500});anular_pago(self.req(),p,"Error");c.refresh_from_db();self.assertEqual(c.saldo,500);self.assertEqual(c.estado,"PENDIENTE");self.assertTrue(Pago.objects.filter(pk=p.pk,estado="ANULADO").exists())
 def test_anular_audita(self):
  c=self.cargo();p=registrar_pago(self.req(),alumno=self.al,monto=500,metodo_pago=self.met,aplicaciones={c.pk:500});anular_pago(self.req(),p,"Error");self.assertTrue(EventoAuditoria.objects.filter(accion="ANULAR_PAGO",detalles__recibo=p.recibo_numero).exists())
 def test_recibos_unicos(self):
  a=self.cargo(200,"A");b=self.cargo(200,"B");p1=registrar_pago(self.req(),alumno=self.al,monto=200,metodo_pago=self.met,aplicaciones={a.pk:200});p2=registrar_pago(self.req(),alumno=self.al,monto=200,metodo_pago=self.met,aplicaciones={b.pk:200});self.assertNotEqual(p1.recibo_numero,p2.recibo_numero)
 def test_masivo_idempotente(self):
  x=generar_cargos_mensuales(self.req(),ciclo=self.c,concepto=self.con,monto=500,fecha_emision=date(2026,8,1),fecha_vencimiento=date(2026,8,10),periodo_referencia="2026-08",grado=None,seccion=None);y=generar_cargos_mensuales(self.req(),ciclo=self.c,concepto=self.con,monto=500,fecha_emision=date(2026,8,1),fecha_vencimiento=date(2026,8,10),periodo_referencia="2026-08",grado=None,seccion=None);self.assertEqual(x[0],1);self.assertEqual(y[0],0)
 def test_masivo_excluye_retirado(self):
  self.ins.estado="RETIRADA";self.ins.fecha_retiro=date.today();self.ins.motivo_retiro="x";self.ins.save();self.assertEqual(generar_cargos_mensuales(self.req(),ciclo=self.c,concepto=self.con,monto=500,fecha_emision=date.today(),fecha_vencimiento=date.today(),periodo_referencia="2026-09")[0],0)
 def test_secretaria_paga(self):
  c=self.cargo();self.assertEqual(registrar_pago(self.req("SECRETARIA"),alumno=self.al,monto=100,metodo_pago=self.met,aplicaciones={c.pk:100}).estado,"CONFIRMADO")
 def test_secretaria_no_configura(self):self.client.force_login(self.u["SECRETARIA"]);self.assertEqual(self.client.get(reverse("finanzas:configuracion")).status_code,403)
 def test_docente_bloqueado(self):self.client.force_login(self.u["DOCENTE"]);self.assertEqual(self.client.get(reverse("finanzas:dashboard")).status_code,403)
 def test_director_consulta(self):self.client.force_login(self.u["DIRECTOR"]);self.assertEqual(self.client.get(reverse("finanzas:dashboard")).status_code,200)
 def test_tenant_cargo_404(self):self.client.force_login(self.u["CONTABILIDAD"]);self.assertEqual(self.client.get(reverse("finanzas:alumno",args=[999])).status_code,404)
 def test_recibo_tenant(self):
  c=self.cargo();p=registrar_pago(self.req(),alumno=self.al,monto=100,metodo_pago=self.met,aplicaciones={c.pk:100});self.client.force_login(self.u["CONTABILIDAD"]);self.assertEqual(self.client.get(reverse("finanzas:pago_detalle",args=[p.pk])).status_code,200)
class ConcurrenciaTests(BaseMixin,TransactionTestCase):
 reset_sequences=True
 def setUp(self):self.build()
 def test_no_sobrepago_tras_bloqueo(self):
  c=self.cargo();registrar_pago(self.req(),alumno=self.al,monto=400,metodo_pago=self.met,aplicaciones={c.pk:400});self.assertRaises(ValidationError,registrar_pago,self.req(),alumno=self.al,monto=200,metodo_pago=self.met,aplicaciones={c.pk:200})
