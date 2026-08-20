import django.core.validators
import django.db.models.deletion
import instituciones.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Institucion", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
            ("nombre", models.CharField(max_length=180)), ("nombre_corto", models.CharField(blank=True, max_length=80)),
            ("codigo", models.CharField(max_length=40, unique=True)), ("razon_social", models.CharField(blank=True, max_length=180)),
            ("direccion", models.TextField(blank=True)), ("departamento", models.CharField(blank=True, max_length=80)),
            ("municipio", models.CharField(blank=True, max_length=80)), ("telefono", models.CharField(blank=True, max_length=30)),
            ("email", models.EmailField(blank=True, max_length=254)), ("sitio_web", models.URLField(blank=True)),
            ("logo_principal", models.ImageField(blank=True, upload_to="instituciones/logos/", validators=[django.core.validators.FileExtensionValidator(["jpg", "jpeg", "png", "webp"])])),
            ("logo_secundario", models.ImageField(blank=True, upload_to="instituciones/logos/", validators=[django.core.validators.FileExtensionValidator(["jpg", "jpeg", "png", "webp"])])),
            ("color_primario", models.CharField(default="#1F4E5F", max_length=7, validators=[instituciones.models.color_validator])),
            ("color_secundario", models.CharField(default="#3B8C88", max_length=7, validators=[instituciones.models.color_validator])),
            ("activa", models.BooleanField(default=True)), ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
            ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
        ], options={"ordering": ("nombre",)}),
        migrations.CreateModel(name="UsuarioInstitucion", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("rol", models.CharField(choices=[("PROPIETARIO", "Propietario"), ("DIRECTOR", "Director"), ("ADMINISTRADOR", "Administrador"), ("SECRETARIA", "Secretaría"), ("CONTABILIDAD", "Contabilidad"), ("DOCENTE", "Docente")], max_length=20)),
            ("activo", models.BooleanField(default=True)), ("fecha_asignacion", models.DateTimeField(auto_now_add=True)),
            ("institucion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asignaciones_usuario", to="instituciones.institucion")),
            ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asignaciones_institucion", to=settings.AUTH_USER_MODEL)),
        ], options={"verbose_name": "asignación usuario-institución", "verbose_name_plural": "asignaciones usuario-institución"}),
        migrations.AddConstraint(model_name="usuarioinstitucion", constraint=models.UniqueConstraint(fields=("usuario", "institucion"), name="usuario_institucion_unica")),
    ]
