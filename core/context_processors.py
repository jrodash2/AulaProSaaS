def aulapro_context(request):
    from django.conf import settings
    from suscripciones.models import ModuloSaaS
    modulos = {codigo: True for codigo, _ in ModuloSaaS.Codigo.choices}
    if getattr(request, "institucion", None) and request.user.is_authenticated:
        from suscripciones.services import suscripcion_actual
        suscripcion = suscripcion_actual(request.institucion)
        if suscripcion:
            habilitados = set(suscripcion.plan.configuracion_modulos.filter(habilitado=True, modulo__activo=True).values_list("modulo__codigo", flat=True))
            modulos = {codigo: codigo in habilitados for codigo in modulos}
    return {
        "institucion_activa": getattr(request, "institucion", None),
        "es_superadministrador": request.user.is_authenticated and request.user.is_superuser,
        "modulos_saas": modulos,
        "suscripcion_actual": getattr(request, "suscripcion_actual", None),
        "static_asset_version": settings.STATIC_ASSET_VERSION,
        "es_entorno_demo": getattr(getattr(request, "institucion", None), "codigo", None) == "AULAPRO-DEMO",
    }
