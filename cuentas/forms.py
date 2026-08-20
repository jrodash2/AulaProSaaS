from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    SetPasswordForm,
    UserCreationForm,
)

from instituciones.models import UsuarioInstitucion

from .models import Usuario


class AulaProAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Usuario", "autofocus": True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña"}))
    remember_me = forms.BooleanField(required=False, label="Recordarme")

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.activo:
            raise forms.ValidationError("Esta cuenta se encuentra inactiva.", code="inactive")

    def get_user(self):
        user = super().get_user()
        if user and not self.cleaned_data.get("remember_me"):
            self.request.session.set_expiry(0)
        return user


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class UsuarioInstitucionCrearForm(UserCreationForm):
    rol = forms.ChoiceField(choices=UsuarioInstitucion.Rol.choices)

    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "username", "email", "rol", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"


class UsuarioInstitucionEditarForm(forms.ModelForm):
    rol = forms.ChoiceField(choices=UsuarioInstitucion.Rol.choices)
    activo = forms.BooleanField(required=False)

    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email", "rol", "activo")

    def __init__(self, *args, asignacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        if asignacion:
            self.fields["rol"].initial = asignacion.rol
            self.fields["activo"].initial = asignacion.activo
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-select" if isinstance(field.widget, forms.Select) else "form-control"


class AulaProPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class AulaProSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
