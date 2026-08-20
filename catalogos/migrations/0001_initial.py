import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="AreaCurricular",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                ("codigo", models.CharField(max_length=40, unique=True)),
                ("nombre", models.CharField(max_length=120)),
                ("descripcion", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "área curricular",
                "verbose_name_plural": "áreas curriculares",
                "ordering": ("nombre",),
            },
        ),
        migrations.CreateModel(
            name="NivelEducativo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                ("codigo", models.CharField(max_length=30, unique=True)),
                ("nombre", models.CharField(max_length=100)),
                ("orden", models.PositiveSmallIntegerField(default=0)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "nivel educativo",
                "verbose_name_plural": "niveles educativos",
                "ordering": ("orden", "nombre"),
            },
        ),
        migrations.CreateModel(
            name="TipoCarrera",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                ("codigo", models.CharField(max_length=30, unique=True)),
                ("nombre", models.CharField(max_length=100)),
                ("descripcion", models.TextField(blank=True)),
                ("orden", models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                "verbose_name_plural": "tipos de carrera",
                "ordering": ("orden", "nombre"),
            },
        ),
        migrations.CreateModel(
            name="CursoCatalogo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("codigo_interno", models.CharField(max_length=50, unique=True)),
                ("codigo_mineduc", models.CharField(blank=True, max_length=50)),
                ("nombre", models.CharField(max_length=180)),
                ("nombre_corto", models.CharField(blank=True, max_length=80)),
                ("descripcion", models.TextField(blank=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                (
                    "area_curricular",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cursos",
                        to="catalogos.areacurricular",
                    ),
                ),
            ],
            options={
                "verbose_name": "curso del catálogo",
                "verbose_name_plural": "cursos del catálogo",
                "ordering": ("nombre",),
            },
        ),
        migrations.CreateModel(
            name="CarreraCatalogo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("activa", models.BooleanField(default=True)),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("codigo_interno", models.CharField(max_length=50, unique=True)),
                ("codigo_mineduc", models.CharField(blank=True, max_length=50)),
                ("nombre", models.CharField(max_length=220)),
                ("nombre_corto", models.CharField(blank=True, max_length=100)),
                ("duracion_anios", models.PositiveSmallIntegerField()),
                ("descripcion", models.TextField(blank=True)),
                (
                    "modalidad",
                    models.CharField(
                        choices=[
                            ("PRESENCIAL", "Presencial"),
                            ("SEMIPRESENCIAL", "Semipresencial"),
                            ("A_DISTANCIA", "A distancia"),
                            ("MIXTA", "Mixta"),
                            ("OTRA", "Otra"),
                        ],
                        default="PRESENCIAL",
                        max_length=20,
                    ),
                ),
                ("jornada_referencia", models.CharField(blank=True, max_length=100)),
                ("acuerdo_ministerial", models.CharField(blank=True, max_length=120)),
                ("fecha_acuerdo", models.DateField(blank=True, null=True)),
                ("fuente_oficial", models.CharField(blank=True, max_length=220)),
                ("url_fuente", models.URLField(blank=True)),
                ("en_revision", models.BooleanField(default=False)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                (
                    "nivel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="carreras",
                        to="catalogos.niveleducativo",
                    ),
                ),
                (
                    "tipo_carrera",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="carreras",
                        to="catalogos.tipocarrera",
                    ),
                ),
            ],
            options={
                "verbose_name": "carrera del catálogo",
                "verbose_name_plural": "carreras del catálogo",
                "ordering": ("nombre",),
            },
        ),
        migrations.CreateModel(
            name="VersionPensum",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("codigo_version", models.CharField(max_length=50)),
                ("nombre", models.CharField(max_length=160)),
                ("acuerdo_ministerial", models.CharField(blank=True, max_length=120)),
                ("fecha_acuerdo", models.DateField(blank=True, null=True)),
                ("fecha_inicio_vigencia", models.DateField()),
                ("fecha_fin_vigencia", models.DateField(blank=True, null=True)),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("BORRADOR", "Borrador"),
                            ("VIGENTE", "Vigente"),
                            ("EN_REVISION", "En revisión"),
                            ("HISTORICO", "Histórico"),
                            ("DEROGADO", "Derogado"),
                        ],
                        default="BORRADOR",
                        max_length=20,
                    ),
                ),
                ("observaciones", models.TextField(blank=True)),
                ("fuente_oficial", models.CharField(blank=True, max_length=220)),
                ("url_fuente", models.URLField(blank=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                (
                    "carrera",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="versiones_pensum",
                        to="catalogos.carreracatalogo",
                    ),
                ),
            ],
            options={
                "verbose_name": "versión de pensum",
                "verbose_name_plural": "versiones de pensum",
                "ordering": ("-fecha_inicio_vigencia", "-fecha_creacion"),
            },
        ),
        migrations.CreateModel(
            name="GradoPensum",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                ("codigo", models.CharField(max_length=30)),
                ("nombre", models.CharField(max_length=100)),
                ("numero_orden", models.PositiveSmallIntegerField()),
                (
                    "pensum",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="grados",
                        to="catalogos.versionpensum",
                    ),
                ),
            ],
            options={
                "verbose_name": "grado de pensum",
                "verbose_name_plural": "grados de pensum",
                "ordering": ("numero_orden", "nombre"),
            },
        ),
        migrations.CreateModel(
            name="CursoPensum",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                ("orden", models.PositiveSmallIntegerField(default=0)),
                (
                    "periodos_semanales",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                ("obligatorio", models.BooleanField(default=True)),
                ("observaciones", models.TextField(blank=True)),
                (
                    "curso",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="apariciones_pensum",
                        to="catalogos.cursocatalogo",
                    ),
                ),
                (
                    "grado",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cursos_pensum",
                        to="catalogos.gradopensum",
                    ),
                ),
                (
                    "pensum",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cursos_pensum",
                        to="catalogos.versionpensum",
                    ),
                ),
            ],
            options={
                "verbose_name": "curso de pensum",
                "verbose_name_plural": "cursos de pensum",
                "ordering": ("grado__numero_orden", "orden", "curso__nombre"),
            },
        ),
        migrations.AddConstraint(
            model_name="versionpensum",
            constraint=models.UniqueConstraint(
                fields=("carrera", "codigo_version"),
                name="version_pensum_codigo_unico_carrera",
            ),
        ),
        migrations.AddConstraint(
            model_name="gradopensum",
            constraint=models.UniqueConstraint(
                fields=("pensum", "codigo"), name="grado_codigo_unico_pensum"
            ),
        ),
        migrations.AddConstraint(
            model_name="cursopensum",
            constraint=models.UniqueConstraint(
                fields=("pensum", "grado", "curso"), name="curso_unico_grado_pensum"
            ),
        ),
    ]
