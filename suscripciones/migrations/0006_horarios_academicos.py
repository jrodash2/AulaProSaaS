from django.db import migrations
def crear(apps,schema_editor):
 M=apps.get_model('suscripciones','ModuloSaaS');PM=apps.get_model('suscripciones','PlanModulo');P=apps.get_model('suscripciones','Plan');m,_=M.objects.update_or_create(codigo='HORARIOS',defaults={'nombre':'Horarios académicos','descripcion':'Planificación semanal de clases, docentes, secciones y aulas.','icono':'bi-calendar-week','activo':True,'orden':12})
 for p in P.objects.filter(codigo__in=('CRECE','PRO','EMPRESA')):PM.objects.update_or_create(plan=p,modulo=m,defaults={'habilitado':True})
class Migration(migrations.Migration):
 dependencies=[('suscripciones','0005_alter_modulosaas_codigo'),('horarios','0001_initial')]
 operations=[migrations.RunPython(crear,migrations.RunPython.noop)]
