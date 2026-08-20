from .models import EventoAuditoria


def obtener_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")


def registrar_evento(request, accion, objeto):
    return EventoAuditoria.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
        institucion=getattr(request, "institucion", None),
        accion=accion,
        modelo=objeto._meta.label,
        objeto_id=str(objeto.pk),
        ip=obtener_ip(request),
    )
