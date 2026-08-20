from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.services import registrar_evento
from core.decorators import superusuario_required

from .forms import (
    AreaCurricularForm,
    CarreraCatalogoForm,
    CursoCatalogoForm,
    CursoPensumForm,
    DuplicarPensumForm,
    GradoPensumForm,
    NivelEducativoForm,
    TipoCarreraForm,
    VersionPensumForm,
)
from .models import (
    AreaCurricular,
    CarreraCatalogo,
    CursoCatalogo,
    CursoPensum,
    GradoPensum,
    NivelEducativo,
    TipoCarrera,
    VersionPensum,
)


@superusuario_required
def landing(request):
    return render(request, "catalogos/landing.html")
from .services import duplicar_version_pensum


REFERENCIAS = {
    "niveles": (NivelEducativo, NivelEducativoForm, "Niveles educativos"),
    "tipos-carrera": (TipoCarrera, TipoCarreraForm, "Tipos de carrera"),
    "areas": (AreaCurricular, AreaCurricularForm, "Áreas curriculares"),
    "cursos": (CursoCatalogo, CursoCatalogoForm, "Cursos"),
}


def _referencia(tipo):
    try:
        return REFERENCIAS[tipo]
    except KeyError as exc:
        raise PermissionDenied from exc


def _paginar(request, queryset):
    pagina = Paginator(queryset, 25).get_page(request.GET.get("page"))
    parametros = request.GET.copy()
    parametros.pop("page", None)
    return pagina, parametros.urlencode()


@superusuario_required
def referencia_lista(request, tipo):
    modelo, _, titulo = _referencia(tipo)
    consulta = request.GET.get("q", "").strip()
    objetos = modelo.objects.all()
    if consulta:
        campo_codigo = "codigo_interno" if modelo is CursoCatalogo else "codigo"
        objetos = objetos.filter(
            Q(nombre__icontains=consulta)
            | Q(**{f"{campo_codigo}__icontains": consulta})
        )
    estado = request.GET.get("estado", "")
    if estado in {"1", "0"}:
        objetos = objetos.filter(activo=estado == "1")
    area = request.GET.get("area", "")
    if modelo is CursoCatalogo and area:
        objetos = objetos.filter(area_curricular_id=area)
    pagina, querystring = _paginar(request, objetos)
    return render(
        request,
        "catalogos/referencia_lista.html",
        {
            "objetos": pagina,
            "pagina": pagina,
            "querystring": querystring,
            "titulo": titulo,
            "tipo": tipo,
            "q": consulta,
            "estado": estado,
            "areas": AreaCurricular.objects.filter(activo=True) if modelo is CursoCatalogo else None,
            "es_curso": modelo is CursoCatalogo,
        },
    )


@superusuario_required
def referencia_formulario(request, tipo, pk=None):
    modelo, formulario_clase, titulo = _referencia(tipo)
    objeto = get_object_or_404(modelo, pk=pk) if pk else None
    form = formulario_clase(request.POST or None, instance=objeto)
    if form.is_valid():
        guardado = form.save()
        registrar_evento(request, "ACTUALIZAR" if objeto else "CREAR", guardado)
        messages.success(request, f"{guardado} se guardó correctamente.")
        return redirect("catalogos:referencia_lista", tipo=tipo)
    return render(
        request,
        "catalogos/referencia_formulario.html",
        {"form": form, "titulo": titulo, "objeto": objeto, "tipo": tipo},
    )


@superusuario_required
def referencia_detalle(request, tipo, pk):
    modelo, _, titulo = _referencia(tipo)
    objeto = get_object_or_404(modelo, pk=pk)
    return render(request, "catalogos/referencia_detalle.html", {"objeto": objeto, "titulo": titulo, "tipo": tipo, "es_curso": modelo is CursoCatalogo})


@superusuario_required
def referencia_estado(request, tipo, pk):
    modelo, _, _ = _referencia(tipo)
    objeto = get_object_or_404(modelo, pk=pk)
    if request.method == "POST":
        objeto.activo = not objeto.activo
        objeto.save(update_fields=("activo",))
        registrar_evento(request, "ACTIVAR" if objeto.activo else "DESACTIVAR", objeto)
        messages.success(request, f"{objeto} {'activado' if objeto.activo else 'desactivado'} correctamente.")
    return redirect("catalogos:referencia_detalle", tipo=tipo, pk=pk)


@superusuario_required
def carrera_lista(request):
    carreras = CarreraCatalogo.objects.select_related("nivel", "tipo_carrera")
    q = request.GET.get("q", "").strip()
    nivel = request.GET.get("nivel", "")
    tipo = request.GET.get("tipo", "")
    activo = request.GET.get("activo", "")
    if q:
        carreras = carreras.filter(
            Q(nombre__icontains=q)
            | Q(codigo_interno__icontains=q)
            | Q(codigo_mineduc__icontains=q)
        )
    if nivel:
        carreras = carreras.filter(nivel_id=nivel)
    if tipo:
        carreras = carreras.filter(tipo_carrera_id=tipo)
    if activo in {"1", "0"}:
        carreras = carreras.filter(activa=activo == "1")
    pagina, querystring = _paginar(request, carreras)
    return render(
        request,
        "catalogos/carrera_lista.html",
        {
            "carreras": pagina,
            "pagina": pagina,
            "querystring": querystring,
            "niveles": NivelEducativo.objects.filter(activo=True),
            "tipos": TipoCarrera.objects.filter(activo=True),
            "filtros": {"q": q, "nivel": nivel, "tipo": tipo, "activo": activo},
        },
    )


@superusuario_required
def carrera_formulario(request, uuid=None):
    carrera = get_object_or_404(CarreraCatalogo, uuid=uuid) if uuid else None
    form = CarreraCatalogoForm(request.POST or None, instance=carrera)
    if form.is_valid():
        guardada = form.save()
        registrar_evento(request, "ACTUALIZAR" if carrera else "CREAR", guardada)
        messages.success(request, "La carrera se guardó correctamente.")
        return redirect("catalogos:carrera_detalle", uuid=guardada.uuid)
    return render(
        request,
        "catalogos/carrera_formulario.html",
        {"form": form, "carrera": carrera},
    )


@superusuario_required
def carrera_detalle(request, uuid):
    carrera = get_object_or_404(
        CarreraCatalogo.objects.select_related("nivel", "tipo_carrera"),
        uuid=uuid,
    )
    return render(
        request,
        "catalogos/carrera_detalle.html",
        {"carrera": carrera},
    )


@superusuario_required
def carrera_estado(request, uuid):
    carrera = get_object_or_404(CarreraCatalogo, uuid=uuid)
    if request.method == "POST":
        carrera.activa = not carrera.activa
        carrera.save(update_fields=("activa",))
        registrar_evento(request, "ACTIVAR" if carrera.activa else "DESACTIVAR", carrera)
        messages.success(request, f"Carrera {'activada' if carrera.activa else 'desactivada'} correctamente.")
    return redirect("catalogos:carrera_detalle", uuid=uuid)


@superusuario_required
def pensum_formulario(request, carrera_uuid, uuid=None):
    carrera = get_object_or_404(CarreraCatalogo, uuid=carrera_uuid)
    pensum = (
        get_object_or_404(VersionPensum, uuid=uuid, carrera=carrera) if uuid else None
    )
    form = VersionPensumForm(request.POST or None, instance=pensum)
    if form.is_valid():
        guardado = form.save(commit=False)
        guardado.carrera = carrera
        guardado.save()
        registrar_evento(request, "ACTUALIZAR" if pensum else "CREAR", guardado)
        messages.success(request, "La versión del pensum se guardó correctamente.")
        return redirect("catalogos:pensum_editor", uuid=guardado.uuid)
    return render(
        request,
        "catalogos/pensum_formulario.html",
        {"form": form, "carrera": carrera, "pensum": pensum},
    )


@superusuario_required
def pensum_editor(request, uuid):
    pensum = get_object_or_404(
        VersionPensum.objects.select_related("carrera").prefetch_related(
            "grados__cursos_pensum__curso"
        ),
        uuid=uuid,
    )
    return render(request, "catalogos/pensum_editor.html", {"pensum": pensum})


@superusuario_required
def grado_formulario(request, pensum_uuid, pk=None):
    pensum = get_object_or_404(VersionPensum, uuid=pensum_uuid)
    grado = get_object_or_404(GradoPensum, pk=pk, pensum=pensum) if pk else None
    form = GradoPensumForm(request.POST or None, instance=grado)
    if form.is_valid():
        guardado = form.save(commit=False)
        guardado.pensum = pensum
        guardado.save()
        registrar_evento(request, "ACTUALIZAR" if grado else "CREAR", guardado)
        messages.success(request, "El grado se guardó correctamente.")
        return redirect("catalogos:pensum_editor", uuid=pensum.uuid)
    return render(
        request,
        "catalogos/editor_formulario.html",
        {"form": form, "pensum": pensum, "titulo": "Grado", "objeto": grado},
    )


@superusuario_required
def grado_estado(request, pensum_uuid, pk):
    pensum = get_object_or_404(VersionPensum, uuid=pensum_uuid)
    grado = get_object_or_404(GradoPensum, pk=pk, pensum=pensum)
    if request.method == "POST":
        grado.activo = not grado.activo
        grado.save(update_fields=("activo",))
        registrar_evento(request, "ACTIVAR" if grado.activo else "DESACTIVAR", grado)
        messages.success(request, f"Grado {'activado' if grado.activo else 'desactivado'} correctamente.")
    return redirect("catalogos:pensum_editor", uuid=pensum.uuid)


@superusuario_required
def curso_pensum_formulario(request, pensum_uuid, pk=None):
    pensum = get_object_or_404(VersionPensum, uuid=pensum_uuid)
    item = get_object_or_404(CursoPensum, pk=pk, pensum=pensum) if pk else None
    form = CursoPensumForm(
        request.POST or None,
        instance=item,
        pensum=pensum,
    )
    if not request.method == "POST" and not item:
        grado_inicial = pensum.grados.filter(
            pk=request.GET.get("grado"),
            activo=True,
        ).first()
        if grado_inicial:
            form.initial["grado"] = grado_inicial
    if form.is_valid():
        guardado = form.save()
        registrar_evento(request, "ACTUALIZAR" if item else "CREAR", guardado)
        messages.success(request, "El curso se guardó en el pensum.")
        return redirect("catalogos:pensum_editor", uuid=pensum.uuid)
    return render(
        request,
        "catalogos/editor_formulario.html",
        {"form": form, "pensum": pensum, "titulo": "Curso del pensum", "objeto": item},
    )


@superusuario_required
def curso_pensum_quitar(request, pensum_uuid, pk):
    if request.method != "POST":
        raise PermissionDenied
    pensum = get_object_or_404(VersionPensum, uuid=pensum_uuid)
    item = get_object_or_404(CursoPensum, pk=pk, pensum=pensum)
    item.activo = False
    item.save(update_fields=("activo",))
    registrar_evento(request, "DESACTIVAR", item)
    messages.success(
        request, "El curso se quitó de la versión sin borrar su historial."
    )
    return redirect("catalogos:pensum_editor", uuid=pensum.uuid)


@superusuario_required
def pensum_duplicar(request, uuid):
    original = get_object_or_404(VersionPensum, uuid=uuid)
    form = DuplicarPensumForm(request.POST or None)
    if form.is_valid():
        nueva = duplicar_version_pensum(original, **form.cleaned_data)
        registrar_evento(request, "DUPLICAR", nueva)
        messages.success(request, "Se creó una copia en estado borrador.")
        return redirect("catalogos:pensum_editor", uuid=nueva.uuid)
    return render(
        request,
        "catalogos/duplicar_pensum.html",
        {"form": form, "original": original},
    )
