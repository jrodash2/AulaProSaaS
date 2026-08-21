from django.urls import path
from . import views
app_name="alumnos"
urlpatterns=[
 path("",views.landing,name="landing"),path("estudiantes/",views.lista,name="lista"),path("estudiantes/nuevo/",views.crear,name="crear"),path("estudiantes/cui/",views.cui_disponible,name="cui_disponible"),path("inscripciones/opciones/",views.opciones_inscripcion,name="opciones_inscripcion"),path("estudiantes/exportar/",views.exportar,name="exportar"),path("estudiantes/<int:pk>/",views.detalle,name="detalle"),path("estudiantes/<int:pk>/editar/",views.editar,name="editar"),
 path("familias/",views.familias,name="familias"),path("familias/nueva/",views.familia_form,name="familia_crear"),path("familias/<int:pk>/",views.familia_detalle,name="familia_detalle"),path("familias/<int:pk>/editar/",views.familia_form,name="familia_editar"),
 path("encargados/",views.encargados,name="encargados"),path("encargados/nuevo/",views.encargado_form,name="encargado_crear"),path("encargados/<int:pk>/",views.encargado_detalle,name="encargado_detalle"),path("encargados/<int:pk>/editar/",views.encargado_form,name="encargado_editar"),
 path("inscripciones/",views.inscripciones,name="inscripciones"),path("estudiantes/<int:alumno_pk>/inscripciones/nueva/",views.inscripcion_form,name="inscripcion_crear"),path("estudiantes/<int:alumno_pk>/inscripciones/<int:pk>/editar/",views.inscripcion_form,name="inscripcion_editar"),path("inscripciones/<int:pk>/retirar/",views.retirar,name="retirar"),
 path("importaciones/",views.importaciones,name="importaciones"),path("importaciones/nueva/",views.importar,name="importar"),path("importaciones/plantilla/",views.plantilla,name="plantilla"),path("importaciones/<int:pk>/",views.importacion_detalle,name="importacion_detalle"),path("importaciones/<int:pk>/confirmar/",views.confirmar_importacion,name="confirmar_importacion"),
]
