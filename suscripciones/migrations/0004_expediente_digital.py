from django.db import migrations

def crear(apps,schema_editor):
 Modulo=apps.get_model('suscripciones','ModuloSaaS');PlanModulo=apps.get_model('suscripciones','PlanModulo');Plan=apps.get_model('suscripciones','Plan')
 modulo,_=Modulo.objects.update_or_create(codigo='EXPEDIENTE',defaults={'nombre':'Expediente digital','descripcion':'Gestión de documentos y requisitos de estudiantes.','icono':'bi-folder2-open','activo':True,'orden':11})
 for plan in Plan.objects.filter(codigo__in=('PRO','EMPRESA')):PlanModulo.objects.update_or_create(plan=plan,modulo=modulo,defaults={'habilitado':True})
class Migration(migrations.Migration):
 dependencies=[('suscripciones','0003_alter_modulosaas_codigo')]
 operations=[migrations.RunPython(crear,migrations.RunPython.noop)]
