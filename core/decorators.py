from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from .permissions import GESTION_INSTITUCIONAL,GESTION_ALUMNOS


def superusuario_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def institucion_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect("core:global_dashboard")
        if not request.institucion:
            messages.warning(request, "Tu usuario no tiene una institución activa asignada.")
            return redirect("core:sin_institucion")
        return view(request, *args, **kwargs)
    return wrapped


def administrador_institucion_required(view):
    """Limita la administración de cuentas a roles directivos del tenant activo."""
    @institucion_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.asignacion_institucion.rol not in GESTION_INSTITUCIONAL:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def gestion_alumnos_required(view):
    """Autoriza expedientes a roles directivos y secretaría del tenant activo."""
    @institucion_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.asignacion_institucion.rol not in GESTION_ALUMNOS:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def lectura_docentes_required(view):
    @institucion_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.asignacion_institucion.rol not in GESTION_ALUMNOS:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped
