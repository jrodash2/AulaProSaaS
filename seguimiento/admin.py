from django.contrib import admin
from .models import *
for modelo in (CategoriaSeguimiento,RegistroSeguimiento,CompromisoSeguimiento,NotaSeguimiento,ReunionSeguimiento,AdjuntoSeguimiento):admin.site.register(modelo)
