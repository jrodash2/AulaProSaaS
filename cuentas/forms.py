from django import forms
from django.contrib.auth.forms import AuthenticationForm


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
