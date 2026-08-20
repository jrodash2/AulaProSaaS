from django import forms

from .models import (
    AreaCurricular,
    CarreraCatalogo,
    CursoCatalogo,
    CursoPensum,
    GradoPensum,
    NivelEducativo,
    TipoCarrera,
    VersionPensum,
)


class AulaProModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = (
                "form-check-input"
                if isinstance(field.widget, forms.CheckboxInput)
                else "form-select"
                if isinstance(field.widget, forms.Select)
                else "form-control"
            )
            field.widget.attrs.setdefault("class", css_class)


class NivelEducativoForm(AulaProModelForm):
    class Meta:
        model = NivelEducativo
        fields = ("codigo", "nombre", "orden", "activo")


class TipoCarreraForm(AulaProModelForm):
    class Meta:
        model = TipoCarrera
        fields = ("codigo", "nombre", "descripcion", "orden", "activo")
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}


class AreaCurricularForm(AulaProModelForm):
    class Meta:
        model = AreaCurricular
        fields = ("codigo", "nombre", "descripcion", "activo")
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}


class CursoCatalogoForm(AulaProModelForm):
    class Meta:
        model = CursoCatalogo
        fields = (
            "codigo_interno",
            "codigo_mineduc",
            "nombre",
            "nombre_corto",
            "area_curricular",
            "descripcion",
            "activo",
        )
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}


class CarreraCatalogoForm(AulaProModelForm):
    class Meta:
        model = CarreraCatalogo
        fields = (
            "codigo_interno",
            "codigo_mineduc",
            "nombre",
            "nombre_corto",
            "nivel",
            "tipo_carrera",
            "duracion_anios",
            "descripcion",
            "modalidad",
            "jornada_referencia",
            "acuerdo_ministerial",
            "fecha_acuerdo",
            "fuente_oficial",
            "url_fuente",
            "activa",
            "en_revision",
        )
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "fecha_acuerdo": forms.DateInput(attrs={"type": "date"}),
        }


class VersionPensumForm(AulaProModelForm):
    class Meta:
        model = VersionPensum
        fields = (
            "codigo_version",
            "nombre",
            "acuerdo_ministerial",
            "fecha_acuerdo",
            "fecha_inicio_vigencia",
            "fecha_fin_vigencia",
            "estado",
            "observaciones",
            "fuente_oficial",
            "url_fuente",
        )
        widgets = {
            "fecha_acuerdo": forms.DateInput(attrs={"type": "date"}),
            "fecha_inicio_vigencia": forms.DateInput(attrs={"type": "date"}),
            "fecha_fin_vigencia": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }


class DuplicarPensumForm(forms.Form):
    codigo_version = forms.CharField(max_length=50, label="Código de nueva versión")
    nombre = forms.CharField(max_length=160, label="Nombre de nueva versión")
    fecha_inicio_vigencia = forms.DateField(
        label="Inicio de vigencia",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class GradoPensumForm(AulaProModelForm):
    class Meta:
        model = GradoPensum
        fields = ("codigo", "nombre", "numero_orden", "activo")


class CursoPensumForm(AulaProModelForm):
    class Meta:
        model = CursoPensum
        fields = (
            "grado",
            "curso",
            "orden",
            "periodos_semanales",
            "obligatorio",
            "observaciones",
            "activo",
        )
        widgets = {"observaciones": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, pensum, **kwargs):
        super().__init__(*args, **kwargs)
        self.pensum = pensum
        self.fields["grado"].queryset = pensum.grados.filter(activo=True)
        self.fields["curso"].queryset = CursoCatalogo.objects.filter(
            activo=True
        ).order_by("nombre")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.pensum = self.pensum
        if commit:
            instance.save()
        return instance
