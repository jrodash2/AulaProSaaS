from django.urls import path
from . import views

app_name = "academico"
urlpatterns = [
    path("", views.landing, name="landing"),
    path("ciclos/", views.ciclos_lista, name="ciclos"), path("ciclos/nuevo/", views.ciclo_formulario, name="ciclo_crear"),
    path("ciclos/<int:pk>/", views.ciclo_detalle, name="ciclo_detalle"),
    path("ciclos/<int:pk>/cierre/", views.ciclo_cierre, name="ciclo_cierre"),
    path("ciclos/<int:pk>/cierre/iniciar/", views.ciclo_iniciar_cierre, name="ciclo_iniciar_cierre"),
    path("ciclos/<int:pk>/resultados/", views.resultados_anuales, name="resultados_anuales"),
    path("ciclos/<int:pk>/resultados/generar/", views.resultados_generar, name="resultados_generar"),
    path("resultados/<int:pk>/confirmar/", views.resultado_confirmar, name="resultado_confirmar"),
    path("ciclos/<int:pk>/resultados/confirmar-sugerencias/", views.resultados_confirmar_sugerencias, name="resultados_confirmar_sugerencias"),
    path("ciclos/<int:pk>/cerrar/", views.ciclo_cerrar, name="ciclo_cerrar"),
    path("ciclos/<int:pk>/crear-siguiente/", views.ciclo_crear_siguiente, name="ciclo_crear_siguiente"),
    path("ciclos/<int:pk>/editar/", views.ciclo_formulario, name="ciclo_editar"), path("ciclos/<int:pk>/actual/", views.ciclo_actual, name="ciclo_actual"),
    path("jornadas/", views.jornadas_lista, name="jornadas"), path("jornadas/nueva/", views.jornada_formulario, name="jornada_crear"),
    path("jornadas/<int:pk>/", views.jornada_detalle, name="jornada_detalle"),
    path("jornadas/<int:pk>/editar/", views.jornada_formulario, name="jornada_editar"), path("jornadas/<int:pk>/estado/", views.jornada_estado, name="jornada_estado"),
    path("oferta/", views.ofertas_lista, name="ofertas"), path("oferta/agregar/", views.oferta_agregar, name="oferta_agregar"),
    path("oferta/opciones-catalogo/", views.opciones_catalogo, name="opciones_catalogo"),
    path("oferta/<int:pk>/", views.oferta_detalle, name="oferta_detalle"), path("oferta/<int:pk>/estado/", views.oferta_estado, name="oferta_estado"),
    path("grados-secciones/", views.grados_secciones, name="grados_secciones"),
    path("grados/<int:pk>/", views.grado_detalle, name="grado_detalle"),
    path("grados/<int:grado_pk>/secciones/nueva/", views.seccion_formulario, name="seccion_crear"),
    path("secciones/<int:pk>/editar/", views.seccion_formulario, name="seccion_editar"), path("secciones/<int:pk>/estado/", views.seccion_estado, name="seccion_estado"),
    path("secciones/<int:pk>/", views.seccion_detalle, name="seccion_detalle"),
    path("cursos/", views.cursos_lista, name="cursos"), path("grados/<int:grado_pk>/cursos/nuevo/", views.curso_formulario, name="curso_crear"),
    path("cursos/<int:pk>/", views.curso_detalle, name="curso_detalle"),
    path("grados/<int:grado_pk>/cursos/<int:pk>/editar/", views.curso_formulario, name="curso_editar"), path("cursos/<int:pk>/estado/", views.curso_estado, name="curso_estado"),
]
