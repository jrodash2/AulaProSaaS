from django.contrib import admin
from .models import AdjuntoEntrega,AdjuntoTarea,EntregaTarea,Tarea
for x in (Tarea,AdjuntoTarea,EntregaTarea,AdjuntoEntrega):admin.site.register(x)
