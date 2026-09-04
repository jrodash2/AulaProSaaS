from django.db import migrations
def seed(apps,schema_editor):
 Modulo=apps.get_model("suscripciones","ModuloSaaS");PlanModulo=apps.get_model("suscripciones","PlanModulo")
 modulo,_=Modulo.objects.update_or_create(codigo="SEGUIMIENTO",defaults={"nombre":"Seguimiento estudiantil","descripcion":"Incidencias, reconocimientos, compromisos y seguimiento del alumno.","icono":"bi-heart-pulse","orden":13,"activo":True})
 for plan in apps.get_model("suscripciones","Plan").objects.filter(codigo__in=("PRO","EMPRESA")):PlanModulo.objects.update_or_create(plan=plan,modulo=modulo,defaults={"habilitado":True})
class Migration(migrations.Migration):
 dependencies=[("suscripciones","0007_alter_modulosaas_codigo"),("seguimiento","0001_initial")]
 operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
