from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("plataforma/", views.global_dashboard, name="global_dashboard"),
    path("inicio/", views.institucion_dashboard, name="institucion_dashboard"),
    path("sin-institucion/", views.sin_institucion, name="sin_institucion"),
    path("perfil/", views.perfil, name="perfil"),
    path("mis-instituciones/", views.mis_instituciones, name="mis_instituciones"),
    path("mis-instituciones/<int:asignacion_id>/entrar/", views.cambiar_institucion, name="cambiar_institucion"),
    path("plataforma/auditoria/", views.auditoria, name="auditoria"),
    path("modulos/<slug:modulo>/", views.modulo, name="modulo"),
]
