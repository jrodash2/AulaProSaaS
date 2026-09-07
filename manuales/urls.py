from django.urls import path

from . import views

app_name = "manuales"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("mi-manual/", views.mi_manual, name="mi_manual"),
    path("<slug:rol>/", views.manual, name="manual"),
    path("<slug:rol>/<slug:seccion>/", views.seccion, name="seccion"),
]
