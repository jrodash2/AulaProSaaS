from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("plataforma/", views.global_dashboard, name="global_dashboard"),
    path("inicio/", views.institucion_dashboard, name="institucion_dashboard"),
    path("demo/guia/", views.demo_guia, name="demo_guia"),
    path("sin-institucion/", views.sin_institucion, name="sin_institucion"),
    path("perfil/", views.perfil, name="perfil"),
    path("perfil/cambiar-contrasena/", views.cambiar_password, name="cambiar_password"),
    path("mis-instituciones/", views.mis_instituciones, name="mis_instituciones"),
    path("mis-instituciones/<int:asignacion_id>/entrar/", views.cambiar_institucion, name="cambiar_institucion"),
    path("plataforma/auditoria/", views.auditoria, name="auditoria"),
    path("plataforma/auditoria/<int:pk>/", views.auditoria_detalle, name="auditoria_detalle"),
    path("plataforma/usuarios/", views.usuarios_globales, name="usuarios_globales"),
    path("plataforma/usuarios/<int:pk>/", views.usuario_global_detalle, name="usuario_global_detalle"),
    path("plataforma/sistema/", views.sistema, name="sistema"),
    path("modulos/<slug:modulo>/", views.modulo, name="modulo"),
]
