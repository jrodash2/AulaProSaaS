from django.db import migrations
def seed(apps,schema_editor):
 M=apps.get_model('suscripciones','ModuloSaaS');P=apps.get_model('suscripciones','Plan');PM=apps.get_model('suscripciones','PlanModulo');m,_=M.objects.update_or_create(codigo='RRHH',defaults={'nombre':'Recursos Humanos','descripcion':'Gestión de empleados, contratos, documentos y permisos del personal.','icono':'bi-briefcase','orden':15,'activo':True})
 for p in P.objects.filter(codigo__in=('PRO','EMPRESA')):PM.objects.update_or_create(plan=p,modulo=m,defaults={'habilitado':True})
class Migration(migrations.Migration):
 dependencies=[('suscripciones','0011_alter_modulosaas_codigo'),('rrhh','0001_initial')]
 operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
