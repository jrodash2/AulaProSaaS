from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class LoginUIRegressionTests(TestCase):
    def test_login_renderiza_panel_educativo_y_controles_accesibles(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestión educativa moderna")
        self.assertContains(response, "Bienvenido a AulaPro")
        self.assertContains(response, 'aria-label="Mostrar contraseña"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_login_invalido_muestra_mensaje_amigable(self):
        response = self.client.post(reverse("login"), {"username": "nadie", "password": "incorrecta"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuario o contraseña incorrectos. Verifica tus datos.")
        self.assertNotContains(response, "Traceback")

    def test_login_valido_conserva_redireccion(self):
        get_user_model().objects.create_user(username="login-ui", password="Segura-2026")
        response = self.client.post(reverse("login"), {"username": "login-ui", "password": "Segura-2026", "next": reverse("core:perfil")})
        self.assertRedirects(response, reverse("core:perfil"), fetch_redirect_response=False)
