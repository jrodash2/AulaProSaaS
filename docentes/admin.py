from django.contrib import admin
from .models import AsignacionDocente,AsignacionGuia,Docente
admin.site.register([Docente,AsignacionDocente,AsignacionGuia])
