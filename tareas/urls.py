from django.urls import path
from . import views
app_name="tareas"
urlpatterns=[path("",views.dashboard,name="dashboard"),path("todas/",views.lista,name="lista"),path("proximas/",views.proximas,name="proximas"),path("nueva/",views.formulario,name="nueva"),path("<int:pk>/",views.detalle,name="detalle"),path("<int:pk>/editar/",views.formulario,name="editar"),path("<int:pk>/estado/",views.estado,name="estado"),path("<int:pk>/adjuntos/<int:adjunto_id>/",views.descargar,name="descargar"),path("reportes/",views.reportes,name="reportes"),path("exportar/",views.exportar,name="exportar"),path("alumnos/<int:pk>/",views.alumno,name="alumno")]
