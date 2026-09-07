from django.contrib import admin
from .models import *
for m in (ConfiguracionAdmision,Aspirante,EncargadoAspirante,SolicitudAdmision,TipoDocumentoAdmision,DocumentoAdmision,EntrevistaAdmision,TipoEvaluacionAdmision,EvaluacionAdmision):admin.site.register(m)
