from django.urls import path
from . import views
app_name="asistencia"
urlpatterns=[
 path("",views.dashboard,name="dashboard"), path("tomar/",views.nueva,name="nueva"), path("sesiones/",views.sesiones,name="sesiones"), path("sesiones/exportar/",views.exportar_sesiones,name="exportar_sesiones"),
 path("sesiones/<int:pk>/",views.detalle,name="detalle"), path("sesiones/<int:pk>/tomar/",views.tomar,name="tomar"), path("sesiones/<int:pk>/reabrir/",views.reabrir,name="reabrir"), path("sesiones/<int:pk>/anular/",views.anular,name="anular"),
 path("justificaciones/",views.justificaciones,name="justificaciones"), path("justificaciones/<int:pk>/",views.justificar_view,name="justificar"), path("reportes/",views.reportes,name="reportes"),
 path("alumnos/<int:pk>/",views.alumno_historial,name="alumno_historial"), path("alumnos/<int:pk>/exportar/",views.exportar_alumno,name="exportar_alumno"),
]
