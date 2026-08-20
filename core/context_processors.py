def aulapro_context(request):
    asignaciones = []
    if request.user.is_authenticated and not request.user.is_superuser:
        asignaciones = list(
            request.user.asignaciones_institucion.select_related("institucion")
            .filter(activo=True, institucion__activa=True)
            .order_by("institucion__nombre")
        )
    return {
        "institucion_activa": getattr(request, "institucion", None),
        "es_superadministrador": request.user.is_authenticated
        and request.user.is_superuser,
        "instituciones_disponibles": asignaciones,
    }
