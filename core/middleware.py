from .tenant import obtener_asignacion_activa


class InstitucionActivaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.asignacion_institucion = obtener_asignacion_activa(request)
        request.institucion = (
            request.asignacion_institucion.institucion
            if request.asignacion_institucion
            else None
        )
        return self.get_response(request)
