from django.contrib import messages
from django.shortcuts import redirect, render

from auditoria.services import registrar_evento
from core.decorators import institucion_required

from .forms import InstitucionForm


@institucion_required
def configuracion(request):
    institucion = request.institucion
    if request.method == "POST":
        form = InstitucionForm(request.POST, request.FILES, instance=institucion)
        if form.is_valid():
            form.save()
            registrar_evento(request, "ACTUALIZAR", institucion)
            messages.success(request, "La información institucional se actualizó correctamente.")
            return redirect("instituciones:configuracion")
    else:
        form = InstitucionForm(instance=institucion)
    return render(request, "instituciones/configuracion.html", {"form": form})
