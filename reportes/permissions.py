from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
FULL={"PROPIETARIO","DIRECTOR","ADMINISTRADOR"}
ACADEMICOS=FULL|{"SECRETARIA"}
FINANCIEROS=FULL|{"CONTABILIDAD"}
DOCENTE={"DOCENTE"}
MAPA={"dashboard":FULL|DOCENTE|{"SECRETARIA","CONTABILIDAD"},"alumnos":ACADEMICOS,"academico":ACADEMICOS,"asistencia":ACADEMICOS|DOCENTE,"calificaciones":FULL|DOCENTE,"docentes":FULL,"tareas":FULL|DOCENTE,"finanzas":FINANCIEROS,"comunicacion":FULL}
def rol(request):return getattr(getattr(request,"asignacion_institucion",None),"rol",None)
def reporte_required(nombre):
 def deco(view):
  @wraps(view)
  @login_required
  def wrapped(request,*a,**kw):
   if not getattr(request,"institucion",None) or rol(request) not in MAPA[nombre]:raise PermissionDenied
   return view(request,*a,**kw)
  return wrapped
 return deco
def es_docente(request):return rol(request)=="DOCENTE"
def puede_finanzas(request):return rol(request) in FINANCIEROS
