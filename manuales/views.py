from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.conf import settings

from .registry import MANUALES
from .services import manual_visible, rol_actual


def _context(request, rol, manual, actual=None):
    institucion = getattr(request, "institucion", None)
    return {"rol_slug": rol, "manual": manual, "seccion": actual,
            "institucion_manual": institucion, "manuales": MANUALES}


@login_required
def inicio(request):
    rol = rol_actual(request)
    recomendado = manual_visible(request, rol)
    disponibles = MANUALES if request.user.is_superuser else {rol: recomendado}
    return render(request, "manuales/inicio.html", {"rol_slug": rol,
                  "manual": recomendado, "manuales": disponibles,
                  "app_version": settings.APP_VERSION})


@login_required
def mi_manual(request):
    return redirect("manuales:manual", rol=rol_actual(request))


@login_required
def manual(request, rol):
    data = manual_visible(request, rol)
    return render(request, "manuales/manual.html", _context(request, rol, data))


@login_required
def seccion(request, rol, seccion):
    data = manual_visible(request, rol)
    items = data["secciones"]
    actual = next((item for item in items if item["slug"] == seccion), None)
    if not actual:
        raise Http404("La sección no existe o no está disponible en tu plan.")
    indice = items.index(actual)
    actual = {**actual, "anterior": items[indice - 1] if indice else None,
              "siguiente": items[indice + 1] if indice + 1 < len(items) else None}
    return render(request, "manuales/seccion.html", _context(request, rol, data, actual))
