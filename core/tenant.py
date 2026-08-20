from instituciones.models import UsuarioInstitucion


def obtener_asignacion_activa(request):
    """Resuelve el tenant exclusivamente entre asignaciones activas del usuario."""
    if not request.user.is_authenticated or request.user.is_superuser:
        return None
    asignaciones = UsuarioInstitucion.objects.select_related("institucion").filter(
        usuario=request.user,
        activo=True,
        institucion__activa=True,
    )
    asignacion_id = request.session.get("asignacion_institucion_id")
    asignacion = asignaciones.filter(pk=asignacion_id).first() if asignacion_id else None
    if asignacion is None:
        asignacion = asignaciones.order_by("fecha_asignacion", "pk").first()
        if asignacion:
            request.session["asignacion_institucion_id"] = asignacion.pk
    return asignacion
