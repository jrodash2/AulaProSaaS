from django.urls import path
from . import views
app_name='admisiones'
urlpatterns=[path('',views.dashboard,name='dashboard'),path('solicitudes/',views.solicitudes,name='solicitudes'),path('solicitudes/<int:pk>/',views.detalle,name='detalle'),path('solicitudes/<int:pk>/estado/',views.estado,name='estado'),path('solicitudes/<int:pk>/convertir/',views.convertir,name='convertir'),path('solicitudes/<int:pk>/entrevista/',views.entrevista,name='entrevista'),path('solicitudes/<int:pk>/evaluacion/',views.evaluacion,name='evaluacion'),path('solicitar/<str:codigo>/',views.solicitar,name='publica'),path('estado/<uuid:token>/',views.portal,name='portal'),path('estado/<uuid:token>/documentos/',views.documento_publico,name='documento_publico')]
