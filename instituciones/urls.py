from django.urls import path

from . import views

app_name = "instituciones"
urlpatterns = [path("configuracion/", views.configuracion, name="configuracion")]
