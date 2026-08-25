from django.urls import path
from . import views

app_name = "mi_suscripcion"
urlpatterns = [path("", views.mi_plan, name="mi_plan"), path("solicitar-cambio/", views.solicitar_cambio, name="solicitar_cambio")]
