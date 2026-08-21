from django import forms
from django.db import models

from catalogos.models import CarreraCatalogo, CursoCatalogo, NivelEducativo, VersionPensum

from .models import CicloEscolar, CursoInstitucion, JornadaInstitucion, Seccion


class AulaProFormMixin:
    def aplicar_estilos(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            field.widget.attrs.setdefault("class", css)


class CicloEscolarForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = CicloEscolar
        fields = ("nombre", "anio", "fecha_inicio", "fecha_fin", "es_actual")
        widgets = {"fecha_inicio": forms.DateInput(attrs={"type": "date"}), "fecha_fin": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.aplicar_estilos()


class JornadaForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = JornadaInstitucion
        fields = ("codigo", "nombre", "hora_inicio", "hora_fin", "orden", "activa")
        widgets = {"hora_inicio": forms.TimeInput(attrs={"type": "time"}), "hora_fin": forms.TimeInput(attrs={"type": "time"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.aplicar_estilos()


class OfertaPensumForm(AulaProFormMixin, forms.Form):
    nivel = forms.ModelChoiceField(queryset=NivelEducativo.objects.none())
    carrera = forms.ModelChoiceField(queryset=CarreraCatalogo.objects.none())
    pensum = forms.ModelChoiceField(queryset=VersionPensum.objects.none(), label="Versión de pensum")
    nombre_mostrado = forms.CharField(max_length=220, required=False)
    codigo_interno = forms.CharField(max_length=50, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nivel"].queryset = NivelEducativo.objects.filter(activo=True)
        self.fields["carrera"].queryset = CarreraCatalogo.objects.filter(activa=True).select_related("nivel")
        carrera_id = self.data.get("carrera") or self.initial.get("carrera")
        self.fields["pensum"].queryset = VersionPensum.objects.filter(carrera_id=carrera_id).order_by(models.Case(models.When(estado=VersionPensum.Estado.VIGENTE, then=0), default=1), "-fecha_inicio_vigencia") if carrera_id else VersionPensum.objects.none()
        self.aplicar_estilos()

    def clean(self):
        cleaned = super().clean()
        carrera, pensum, nivel = cleaned.get("carrera"), cleaned.get("pensum"), cleaned.get("nivel")
        if carrera and nivel and carrera.nivel_id != nivel.pk:
            self.add_error("carrera", "La carrera no pertenece al nivel seleccionado.")
        if carrera and pensum and pensum.carrera_id != carrera.pk:
            self.add_error("pensum", "El pensum no pertenece a la carrera seleccionada.")
        return cleaned


class SeccionForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = Seccion
        fields = ("grado", "jornada", "codigo", "nombre", "capacidad", "activa")

    def __init__(self, *args, institucion, ciclo, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grado"].queryset = ciclo.grados.filter(institucion=institucion, activo=True)
        self.fields["jornada"].queryset = institucion.jornadas.filter(activa=True)
        self.aplicar_estilos()


class CursoInstitucionForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = CursoInstitucion
        fields = ("curso_catalogo", "nombre_personalizado", "nombre_mostrado", "periodos_semanales", "obligatorio", "origen", "orden", "activo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["curso_catalogo"].queryset = CursoCatalogo.objects.filter(activo=True)
        self.aplicar_estilos()
