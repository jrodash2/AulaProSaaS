from datetime import date,timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory,TestCase
from django.urls import reverse
from instituciones.models import Institucion,UsuarioInstitucion
from docentes.models import Docente
from .forms import ContratoForm, EmpleadoForm
from .models import *
from .services import *
class Base(TestCase):
 def setUp(self):
  self.a=Institucion.objects.create(nombre="A",codigo="RHA");self.b=Institucion.objects.create(nombre="B",codigo="RHB");self.users={}
  for rol in ("PROPIETARIO","DIRECTOR","ADMINISTRADOR","SECRETARIA","CONTABILIDAD","DOCENTE","PADRE"):
   u=get_user_model().objects.create_user(username="rh"+rol,password="x");UsuarioInstitucion.objects.create(usuario=u,institucion=self.a,rol=rol);self.users[rol]=u
  self.area=AreaLaboral.objects.create(institucion=self.a,codigo="DOC",nombre="Docencia");self.puesto=PuestoLaboral.objects.create(institucion=self.a,area=self.area,codigo="PROF",nombre="Profesor",tipo="DOCENTE");self.doc=Docente.objects.create(institucion=self.a,usuario=self.users["DOCENTE"],primer_nombre="Juan",primer_apellido="Pérez",telefono="1",fecha_ingreso=date.today());self.emp=Empleado.objects.create(institucion=self.a,nombres="Juan",apellidos="Pérez",puesto=self.puesto,area=self.area,fecha_ingreso=date(2024,1,1),usuario=self.users["DOCENTE"],docente=self.doc,creado_por=self.users["DIRECTOR"])
 def req(self,rol):
  r=RequestFactory().post('/');r.user=self.users[rol];r.institucion=self.a;r.asignacion_institucion=UsuarioInstitucion.objects.get(usuario=r.user,institucion=self.a);return r
class ModeloTests(Base):
 def test_codigo_tenant(self):self.assertEqual(self.emp.codigo_empleado,"EMP-00001")
 def test_area_unica(self):self.assertRaises(ValidationError,AreaLaboral.objects.create,institucion=self.a,codigo="DOC",nombre="Otra")
 def test_puesto_otro_tenant(self):
  area=AreaLaboral.objects.create(institucion=self.b,codigo="B",nombre="B");self.puesto.area=area;self.assertRaises(ValidationError,self.puesto.save)
 def test_usuario_otro_tenant(self):
  u=get_user_model().objects.create_user(username="externo");self.emp.usuario=u;self.assertRaises(ValidationError,self.emp.save)
 def test_docente_otro_tenant(self):
  u=get_user_model().objects.create_user(username="docb");UsuarioInstitucion.objects.create(usuario=u,institucion=self.b,rol="DOCENTE");d=Docente.objects.create(institucion=self.b,usuario=u,primer_nombre="B",primer_apellido="B",telefono="1",fecha_ingreso=date.today());self.emp.docente=d;self.assertRaises(ValidationError,self.emp.save)
 def test_contrato_vigente(self):
  c=ContratoLaboral.objects.create(institucion=self.a,empleado=self.emp,numero_contrato="C1",tipo_contrato="PLAZO_FIJO",fecha_inicio=date.today(),fecha_fin=date.today()+timedelta(days=10),puesto=self.puesto,estado="VIGENTE",creado_por=self.users["DIRECTOR"]);self.assertEqual(c.estado_vigente,"VIGENTE");self.assertEqual(contratos_por_vencer(self.a).count(),1)
 def test_contrato_vencido_calculado(self):
  c=ContratoLaboral.objects.create(institucion=self.a,empleado=self.emp,numero_contrato="C1",tipo_contrato="PLAZO_FIJO",fecha_inicio=date.today()-timedelta(days=30),fecha_fin=date.today()-timedelta(days=1),puesto=self.puesto,estado="VIGENTE",creado_por=self.users["DIRECTOR"]);self.assertEqual(c.estado_vigente,"VENCIDO")
 def test_movimiento_preservado(self):
  m=cambiar_puesto(self.emp,self.puesto,self.area,date.today(),"Confirmación",self.users["DIRECTOR"]);self.assertTrue(m.pk);self.assertEqual(self.emp.movimientos.count(),1)
 def test_egreso_conserva_historial_desactiva_acceso(self):
  registrar_egreso(self.emp,date.today(),"Fin",self.users["DIRECTOR"]);self.emp.refresh_from_db();self.assertEqual(self.emp.estado,"RETIRADO");self.assertTrue(self.emp.movimientos.exists());self.assertFalse(UsuarioInstitucion.objects.get(usuario=self.users["DOCENTE"],institucion=self.a).activo)
 def test_archivo_peligroso(self):
  t=TipoDocumentoEmpleado.objects.create(institucion=self.a,codigo="DPI",nombre="DPI");d=DocumentoEmpleado(institucion=self.a,empleado=self.emp,tipo_documento=t,archivo=SimpleUploadedFile("x.exe",b"MZ"),nombre_original="x.exe");self.assertRaises(ValidationError,d.save)
 def test_expediente_porcentaje(self):
  TipoDocumentoEmpleado.objects.create(institucion=self.a,codigo="DPI",nombre="DPI");self.assertEqual(resumen_expediente(self.emp)["porcentaje"],0)
 def test_permiso_fechas(self):self.assertRaises(ValidationError,PermisoLaboral.objects.create,institucion=self.a,empleado=self.emp,tipo="PERSONAL",fecha_inicio=date.today(),fecha_fin=date.today()-timedelta(days=1),motivo="x")
class PermisosVistaTests(Base):
 def test_director_accede(self):self.client.force_login(self.users["DIRECTOR"]);self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code,200)
 def test_docente_solo_perfil(self):self.client.force_login(self.users["DOCENTE"]);self.assertEqual(self.client.get(reverse("rrhh:mi_perfil")).status_code,200);self.assertEqual(self.client.get(reverse("rrhh:empleado_nuevo")).status_code,403)
 def test_padre_bloqueado(self):self.client.force_login(self.users["PADRE"]);self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code,403)
 def test_tenant_idor(self):
  area=AreaLaboral.objects.create(institucion=self.b,codigo="B",nombre="B");puesto=PuestoLaboral.objects.create(institucion=self.b,area=area,codigo="B",nombre="B");e=Empleado.objects.create(institucion=self.b,nombres="B",apellidos="B",puesto=puesto,area=area,fecha_ingreso=date.today());self.client.force_login(self.users["DIRECTOR"]);self.assertEqual(self.client.get(reverse("rrhh:empleado",args=[e.pk])).status_code,404)
 def test_salario_no_visible_secretaria(self):
  ContratoLaboral.objects.create(institucion=self.a,empleado=self.emp,numero_contrato="C1",tipo_contrato="INDEFINIDO",fecha_inicio=date.today(),puesto=self.puesto,estado="VIGENTE",creado_por=self.users["DIRECTOR"],salario_referencia=Decimal("9000"));self.client.force_login(self.users["SECRETARIA"]);response=self.client.get(reverse("rrhh:empleado",args=[self.emp.pk]));self.assertNotContains(response,"9000")
 def test_form_no_expone_salario(self):self.assertNotIn("salario_referencia",ContratoForm(institucion=self.a,ver_salario=False).fields)
 def test_permiso_y_resolucion_notifica(self):
  p=PermisoLaboral.objects.create(institucion=self.a,empleado=self.emp,tipo="VACACIONES",fecha_inicio=date.today(),fecha_fin=date.today(),motivo="Descanso",solicitado_por=self.users["DOCENTE"]);resolver_permiso(self.req("DIRECTOR"),p,"APROBADO");self.assertEqual(p.estado,"APROBADO");self.assertEqual(self.users["DOCENTE"].notificaciones.filter(tipo_origen="PERMISO_LABORAL").count(),1)
 def test_resolver_solo_post(self):
  p=PermisoLaboral.objects.create(institucion=self.a,empleado=self.emp,tipo="PERSONAL",fecha_inicio=date.today(),fecha_fin=date.today(),motivo="x",solicitado_por=self.users["DIRECTOR"]);self.client.force_login(self.users["DIRECTOR"]);self.assertEqual(self.client.get(reverse("rrhh:permiso_resolver",args=[p.pk])).status_code,405)


class EmpleadoFormHotfixTests(Base):
 def test_nuevo_empleado_carga_sin_field_error(self):
  self.client.force_login(self.users["DIRECTOR"])
  response=self.client.get(reverse("rrhh:empleado_nuevo"))
  self.assertEqual(response.status_code,200)

 def test_solo_muestra_docentes_activos_del_tenant(self):
  activo=self.doc
  inactivo=Docente.objects.create(institucion=self.a,primer_nombre="Inactivo",primer_apellido="Local",telefono="1",fecha_ingreso=date.today(),estado=Docente.Estado.INACTIVO)
  externo=Docente.objects.create(institucion=self.b,primer_nombre="Activo",primer_apellido="Externo",telefono="1",fecha_ingreso=date.today(),estado=Docente.Estado.ACTIVO)
  form=EmpleadoForm(institucion=self.a)
  self.assertQuerySetEqual(form.fields["docente"].queryset,[activo])
  self.assertNotIn(inactivo,form.fields["docente"].queryset)
  self.assertNotIn(externo,form.fields["docente"].queryset)

 def test_edicion_conserva_docente_y_usuario_inactivos(self):
  self.doc.estado=Docente.Estado.SUSPENDIDO
  self.doc.save()
  asignacion=UsuarioInstitucion.objects.get(usuario=self.users["DOCENTE"],institucion=self.a)
  asignacion.activo=False
  asignacion.save()
  form=EmpleadoForm(instance=self.emp,institucion=self.a)
  self.assertIn(self.doc,form.fields["docente"].queryset)
  self.assertIn(self.users["DOCENTE"],form.fields["usuario"].queryset)

 def test_formulario_usa_estilos_aulapro(self):
  form=EmpleadoForm(institucion=self.a)
  self.assertIn("form-select",form.fields["docente"].widget.attrs["class"])
  self.assertFalse(form.fields["docente"].required)
