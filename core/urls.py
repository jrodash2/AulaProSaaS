from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("plataforma/", views.global_dashboard, name="global_dashboard"),
    path("inicio/", views.institucion_dashboard, name="institucion_dashboard"),
    path("sin-institucion/", views.sin_institucion, name="sin_institucion"),
]
