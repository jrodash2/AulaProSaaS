from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .models import Suscripcion
from .services import estado_suscripcion, modulo_habilitado, suscripcion_actual


MAPA_MODULOS = {
    "/academico/": "ACADEMICO", "/alumnos/": "ALUMNOS", "/docentes/": "DOCENTES",
    "/asistencia/": "ASISTENCIA", "/calificaciones/": "CALIFICACIONES", "/tareas/": "TAREAS",
    "/finanzas/": "FINANZAS", "/portal/": "PORTAL", "/comunicacion/": "COMUNICACIONES", "/reportes/": "REPORTES",
}


class SuscripcionActivaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.suscripcion_actual = None
        request.estado_suscripcion = None
        request.suscripcion_solo_lectura = False
        if not request.user.is_authenticated or request.user.is_superuser or not getattr(request, "institucion", None):
            return self.get_response(request)
        suscripcion = suscripcion_actual(request.institucion)
        request.suscripcion_actual = suscripcion
        if not suscripcion:  # instituciones históricas continúan hasta ejecutar el comando de asignación
            return self.get_response(request)
        estado = estado_suscripcion(request.institucion)
        request.estado_suscripcion = estado
        request.suscripcion_solo_lectura = estado == Suscripcion.Estado.VENCIDA
        ruta_plan = request.path.startswith("/institucion/suscripcion/")
        rol = getattr(request.asignacion_institucion, "rol", "")
        if estado in (Suscripcion.Estado.SUSPENDIDA, Suscripcion.Estado.CANCELADA):
            if not ruta_plan and rol in ("PROPIETARIO", "DIRECTOR"):
                return redirect("mi_suscripcion:mi_plan")
            if not ruta_plan:
                raise PermissionDenied
        if request.suscripcion_solo_lectura and request.method not in ("GET", "HEAD", "OPTIONS") and not ruta_plan:
            return render(request, "suscripciones/solo_lectura.html", {"suscripcion": suscripcion}, status=403)
        for prefix, modulo in MAPA_MODULOS.items():
            if request.path.startswith(prefix) and not modulo_habilitado(request.institucion, modulo):
                return render(request, "suscripciones/modulo_no_incluido.html", {"modulo": modulo}, status=403)
        return self.get_response(request)
