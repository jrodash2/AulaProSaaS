from django import forms

from .models import Institucion


class InstitucionForm(forms.ModelForm):
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
