from django.urls import path

from . import views

app_name = "instituciones"
urlpatterns = [
    path("configuracion/", views.configuracion, name="configuracion"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/nuevo/", views.usuario_crear, name="usuario_crear"),
    path("usuarios/<int:pk>/", views.usuario_detalle, name="usuario_detalle"),
    path("usuarios/<int:pk>/editar/", views.usuario_editar, name="usuario_editar"),
    path("usuarios/<int:pk>/estado/", views.usuario_estado, name="usuario_estado"),
    path("usuarios/<int:pk>/restablecer-contrasena/", views.usuario_password, name="usuario_password"),
    path("plataforma/", views.lista, name="lista"),
    path("plataforma/nueva/", views.crear, name="crear"),
    path("plataforma/<uuid:uuid>/", views.detalle, name="detalle"),
    path("plataforma/<uuid:uuid>/editar/", views.editar, name="editar"),
    path("plataforma/<uuid:uuid>/estado/", views.cambiar_estado, name="estado"),
]
