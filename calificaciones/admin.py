from django.contrib import admin
from .models import *
for model in (ConfiguracionCalificaciones,PeriodoAcademico,TipoEvaluacion,ActividadEvaluacion,Calificacion):admin.site.register(model)
