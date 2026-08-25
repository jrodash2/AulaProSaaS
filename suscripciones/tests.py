from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from alumnos.models import Alumno, Inscripcion
from comunicaciones.models import Notificacion
from instituciones.models import UsuarioInstitucion
from tareas.tests import Base
from .models import ModuloSaaS, Plan, PlanModulo, SolicitudCambioPlan, Suscripcion
from .services import cambiar_estado, cambiar_plan, crear_catalogo_inicial, estado_suscripcion, metricas_saas, modulo_habilitado, obtener_uso_plan, renovar_suscripcion


class SuscripcionBase(Base):
    def setUp(self):
        super().setUp()
        self.c.es_actual=True;self.c.save()
        self.modulos={c:ModuloSaaS.objects.update_or_create(codigo=c,defaults={"nombre":n,"activo":True})[0] for c,n in ModuloSaaS.Codigo.choices}
        self.plan=Plan.objects.create(codigo="TEST",nombre="Test",precio_mensual=Decimal("120"),precio_anual=Decimal("1200"),max_alumnos=10,max_usuarios=10)
        for m in self.modulos.values():PlanModulo.objects.create(plan=self.plan,modulo=m,habilitado=True)
        self.sus=Suscripcion.objects.create(institucion=self.a,plan=self.plan,estado="ACTIVA",modalidad="MENSUAL",fecha_inicio=date(2026,1,1),fecha_fin=date(2027,1,1),creada_por=self.u["ADMINISTRADOR"])
        self.super=get_user_model().objects.create_superuser("saas_admin",password="x")


class PlanEstadoTests(SuscripcionBase):
    def test_precio_es_decimal_y_limites(self):
        self.assertIsInstance(self.plan.precio_mensual,Decimal);self.assertEqual(self.sus.limite_alumnos,10)
    def test_modulo_configurable(self):
        self.assertTrue(modulo_habilitado(self.a,"FINANZAS"));PlanModulo.objects.filter(plan=self.plan,modulo=self.modulos["FINANZAS"]).update(habilitado=False);self.assertFalse(modulo_habilitado(self.a,"FINANZAS"))
    def test_estado_activo(self):self.assertEqual(estado_suscripcion(self.a,date(2026,8,25)),"ACTIVA")
    def test_vencida_por_fecha_sin_mutar(self):self.assertEqual(estado_suscripcion(self.a,date(2028,1,1)),"VENCIDA");self.sus.refresh_from_db();self.assertEqual(self.sus.estado,"ACTIVA")
    def test_trial_vigente_y_vencido(self):
        self.sus.estado="VENCIDA";self.sus.save();trial=Suscripcion.objects.create(institucion=self.a,plan=self.plan,estado="PRUEBA",modalidad="MENSUAL",fecha_inicio=date(2026,1,1),fecha_fin=date(2026,12,1),periodo_prueba_hasta=date(2026,9,1));self.assertEqual(estado_suscripcion(self.a,date(2026,8,25)),"PRUEBA");self.assertEqual(estado_suscripcion(self.a,date(2026,9,2)),"VENCIDA")
    def test_override(self):self.sus.max_alumnos_override=25;self.sus.save();self.assertEqual(self.sus.limite_alumnos,25)


class LimitesTests(SuscripcionBase):
    def nuevo_alumno(self,n):return Alumno.objects.create(institucion=self.a,cui=f"9{n:012d}",primer_nombre="Nuevo",primer_apellido=str(n),fecha_nacimiento=date(2015,1,1),sexo="M",fecha_ingreso=date(2026,1,1))
    def inscribir(self,al):return Inscripcion.objects.create(institucion=self.a,alumno=al,ciclo=self.c,oferta_academica=self.o,grado=self.g,seccion=self.s,fecha_inscripcion=date(2026,8,1))
    def test_uso_alumnos_actuales(self):self.assertEqual(obtener_uso_plan(self.a)["alumnos"]["usados"],1)
    def test_hasta_limite_permitido_y_siguiente_bloqueado(self):
        self.sus.max_alumnos_override=2;self.sus.save();self.inscribir(self.nuevo_alumno(1));self.assertRaises(ValidationError,self.inscribir,self.nuevo_alumno(2))
    def test_retirar_libera_cupo(self):
        self.sus.max_alumnos_override=1;self.sus.save();self.ins.estado="RETIRADA";self.ins.fecha_retiro=date(2026,8,1);self.ins.motivo_retiro="Cambio";self.ins.save();self.inscribir(self.nuevo_alumno(3));self.assertEqual(obtener_uso_plan(self.a)["alumnos"]["usados"],1)
    def test_padre_alumno_no_consumen_docente_si(self):
        antes=obtener_uso_plan(self.a)["usuarios"]["usados"]
        for rol in ("PADRE","ALUMNO"):
            u=get_user_model().objects.create_user(f"lic_{rol}");UsuarioInstitucion.objects.create(usuario=u,institucion=self.a,rol=rol)
        self.assertEqual(obtener_uso_plan(self.a)["usuarios"]["usados"],antes)
        u=get_user_model().objects.create_user("lic_doc");UsuarioInstitucion.objects.create(usuario=u,institucion=self.a,rol="DOCENTE");self.assertEqual(obtener_uso_plan(self.a)["usuarios"]["usados"],antes+1)
    def test_limite_usuario_bloquea(self):
        usados=obtener_uso_plan(self.a)["usuarios"]["usados"];self.sus.max_usuarios_override=usados;self.sus.save();u=get_user_model().objects.create_user("extra");self.assertRaises(ValidationError,UsuarioInstitucion.objects.create,usuario=u,institucion=self.a,rol="SECRETARIA")


class OperacionesSaaSTests(SuscripcionBase):
    def test_mrr_mensual_y_anual(self):
        self.assertEqual(metricas_saas()["mrr"],Decimal("120"));self.sus.modalidad="ANUAL";self.sus.save();self.assertEqual(metricas_saas()["mrr"],Decimal("100"))
    def test_suspendida_no_cuenta_mrr(self):cambiar_estado(self.sus,"SUSPENDIDA",self.super);self.assertEqual(metricas_saas()["mrr"],0)
    def test_renovar(self):
        renovar_suscripcion(self.sus,self.super,meses=1);self.sus.refresh_from_db();self.assertGreater(self.sus.fecha_fin,date(2027,1,1));self.assertTrue(self.sus.historial.filter(accion="RENOVAR_SUSCRIPCION").exists())
    def test_upgrade_inmediato(self):
        pro=Plan.objects.create(codigo="PRO2",nombre="Pro",precio_mensual=200,max_alumnos=100,max_usuarios=30);cambiar_plan(self.sus,pro,self.super);self.sus.refresh_from_db();self.assertEqual(self.sus.plan,pro)
    def test_downgrade_sobreuso_bloqueado(self):
        bajo=Plan.objects.create(codigo="BAJO",nombre="Bajo",precio_mensual=50,max_alumnos=0,max_usuarios=10);self.assertRaises(ValidationError,cambiar_plan,self.sus,bajo,self.super)
    def test_acciones_solo_superadmin(self):
        self.client.force_login(self.u["ADMINISTRADOR"]);self.assertEqual(self.client.get(reverse("suscripciones:planes")).status_code,403)
        self.client.force_login(self.super);self.assertEqual(self.client.get(reverse("suscripciones:planes")).status_code,200)
    def test_modulo_url_bloqueado(self):
        PlanModulo.objects.filter(plan=self.plan,modulo=self.modulos["FINANZAS"]).update(habilitado=False);self.client.force_login(self.u["ADMINISTRADOR"]);self.assertEqual(self.client.get(reverse("finanzas:dashboard")).status_code,403)
    def test_sidebar_no_muestra_finanzas_excluidas(self):
        PlanModulo.objects.filter(plan=self.plan,modulo=self.modulos["FINANZAS"]).update(habilitado=False);self.client.force_login(self.u["ADMINISTRADOR"]);self.assertNotContains(self.client.get(reverse("core:institucion_dashboard")),">Finanzas<")
    def test_vencida_bloquea_escritura_pero_no_lectura(self):
        self.sus.fecha_fin=date(2026,1,2);self.sus.save();self.client.force_login(self.u["ADMINISTRADOR"]);self.assertEqual(self.client.get(reverse("alumnos:lista")).status_code,200);self.assertEqual(self.client.post(reverse("alumnos:crear")).status_code,403)


class CommandsTests(SuscripcionBase):
    def test_actualizar_idempotente(self):
        self.sus.fecha_inicio=date(2024,1,1);self.sus.fecha_fin=date(2025,1,1);self.sus.save();call_command("actualizar_suscripciones");call_command("actualizar_suscripciones");self.sus.refresh_from_db();self.assertEqual(self.sus.estado,"VENCIDA")
    def test_alertas_no_duplican(self):
        owner=get_user_model().objects.create_user("owner");UsuarioInstitucion.objects.create(usuario=owner,institucion=self.a,rol="PROPIETARIO");self.sus.fecha_fin=timezone.localdate()+timedelta(days=7);self.sus.save();call_command("generar_alertas_suscripciones");call_command("generar_alertas_suscripciones");self.assertEqual(Notificacion.objects.filter(usuario=owner,tipo_origen="SUSCRIPCION").count(),1)
    def test_catalogo_demo_idempotente(self):crear_catalogo_inicial();crear_catalogo_inicial();self.assertEqual(Plan.objects.filter(codigo__in=("INICIO","CRECE","PRO","EMPRESA")).count(),4)
