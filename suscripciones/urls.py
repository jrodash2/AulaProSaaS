from django.urls import path
from . import views

app_name = "suscripciones"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("planes/", views.planes, name="planes"),
    path("planes/nuevo/", views.plan_form, name="plan_nuevo"),
    path("planes/<int:pk>/", views.plan_detalle, name="plan_detalle"),
    path("planes/<int:pk>/editar/", views.plan_form, name="plan_editar"),
    path("suscripciones/", views.lista_suscripciones, name="lista"),
    path("suscripciones/nueva/", views.suscripcion_form, name="nueva"),
    path("suscripciones/<int:pk>/", views.detalle, name="detalle"),
    path("suscripciones/<int:pk>/editar/", views.suscripcion_form, name="editar"),
    path("suscripciones/<int:pk>/renovar/", views.renovar, name="renovar"),
    path("suscripciones/<int:pk>/cambiar-plan/", views.cambiar_plan_view, name="cambiar_plan"),
    path("suscripciones/<int:pk>/estado/<slug:estado>/", views.estado_view, name="estado"),
    path("solicitudes/", views.solicitudes, name="solicitudes"),
    path("solicitudes/<int:pk>/<slug:estado>/", views.solicitud_estado, name="solicitud_estado"),
    path("uso/", views.uso, name="uso"),
]
