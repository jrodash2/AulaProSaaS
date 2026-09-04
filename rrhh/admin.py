from django.contrib import admin
from .models import *
for model in (AreaLaboral,PuestoLaboral,Empleado,ContratoLaboral,MovimientoLaboral,TipoDocumentoEmpleado,DocumentoEmpleado,PermisoLaboral):admin.site.register(model)
