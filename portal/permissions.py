from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from alumnos.models import Alumno, AlumnoEncargado

def rol_portal(request):
    return getattr(getattr(request,"asignacion_institucion",None),"rol",None)

def portal_role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(request,*args,**kwargs):
            if not request.user.is_authenticated: raise PermissionDenied
            if rol_portal(request) not in roles: raise PermissionDenied
            return view(request,*args,**kwargs)
        return login_required(wrapped)
    return decorator

def alumnos_permitidos(request):
    qs=Alumno.objects.filter(institucion=request.institucion)
    if rol_portal(request)=="ALUMNO": return qs.filter(usuario=request.user)
    if rol_portal(request)=="PADRE":
        return qs.filter(vinculos_encargados__encargado__usuario=request.user,vinculos_encargados__activo=True,vinculos_encargados__encargado__activo=True).distinct()
    return qs.none()

def get_alumno_portal(request,pk):
    return get_object_or_404(alumnos_permitidos(request),pk=pk)
