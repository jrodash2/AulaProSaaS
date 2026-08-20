from django.urls import path
from . import views

app_name = "academico"
urlpatterns = [
    path("", views.landing, name="landing"),
    path("ciclos/", views.ciclos_lista, name="ciclos"), path("ciclos/nuevo/", views.ciclo_formulario, name="ciclo_crear"),
    path("ciclos/<int:pk>/editar/", views.ciclo_formulario, name="ciclo_editar"), path("ciclos/<int:pk>/actual/", views.ciclo_actual, name="ciclo_actual"),
    path("jornadas/", views.jornadas_lista, name="jornadas"), path("jornadas/nueva/", views.jornada_formulario, name="jornada_crear"),
    path("jornadas/<int:pk>/editar/", views.jornada_formulario, name="jornada_editar"), path("jornadas/<int:pk>/estado/", views.jornada_estado, name="jornada_estado"),
    path("oferta/", views.ofertas_lista, name="ofertas"), path("oferta/agregar/", views.oferta_agregar, name="oferta_agregar"),
    path("oferta/opciones-catalogo/", views.opciones_catalogo, name="opciones_catalogo"),
    path("oferta/<int:pk>/", views.oferta_detalle, name="oferta_detalle"), path("oferta/<int:pk>/estado/", views.oferta_estado, name="oferta_estado"),
    path("grados-secciones/", views.grados_secciones, name="grados_secciones"),
    path("grados/<int:grado_pk>/secciones/nueva/", views.seccion_formulario, name="seccion_crear"),
    path("secciones/<int:pk>/editar/", views.seccion_formulario, name="seccion_editar"), path("secciones/<int:pk>/estado/", views.seccion_estado, name="seccion_estado"),
    path("cursos/", views.cursos_lista, name="cursos"), path("grados/<int:grado_pk>/cursos/nuevo/", views.curso_formulario, name="curso_crear"),
    path("grados/<int:grado_pk>/cursos/<int:pk>/editar/", views.curso_formulario, name="curso_editar"), path("cursos/<int:pk>/estado/", views.curso_estado, name="curso_estado"),
]
