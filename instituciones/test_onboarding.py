from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.http import QueryDict
from django.urls import reverse

from academico.models import CicloEscolar, JornadaInstitucion
from instituciones.models import Institucion, OnboardingInstitucion, UsuarioInstitucion
from suscripciones.forms import PlanForm
from suscripciones.models import ModuloSaaS, Plan, PlanModulo, Suscripcion
from suscripciones.services import modulo_habilitado
from tareas.tests import Base


class CatalogoModulosTests(TestCase):
    def test_migracion_crea_diez_modulos(self):
        self.assertEqual(ModuloSaaS.objects.filter(codigo__in=[c for c, _ in ModuloSaaS.Codigo.choices]).count(), 10)
        self.assertEqual(list(ModuloSaaS.objects.order_by("orden").values_list("orden", flat=True)), list(range(1, 11)))

    def test_comando_sincronizar_idempotente_y_preserva_inactivo(self):
        modulo=ModuloSaaS.objects.get(codigo="FINANZAS");modulo.activo=False;modulo.nombre="Viejo";modulo.save()
        call_command("sincronizar_modulos_saas");call_command("sincronizar_modulos_saas")
        modulo.refresh_from_db();self.assertFalse(modulo.activo);self.assertEqual(modulo.nombre,"Finanzas")

    def test_comando_reactiva_solo_con_flag(self):
        ModuloSaaS.objects.filter(codigo="PORTAL").update(activo=False);call_command("sincronizar_modulos_saas",reactivar=True);self.assertTrue(ModuloSaaS.objects.get(codigo="PORTAL").activo)

    def datos_plan(self, modulos):
        data=QueryDict(mutable=True);data.update({"codigo":"NUEVO","nombre":"Nuevo","descripcion":"x","precio_mensual":"99.00","precio_anual":"999.00","max_alumnos":100,"max_usuarios":10,"orden":1,"activo":"on","publico":"on"});data.setlist("modulos_seleccionados",[str(m.pk) for m in modulos]);return data

    def test_plan_form_muestra_modulos_activos(self):
        form=PlanForm();self.assertEqual(len(form.modulos_disponibles),10)

    def test_guardar_y_desmarcar_plan_modulo(self):
        mods=list(ModuloSaaS.objects.order_by("orden")[:3]);form=PlanForm(self.datos_plan(mods));self.assertTrue(form.is_valid(),form.errors);plan=form.save();self.assertEqual(plan.configuracion_modulos.filter(habilitado=True).count(),3)
        data=self.datos_plan(mods[:1]);data["codigo"]=plan.codigo;form=PlanForm(data,instance=plan);self.assertTrue(form.is_valid(),form.errors);form.save();self.assertEqual(plan.configuracion_modulos.filter(habilitado=True).count(),1)

    def test_editar_conserva_seleccionados_e_inactivo_no_aparece(self):
        plan=Plan.objects.create(codigo="EDIT",nombre="Editar",precio_mensual=1,orden=1);mod=ModuloSaaS.objects.get(codigo="ACADEMICO");PlanModulo.objects.create(plan=plan,modulo=mod,habilitado=True)
        form=PlanForm(instance=plan);self.assertIn(mod.pk,[int(pk) for pk in form.fields["modulos_seleccionados"].initial])
        ModuloSaaS.objects.filter(codigo="PORTAL").update(activo=False);self.assertFalse(any(m.codigo == "PORTAL" for m in PlanForm().modulos_disponibles))

    def test_plan_detalle_muestra_modulos_habilitados(self):
        plan = Plan.objects.create(codigo="DET", nombre="Detalle", precio_mensual=1, orden=1)
        modulo = ModuloSaaS.objects.get(codigo="ACADEMICO")
        PlanModulo.objects.create(plan=plan, modulo=modulo, habilitado=True)
        usuario = get_user_model().objects.create_superuser("saas_detail", password="x")
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse("suscripciones:plan_detalle", args=[plan.pk]))
        self.assertContains(respuesta, "Académico")


class OnboardingTests(Base):
    def setUp(self):
        super().setUp();self.c.es_actual=True;self.c.save();self.owner=get_user_model().objects.create_user("owner_onboarding",password="x");UsuarioInstitucion.objects.create(usuario=self.owner,institucion=self.a,rol="PROPIETARIO")

    def test_estado_detecta_ciclo_y_jornada(self):
        from instituciones.onboarding import estado_onboarding
        estado=estado_onboarding(self.a);self.assertTrue(estado["pasos"][1]["completo"]);self.assertFalse(estado["pasos"][2]["completo"])
        JornadaInstitucion.objects.create(institucion=self.a,codigo="MAT",nombre="Matutina");self.assertTrue(estado_onboarding(self.a)["pasos"][2]["completo"])

    def test_admin_y_propietario_acceden_docente_padre_bloqueados(self):
        for usuario,esperado in ((self.u["ADMINISTRADOR"],200),(self.owner,200),(self.u["DOCENTE"],403)):
            self.client.force_login(usuario);self.assertEqual(self.client.get(reverse("instituciones:onboarding")).status_code,esperado)
        padre=get_user_model().objects.create_user("padre_onboarding");UsuarioInstitucion.objects.create(usuario=padre,institucion=self.a,rol="PADRE");self.client.force_login(padre);self.assertEqual(self.client.get(reverse("instituciones:onboarding")).status_code,403)

    def test_guarda_y_permite_continuar(self):
        self.client.force_login(self.u["ADMINISTRADOR"]);self.assertEqual(self.client.post(reverse("instituciones:onboarding_paso",args=[4]),{"accion":"siguiente"}).status_code,302);registro=OnboardingInstitucion.objects.get(institucion=self.a);self.assertEqual(registro.paso_actual,5)

    def test_propietario_puede_omitir_admin_no(self):
        self.client.force_login(self.owner);self.client.post(reverse("instituciones:onboarding_omitir"));self.assertTrue(OnboardingInstitucion.objects.get(institucion=self.a).omitido)
        OnboardingInstitucion.objects.filter(institucion=self.a).update(completado=False,omitido=False);self.client.force_login(self.u["ADMINISTRADOR"]);self.assertEqual(self.client.post(reverse("instituciones:onboarding_omitir")).status_code,403)

    def test_tenant_no_se_recibe_desde_cliente(self):
        self.client.force_login(self.u["ADMINISTRADOR"]);self.client.post(reverse("instituciones:onboarding_paso",args=[4]),{"accion":"siguiente","institucion":self.b.pk});self.assertFalse(OnboardingInstitucion.objects.filter(institucion=self.b).exists())

    def test_finanzas_y_portal_omitidos_segun_plan(self):
        plan=Plan.objects.create(codigo="BASICO",nombre="Básico",precio_mensual=Decimal("1"),max_alumnos=10,max_usuarios=10)
        for codigo in ("ACADEMICO","ALUMNOS","DOCENTES"):
            PlanModulo.objects.create(plan=plan,modulo=ModuloSaaS.objects.get(codigo=codigo),habilitado=True)
        Suscripcion.objects.create(institucion=self.a,plan=plan,estado="ACTIVA",modalidad="MENSUAL",fecha_inicio=date(2026,1,1),fecha_fin=date(2027,1,1))
        from instituciones.onboarding import estado_onboarding
        estado=estado_onboarding(self.a);self.assertTrue(estado["pasos"][8]["omitido_plan"]);self.assertTrue(estado["pasos"][9]["omitido_plan"]);self.assertFalse(modulo_habilitado(self.a,"FINANZAS"))


class AltaInstitucionTests(TestCase):
    def test_superadmin_crea_institucion_plan_propietario_y_onboarding(self):
        superadmin=get_user_model().objects.create_superuser("root_onboarding",password="x");self.client.force_login(superadmin)
        plan=Plan.objects.create(codigo="ALTA",nombre="Alta",precio_mensual=Decimal("10"),max_alumnos=100,max_usuarios=10)
        data={"nombre":"Colegio Nuevo","nombre_corto":"Nuevo","codigo":"NUEVO-ONB","razon_social":"Colegio Nuevo SA","direccion":"Zona 1","departamento":"Guatemala","municipio":"Guatemala","telefono":"2222","email":"colegio@example.com","sitio_web":"https://example.com","color_primario":"#1F4E5F","color_secundario":"#3B8C88","activa":"on","plan":plan.pk,"trial_dias":30,"propietario_username":"nuevo_propietario","propietario_email":"owner@example.com","propietario_password":"ClaveSegura2026!"}
        response=self.client.post(reverse("instituciones:crear"),data);self.assertEqual(response.status_code,302)
        inst=Institucion.objects.get(codigo="NUEVO-ONB");self.assertTrue(inst.suscripciones.filter(plan=plan,estado="PRUEBA").exists());self.assertTrue(inst.asignaciones_usuario.filter(rol="PROPIETARIO").exists());self.assertTrue(OnboardingInstitucion.objects.filter(institucion=inst,paso_actual=1).exists());self.assertTrue(get_user_model().objects.get(username="nuevo_propietario").check_password("ClaveSegura2026!"))
