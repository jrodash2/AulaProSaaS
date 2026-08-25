from core.forms import AulaProFormMixin
from django import forms

from .models import Institucion


class InstitucionForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = Institucion
        fields = ("nombre", "nombre_corto", "direccion", "departamento", "municipio", "telefono", "email", "sitio_web", "logo_principal", "logo_secundario", "color_primario", "color_secundario")
        widgets = {
            "direccion": forms.Textarea(attrs={"rows": 3}),
            "color_primario": forms.TextInput(attrs={"type": "color"}),
            "color_secundario": forms.TextInput(attrs={"type": "color"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        for field_name in ("logo_principal", "logo_secundario"):
            image = cleaned.get(field_name)
            if image and getattr(image, "size", 0) > 2 * 1024 * 1024:
                self.add_error(field_name, "La imagen no puede superar 2 MB.")
        return cleaned


class InstitucionCrearForm(InstitucionForm):
    plan = forms.ModelChoiceField(queryset=__import__("suscripciones.models", fromlist=["Plan"]).Plan.objects.filter(activo=True), required=False, help_text="Obligatorio para nuevas instituciones.")
    trial_dias = forms.IntegerField(min_value=0, initial=30, required=False, label="Días de prueba")
    class Meta(InstitucionForm.Meta):
        fields = ("nombre", "nombre_corto", "codigo", "razon_social", "direccion", "departamento", "municipio", "telefono", "email", "sitio_web", "logo_principal", "logo_secundario", "color_primario", "color_secundario", "activa")

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and not cleaned.get("plan"):
            self.add_error("plan", "Seleccione el plan inicial.")
        return cleaned
