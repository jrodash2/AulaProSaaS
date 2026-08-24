from django.contrib import admin
from .models import RegistroAsistencia, SesionAsistencia
admin.site.register(SesionAsistencia)
admin.site.register(RegistroAsistencia)
