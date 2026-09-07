from django.db import migrations
def seed(apps,schema_editor):
 M=apps.get_model('suscripciones','ModuloSaaS');P=apps.get_model('suscripciones','Plan');PM=apps.get_model('suscripciones','PlanModulo');m,_=M.objects.update_or_create(codigo='ADMISIONES',defaults={'nombre':'Admisiones','descripcion':'Gestión de aspirantes, solicitudes, entrevistas y procesos de ingreso.','icono':'bi-person-plus','orden':14,'activo':True})
 for p in P.objects.filter(codigo__in=('PRO','EMPRESA')):PM.objects.update_or_create(plan=p,modulo=m,defaults={'habilitado':True})
class Migration(migrations.Migration):
 dependencies=[('suscripciones','0009_alter_modulosaas_codigo'),('admisiones','0001_initial')]
 operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
