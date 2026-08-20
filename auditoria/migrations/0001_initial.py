import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("instituciones", "0001_initial")]
    operations = [migrations.CreateModel(name="EventoAuditoria", fields=[
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("accion", models.CharField(max_length=40)), ("modelo", models.CharField(max_length=120)),
        ("objeto_id", models.CharField(blank=True, max_length=64)), ("fecha", models.DateTimeField(auto_now_add=True, db_index=True)),
        ("ip", models.GenericIPAddressField(blank=True, null=True)),
        ("institucion", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="eventos_auditoria", to="instituciones.institucion")),
        ("usuario", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="eventos_auditoria", to=settings.AUTH_USER_MODEL)),
    ], options={"verbose_name": "evento de auditoría", "verbose_name_plural": "eventos de auditoría", "ordering": ("-fecha",)})]
