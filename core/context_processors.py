def aulapro_context(request):
    return {
        "institucion_activa": getattr(request, "institucion", None),
        "es_superadministrador": request.user.is_authenticated and request.user.is_superuser,
    }
