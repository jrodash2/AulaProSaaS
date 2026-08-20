from django.urls import path

from . import views

app_name = "catalogos"
urlpatterns = [
    path("carreras/", views.carrera_lista, name="carrera_lista"),
    path("carreras/nueva/", views.carrera_formulario, name="carrera_crear"),
    path("carreras/<uuid:uuid>/", views.carrera_detalle, name="carrera_detalle"),
    path(
        "carreras/<uuid:uuid>/editar/", views.carrera_formulario, name="carrera_editar"
    ),
    path(
        "carreras/<uuid:carrera_uuid>/pensum/nuevo/",
        views.pensum_formulario,
        name="pensum_crear",
    ),
    path(
        "carreras/<uuid:carrera_uuid>/pensum/<uuid:uuid>/editar/",
        views.pensum_formulario,
        name="pensum_editar",
    ),
    path("pensum/<uuid:uuid>/", views.pensum_editor, name="pensum_editor"),
    path("pensum/<uuid:uuid>/duplicar/", views.pensum_duplicar, name="pensum_duplicar"),
    path(
        "pensum/<uuid:pensum_uuid>/grados/nuevo/",
        views.grado_formulario,
        name="grado_crear",
    ),
    path(
        "pensum/<uuid:pensum_uuid>/grados/<int:pk>/editar/",
        views.grado_formulario,
        name="grado_editar",
    ),
    path(
        "pensum/<uuid:pensum_uuid>/cursos/agregar/",
        views.curso_pensum_formulario,
        name="curso_pensum_agregar",
    ),
    path(
        "pensum/<uuid:pensum_uuid>/cursos/<int:pk>/editar/",
        views.curso_pensum_formulario,
        name="curso_pensum_editar",
    ),
    path(
        "pensum/<uuid:pensum_uuid>/cursos/<int:pk>/quitar/",
        views.curso_pensum_quitar,
        name="curso_pensum_quitar",
    ),
    path("<slug:tipo>/", views.referencia_lista, name="referencia_lista"),
    path("<slug:tipo>/nuevo/", views.referencia_formulario, name="referencia_crear"),
    path(
        "<slug:tipo>/<int:pk>/editar/",
        views.referencia_formulario,
        name="referencia_editar",
    ),
]
