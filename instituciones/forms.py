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
    propietario_username = forms.CharField(max_length=150, label="Usuario propietario")
    propietario_email = forms.EmailField(label="Email del propietario")
    propietario_password = forms.CharField(min_length=8, widget=forms.PasswordInput, label="Contraseña inicial")
    class Meta(InstitucionForm.Meta):
        fields = ("nombre", "nombre_corto", "codigo", "razon_social", "direccion", "departamento", "municipio", "telefono", "email", "sitio_web", "logo_principal", "logo_secundario", "color_primario", "color_secundario", "activa")

    def clean(self):
        cleaned = super().clean()
        if not self.instance.pk and not cleaned.get("plan"):
            self.add_error("plan", "Seleccione el plan inicial.")
        if not self.instance.pk and cleaned.get("propietario_username"):
            from django.contrib.auth import get_user_model
            if get_user_model().objects.filter(username__iexact=cleaned["propietario_username"]).exists():
                self.add_error("propietario_username", "Este nombre de usuario ya está registrado.")
        return cleaned


class OnboardingFinanzasForm(AulaProFormMixin, forms.Form):
    moneda = forms.CharField(max_length=3, initial="GTQ")
    simbolo_moneda = forms.CharField(max_length=5, initial="Q")
    dia_vencimiento_mensualidad = forms.IntegerField(min_value=1, max_value=28, initial=10)
    prefijo_recibo = forms.CharField(max_length=20, initial="REC")
    crear_inscripcion = forms.BooleanField(required=False, initial=True, label="Crear concepto Inscripción")
    monto_inscripcion = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2)
    crear_colegiatura = forms.BooleanField(required=False, initial=True, label="Crear concepto Colegiatura")
    monto_colegiatura = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2)
