from django.contrib import admin
from .models import *
for x in (ConfiguracionFinanciera,ConceptoCobro,MetodoPago,Cargo,Pago,AplicacionPago):admin.site.register(x)
