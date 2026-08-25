from .permissions import alumnos_permitidos,rol_portal
def portal_context(request):
    if not request.user.is_authenticated or not getattr(request,"institucion",None) or rol_portal(request)!="PADRE": return {}
    alumnos=alumnos_permitidos(request);seleccionado=alumnos.filter(pk=request.session.get("portal_alumno_id")).first()
    return {"portal_alumnos":alumnos,"portal_alumno_seleccionado":seleccionado}
