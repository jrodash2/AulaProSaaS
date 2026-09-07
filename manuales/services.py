from django.core.exceptions import PermissionDenied

from .registry import MANUALES


def rol_actual(request):
    if request.user.is_superuser:
        return "superadmin"
    asignacion = getattr(request, "asignacion_institucion", None)
    if not asignacion:
        raise PermissionDenied("Selecciona una institución para consultar tu manual.")
    return asignacion.rol.lower()


def puede_consultar(request, rol):
    return request.user.is_superuser or rol_actual(request) == rol


def manual_visible(request, rol):
    if rol not in MANUALES or not puede_consultar(request, rol):
        raise PermissionDenied("Este manual no corresponde a tu rol.")
    manual = {**MANUALES[rol]}
    modulos = {}
    institucion = getattr(request, "institucion", None)
    if institucion and not request.user.is_superuser:
        from suscripciones.services import suscripcion_actual
        suscripcion = suscripcion_actual(institucion)
        if suscripcion:
            habilitados = set(suscripcion.plan.configuracion_modulos.filter(
                habilitado=True, modulo__activo=True
            ).values_list("modulo__codigo", flat=True))
            modulos = {codigo: codigo in habilitados for codigo in habilitados}
    if not request.user.is_superuser and modulos:
        manual["secciones"] = [
            item for item in manual["secciones"]
            if not item.get("modulo") or modulos.get(item["modulo"], False)
        ]
    return manual
