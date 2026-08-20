from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from cuentas.models import Usuario
from instituciones.models import Institucion

from .decorators import institucion_required, superusuario_required


@login_required
def inicio(request):
    if request.user.is_superuser:
        return redirect("core:global_dashboard")
    return redirect("core:institucion_dashboard")


@superusuario_required
def global_dashboard(request):
    context = {
        "total_instituciones": Institucion.objects.count(),
        "instituciones_activas": Institucion.objects.filter(activa=True).count(),
        "total_usuarios": Usuario.objects.count(),
        "ultimas_instituciones": Institucion.objects.order_by("-fecha_creacion")[:5],
    }
    return render(request, "core/global_dashboard.html", context)


@institucion_required
def institucion_dashboard(request):
    return render(request, "core/institucion_dashboard.html")


@login_required
def sin_institucion(request):
    return render(request, "core/sin_institucion.html")
