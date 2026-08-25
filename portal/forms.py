from django import forms
from core.forms import AulaProFormMixin
from tareas.models import validar_archivo_seguro

class EntregaForm(AulaProFormMixin, forms.Form):
    archivo = forms.FileField(validators=[validar_archivo_seguro])
    comentario = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

class AccesoPortalForm(AulaProFormMixin, forms.Form):
    username=forms.CharField(label="Usuario",max_length=150)
    email=forms.EmailField()
    password=forms.CharField(label="Contraseña inicial",widget=forms.PasswordInput)
    def clean_username(self):
        from cuentas.models import Usuario
        username=self.cleaned_data["username"].strip()
        if Usuario.objects.filter(username=username).exists(): raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username
