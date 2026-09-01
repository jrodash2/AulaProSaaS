from django.urls import path
from . import views
app_name="portal"
urlpatterns=[
 path("",views.dashboard,name="dashboard"),path("seleccionar/<int:pk>/",views.seleccionar,name="seleccionar"),
 path("estudiantes/<int:pk>/",views.estudiante,name="estudiante"),path("estudiantes/<int:pk>/asistencia/",views.asistencia,name="asistencia"),path("estudiantes/<int:pk>/calificaciones/",views.calificaciones,name="calificaciones"),path("estudiantes/<int:pk>/tareas/",views.tareas,name="tareas"),path("estudiantes/<int:pk>/tareas/<int:tarea_pk>/",views.tarea_detalle,name="tarea"),path("estudiantes/<int:pk>/finanzas/",views.finanzas,name="finanzas"),path("estudiantes/<int:pk>/recibos/",views.recibos,name="recibos"),path("estudiantes/<int:pk>/recibos/<int:pago_pk>/",views.recibo,name="recibo"),path("estudiantes/<int:pk>/adjuntos-tarea/<int:adjunto_pk>/",views.descargar_tarea,name="descargar_tarea"),path("estudiantes/<int:pk>/adjuntos-entrega/<int:adjunto_pk>/",views.descargar_entrega,name="descargar_entrega"),
 path("estudiantes/<int:pk>/documentos/",views.documentos,name="documentos"),path("estudiantes/<int:pk>/documentos/subir/",views.documento_subir,name="documento_subir"),path("estudiantes/<int:pk>/documentos/<int:documento_pk>/descargar/",views.documento_descargar,name="documento_descargar"),
 path("admin/encargados/<int:pk>/acceso/",views.acceso_encargado,name="acceso_encargado"),path("admin/alumnos/<int:pk>/acceso/",views.acceso_alumno,name="acceso_alumno"),path("admin/<str:tipo>/<int:pk>/revocar/",views.revocar_acceso,name="revocar"),
]
