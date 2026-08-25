from .models import Notificacion
def notificaciones_context(request):
    if not request.user.is_authenticated or not getattr(request,"institucion",None):return {}
    qs=Notificacion.objects.filter(institucion=request.institucion,usuario=request.user)
    return {"notificaciones_no_leidas":qs.filter(leida=False).count(),"notificaciones_recientes":qs[:5]}
