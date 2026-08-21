from django.urls import path
from . import views
app_name="docentes"
urlpatterns=[
 path("",views.lista,name="lista"),path("nuevo/",views.crear,name="crear"),path("exportar/",views.exportar,name="exportar"),path("<int:pk>/",views.detalle,name="detalle"),path("<int:pk>/editar/",views.editar,name="editar"),path("<int:pk>/crear-acceso/",views.crear_acceso,name="crear_acceso"),path("<int:pk>/acceso/estado/",views.acceso_estado,name="acceso_estado"),
 path("asignaciones/listado/",views.asignaciones,name="asignaciones"),path("asignaciones/nueva/",views.asignacion_form,name="asignacion_crear"),path("asignaciones/<int:pk>/",views.asignacion_detalle,name="asignacion_detalle"),path("asignaciones/<int:pk>/editar/",views.asignacion_form,name="asignacion_editar"),path("asignaciones/<int:pk>/estado/",views.asignacion_estado,name="asignacion_estado"),path("secciones/<int:seccion_pk>/asignacion-rapida/",views.asignacion_rapida,name="asignacion_rapida"),path("secciones/<int:seccion_pk>/guia/",views.guia,name="guia"),
 path("carga/",views.carga,name="carga"),path("carga/exportar/",views.exportar_carga,name="exportar_carga"),path("mis-clases/",views.mis_clases,name="mis_clases"),path("mis-clases/<int:pk>/",views.mi_clase,name="mi_clase"),path("opciones/",views.opciones,name="opciones"),
]
