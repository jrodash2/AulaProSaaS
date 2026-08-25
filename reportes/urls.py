from django.urls import path
from . import views
app_name="reportes"
urlpatterns=[path("",views.dashboard,name="dashboard"),path("alumnos/",views.alumnos,name="alumnos"),path("academico/",views.academico,name="academico"),path("asistencia/",views.asistencia,name="asistencia"),path("calificaciones/",views.calificaciones,name="calificaciones"),path("docentes/",views.docentes,name="docentes"),path("tareas/",views.tareas,name="tareas"),path("finanzas/",views.finanzas,name="finanzas"),path("comunicacion/",views.comunicacion,name="comunicacion"),path("exportar/alumnos.xlsx",views.exportar_alumnos,name="exportar_alumnos"),path("exportar/asistencia.xlsx",views.exportar_asistencia,name="exportar_asistencia"),path("exportar/finanzas.xlsx",views.exportar_finanzas,name="exportar_finanzas")]
