from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse

from auditoria.services import registrar_evento
from core.decorators import administrador_institucion_required, institucion_required

from .forms import CicloEscolarForm, CursoInstitucionForm, JornadaForm, OfertaPensumForm, SeccionForm
from .models import CicloEscolar, CursoInstitucion, GradoInstitucion, JornadaInstitucion, OfertaAcademica, ResultadoAnualAlumno, Seccion
from .services import (cerrar_ciclo, confirmar_resultado, crear_ciclo_siguiente, crear_oferta_desde_pensum,
                       establecer_ciclo_actual, generar_resultado_anual, validar_cierre)

CIERRE_ROLES = {"PROPIETARIO", "DIRECTOR"}
RESULTADOS_ROLES = CIERRE_ROLES | {"ADMINISTRADOR"}

def _exigir_rol(request, permitidos):
    if request.asignacion_institucion.rol not in permitidos:
        raise PermissionDenied


def _ciclos(request):
    return CicloEscolar.objects.filter(institucion=request.institucion)


def _ciclo_seleccionado(request, requerido=False):
    ciclos = _ciclos(request)
    ciclo_solicitado = request.GET.get("ciclo") or request.POST.get("ciclo")
    ciclo_id = ciclo_solicitado or request.session.get("ciclo_escolar_id")
    if ciclo_solicitado:
        ciclo = get_object_or_404(ciclos, pk=ciclo_solicitado)
    else:
        ciclo = ciclos.filter(pk=ciclo_id).first() if ciclo_id else ciclos.filter(es_actual=True).first()
    if ciclo is None:
        ciclo = ciclos.filter(activo=True).first()
    if ciclo:
        request.session["ciclo_escolar_id"] = ciclo.pk
    if requerido and ciclo is None:
        raise PermissionDenied("Configure primero un ciclo escolar.")
    return ciclo, ciclos


def _verificar_abierto(ciclo):
    if ciclo.cerrado:
        raise PermissionDenied("El ciclo está cerrado y no admite cambios académicos.")


@institucion_required
def landing(request):
    ciclo, ciclos = _ciclo_seleccionado(request)
    contexto = {"ciclo": ciclo, "ciclos": ciclos}
    if ciclo:
        contexto.update(ofertas=ciclo.ofertas.filter(institucion=request.institucion).count(), grados=ciclo.grados.filter(institucion=request.institucion).count(), cursos=ciclo.cursos.filter(institucion=request.institucion).count())
    return render(request, "academico/landing.html", contexto)


@institucion_required
def ciclos_lista(request):
    return render(request, "academico/ciclos_lista.html", {"ciclos": _ciclos(request)})


@institucion_required
def ciclo_detalle(request, pk):
    from alumnos.models import Inscripcion
    from auditoria.models import EventoAuditoria

    ciclo = get_object_or_404(_ciclos(request), pk=pk)
    ofertas = ciclo.ofertas.filter(institucion=request.institucion).select_related("nivel")
    return render(request, "academico/ciclo_detalle.html", {
        "ciclo": ciclo,
        "ofertas": ofertas,
        "total_grados": ciclo.grados.filter(institucion=request.institucion).count(),
        "total_secciones": Seccion.objects.filter(institucion=request.institucion, ciclo=ciclo).count(),
        "total_inscripciones": Inscripcion.objects.filter(institucion=request.institucion, ciclo=ciclo).count(),
        "total_periodos": ciclo.periodos_academicos.count(),
        "total_resultados": ciclo.resultados_anuales.count(),
        "resultados_confirmados": ciclo.resultados_anuales.filter(resultado_final__isnull=False).count(),
        "actividad": EventoAuditoria.objects.filter(institucion=request.institucion, modelo=ciclo._meta.label, objeto_id=str(ciclo.pk))[:10],
    })


@institucion_required
def ciclo_cierre(request, pk):
    ciclo = get_object_or_404(_ciclos(request), pk=pk)
    _exigir_rol(request, RESULTADOS_ROLES)
    return render(request, "academico/cierre_wizard.html", {
        "ciclo": ciclo, "validacion": validar_cierre(ciclo),
        "activas": ciclo.inscripciones.filter(estado="ACTIVA").count(),
        "generados": ciclo.resultados_anuales.count(),
        "confirmados": ciclo.resultados_anuales.filter(resultado_final__isnull=False).count(),
    })


@institucion_required
@require_POST
def ciclo_iniciar_cierre(request, pk):
    ciclo = get_object_or_404(_ciclos(request), pk=pk)
    _exigir_rol(request, CIERRE_ROLES)
    if ciclo.cerrado:
        raise ValidationError("El ciclo ya está cerrado.")
    ciclo.estado = CicloEscolar.Estado.EN_CIERRE
    ciclo.save(update_fields=("estado", "fecha_actualizacion"))
    registrar_evento(request, "INICIAR_CIERRE_CICLO", ciclo)
    messages.success(request, "Cierre académico iniciado.")
    return redirect("academico:ciclo_cierre", pk=ciclo.pk)


def _resultados_filtrados(request, ciclo):
    qs = ciclo.resultados_anuales.select_related("alumno", "inscripcion__oferta_academica", "inscripcion__grado", "inscripcion__seccion", "confirmado_por")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(alumno__cui__icontains=q) | Q(alumno__primer_nombre__icontains=q) | Q(alumno__primer_apellido__icontains=q))
    for key, lookup in (("oferta", "inscripcion__oferta_academica_id"), ("grado", "inscripcion__grado_id"), ("seccion", "inscripcion__seccion_id"), ("sugerido", "resultado_sugerido"), ("final", "resultado_final")):
        if request.GET.get(key): qs = qs.filter(**{lookup: request.GET[key]})
    if request.GET.get("pendientes") == "1": qs = qs.filter(Q(resultado_final__isnull=True) | Q(resultado_sugerido="PENDIENTE"))
    return qs


@institucion_required
def resultados_anuales(request, pk):
    ciclo = get_object_or_404(_ciclos(request), pk=pk)
    _exigir_rol(request, RESULTADOS_ROLES | {"DOCENTE"})
    qs = _resultados_filtrados(request, ciclo)
    conteos = {valor: ciclo.resultados_anuales.filter(resultado_final=valor).count() for valor, _ in ResultadoAnualAlumno.Resultado.choices}
    return render(request, "academico/resultados_anuales.html", {"ciclo": ciclo, "resultados": qs, "conteos": conteos,
        "ofertas": ciclo.ofertas.all(), "grados": ciclo.grados.all(), "secciones": ciclo.secciones.all(), "opciones": ResultadoAnualAlumno.Resultado.choices,
        "puede_editar": request.asignacion_institucion.rol in RESULTADOS_ROLES})


@institucion_required
@require_POST
def resultados_generar(request, pk):
    ciclo = get_object_or_404(_ciclos(request), pk=pk, cerrado=False)
    _exigir_rol(request, RESULTADOS_ROLES)
    total = 0
    with transaction.atomic():
        for inscripcion in ciclo.inscripciones.filter(estado__in=("ACTIVA", "RETIRADA", "TRASLADADA")):
            generar_resultado_anual(inscripcion); total += 1
    registrar_evento(request, "GENERAR_RESULTADOS_ANUALES", ciclo, {"alumnos": total})
    messages.success(request, f"Se generaron o actualizaron {total} resultados.")
    return redirect("academico:resultados_anuales", pk=ciclo.pk)


@institucion_required
@require_POST
def resultado_confirmar(request, pk):
    resultado = get_object_or_404(ResultadoAnualAlumno, pk=pk, institucion=request.institucion)
    _exigir_rol(request, RESULTADOS_ROLES)
    try:
        confirmar_resultado(resultado, request.POST.get("resultado_final"), request.user, request.POST.get("observaciones", ""))
    except ValidationError as exc: messages.error(request, "; ".join(exc.messages))
    else:
        registrar_evento(request, "CONFIRMAR_RESULTADO_ALUMNO", resultado)
        messages.success(request, "Resultado confirmado.")
    return redirect("academico:resultados_anuales", pk=resultado.ciclo_id)


@institucion_required
@require_POST
def resultados_confirmar_sugerencias(request, pk):
    ciclo = get_object_or_404(_ciclos(request), pk=pk)
    _exigir_rol(request, RESULTADOS_ROLES)
    candidatos = ciclo.resultados_anuales.filter(resultado_final__isnull=True).exclude(resultado_sugerido="PENDIENTE")
    with transaction.atomic():
        for resultado in candidatos: confirmar_resultado(resultado, resultado.resultado_sugerido, request.user)
    registrar_evento(request, "CONFIRMAR_RESULTADOS_MASIVO", ciclo, {"alumnos": candidatos.count()})
    messages.success(request, "Sugerencias válidas confirmadas.")
    return redirect("academico:resultados_anuales", pk=ciclo.pk)


@institucion_required
@require_POST
def ciclo_cerrar(request, pk):
    ciclo = get_object_or_404(_ciclos(request), pk=pk)
    _exigir_rol(request, CIERRE_ROLES)
    if request.POST.get("confirmacion", "").strip() != f"CERRAR {ciclo.anio}":
        messages.error(request, f"Escriba CERRAR {ciclo.anio} para confirmar.")
        return redirect("academico:ciclo_cierre", pk=pk)
    try: cerrar_ciclo(ciclo)
    except ValidationError as exc: messages.error(request, "; ".join(exc.messages)); return redirect("academico:ciclo_cierre", pk=pk)
    registrar_evento(request, "CERRAR_CICLO", ciclo)
    messages.success(request, f"Ciclo {ciclo.anio} cerrado correctamente.")
    return redirect("academico:ciclo_detalle", pk=pk)


@institucion_required
def ciclo_crear_siguiente(request, pk):
    ciclo = get_object_or_404(_ciclos(request), pk=pk)
    _exigir_rol(request, CIERRE_ROLES)
    existente = _ciclos(request).filter(anio=ciclo.anio + 1).first()
    if request.method == "POST" and not existente:
        try: existente = crear_ciclo_siguiente(ciclo, anio=ciclo.anio + 1)
        except ValidationError as exc: messages.error(request, "; ".join(exc.messages))
        else:
            registrar_evento(request, "CREAR_CICLO_SIGUIENTE", existente, {"ciclo_origen": ciclo.anio, "ciclo_destino": existente.anio})
            messages.success(request, f"Ciclo {existente.anio} preparado.")
            return redirect("academico:ciclo_detalle", pk=existente.pk)
    return render(request, "academico/crear_ciclo_siguiente.html", {"ciclo": ciclo, "existente": existente,
        "preview": {"jornadas": request.institucion.jornadas.count(), "ofertas": ciclo.ofertas.count(), "grados": ciclo.grados.count(), "secciones": ciclo.secciones.count(), "cursos": ciclo.cursos.count()}})


@administrador_institucion_required
def ciclo_formulario(request, pk=None):
    ciclo = get_object_or_404(_ciclos(request), pk=pk) if pk else None
    era_actual = ciclo.es_actual if ciclo else False
    if ciclo:
        _verificar_abierto(ciclo)
    form = CicloEscolarForm(request.POST or None, instance=ciclo)
    form.instance.institucion = request.institucion
    if request.method == "POST" and form.is_valid():
        guardado = form.save(commit=False); guardado.institucion = request.institucion; guardado.save()
        registrar_evento(request, "EDITAR_CICLO" if ciclo else "CREAR_CICLO", guardado)
        if guardado.es_actual and not era_actual:
            registrar_evento(request, "CAMBIAR_CICLO_ACTUAL", guardado)
        messages.success(request, "Ciclo escolar guardado correctamente.")
        return redirect("academico:ciclos")
    return render(request, "academico/formulario.html", {"form": form, "titulo": "Editar ciclo escolar" if ciclo else "Nuevo ciclo escolar", "volver": "academico:ciclos"})


@administrador_institucion_required
@require_POST
def ciclo_actual(request, pk):
    ciclo = get_object_or_404(_ciclos(request), pk=pk, activo=True)
    if request.method == "POST":
        establecer_ciclo_actual(ciclo); registrar_evento(request, "CAMBIAR_CICLO_ACTUAL", ciclo)
        request.session["ciclo_escolar_id"] = ciclo.pk
        messages.success(request, f"{ciclo.nombre} es ahora el ciclo actual.")
    return redirect("academico:ciclos")


@institucion_required
def jornadas_lista(request):
    return render(request, "academico/jornadas_lista.html", {"jornadas": request.institucion.jornadas.all()})


@institucion_required
def jornada_detalle(request, pk):
    jornada = get_object_or_404(request.institucion.jornadas, pk=pk)
    secciones = jornada.secciones.filter(institucion=request.institucion).select_related("grado", "ciclo")
    return render(request, "academico/jornada_detalle.html", {"jornada": jornada, "secciones": secciones})


@administrador_institucion_required
def jornada_formulario(request, pk=None):
    jornada = get_object_or_404(request.institucion.jornadas, pk=pk) if pk else None
    form = JornadaForm(request.POST or None, instance=jornada)
    form.instance.institucion = request.institucion
    if request.method == "POST" and form.is_valid():
        guardada = form.save(commit=False); guardada.institucion = request.institucion; guardada.save()
        registrar_evento(request, "EDITAR_JORNADA" if jornada else "CREAR_JORNADA", guardada)
        messages.success(request, "Jornada guardada correctamente.")
        return redirect("academico:jornadas")
    return render(request, "academico/formulario.html", {"form": form, "titulo": "Editar jornada" if jornada else "Nueva jornada", "volver": "academico:jornadas"})


@administrador_institucion_required
@require_POST
def jornada_estado(request, pk):
    jornada = get_object_or_404(request.institucion.jornadas, pk=pk)
    if request.method == "POST":
        jornada.activa = not jornada.activa; jornada.save(update_fields=("activa",)); registrar_evento(request, "EDITAR_JORNADA", jornada)
        messages.success(request, "Estado de jornada actualizado.")
    return redirect("academico:jornadas")


@institucion_required
def ofertas_lista(request):
    ciclo, ciclos = _ciclo_seleccionado(request)
    ofertas = OfertaAcademica.objects.filter(institucion=request.institucion, ciclo=ciclo).select_related("nivel", "carrera_catalogo", "version_pensum") if ciclo else OfertaAcademica.objects.none()
    return render(request, "academico/ofertas_lista.html", {"ciclo": ciclo, "ciclos": ciclos, "ofertas": ofertas})


@administrador_institucion_required
def oferta_agregar(request):
    ciclo, ciclos = _ciclo_seleccionado(request, requerido=True); _verificar_abierto(ciclo)
    form = OfertaPensumForm(request.POST or None)
    vista_previa = request.method == "POST" and form.is_valid() and request.POST.get("accion") == "previsualizar"
    if request.method == "POST" and form.is_valid() and request.POST.get("accion") == "confirmar":
        try:
            oferta = crear_oferta_desde_pensum(institucion=request.institucion, ciclo=ciclo, nivel=form.cleaned_data["nivel"], carrera=form.cleaned_data["carrera"], pensum=form.cleaned_data["pensum"], nombre_mostrado=form.cleaned_data["nombre_mostrado"] or None, codigo_interno=form.cleaned_data["codigo_interno"] or None)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            registrar_evento(request, "AGREGAR_OFERTA", oferta); messages.success(request, "Oferta académica configurada correctamente.")
            return redirect("academico:oferta_detalle", pk=oferta.pk)
    contexto = {"form": form, "ciclo": ciclo, "ciclos": ciclos, "vista_previa": vista_previa}
    if vista_previa:
        pensum = form.cleaned_data["pensum"]
        contexto.update(total_grados=pensum.grados.filter(activo=True).count(), total_cursos=pensum.cursos_pensum.filter(activo=True).count(), pensum=pensum, carrera=form.cleaned_data["carrera"])
    return render(request, "academico/oferta_formulario.html", contexto)


@institucion_required
def opciones_catalogo(request):
    from catalogos.models import CarreraCatalogo, VersionPensum
    if request.GET.get("nivel"):
        carreras = CarreraCatalogo.objects.filter(activa=True, nivel_id=request.GET["nivel"]).values("id", "nombre")
        return JsonResponse({"resultados": list(carreras)})
    if request.GET.get("carrera"):
        versiones = VersionPensum.objects.filter(carrera_id=request.GET["carrera"]).order_by("-fecha_inicio_vigencia").values("id", "nombre", "codigo_version", "estado")
        return JsonResponse({"resultados": list(versiones)})
    return JsonResponse({"resultados": []})


@institucion_required
def oferta_detalle(request, pk):
    oferta = get_object_or_404(OfertaAcademica.objects.select_related("nivel", "carrera_catalogo", "version_pensum", "ciclo").prefetch_related("grados__cursos__curso_catalogo"), pk=pk, institucion=request.institucion)
    return render(request, "academico/oferta_detalle.html", {"oferta": oferta})


@administrador_institucion_required
@require_POST
def oferta_estado(request, pk):
    oferta = get_object_or_404(OfertaAcademica, pk=pk, institucion=request.institucion); _verificar_abierto(oferta.ciclo)
    if request.method == "POST":
        oferta.activa = not oferta.activa; oferta.save(update_fields=("activa",)); registrar_evento(request, "ACTIVAR_OFERTA" if oferta.activa else "DESACTIVAR_OFERTA", oferta)
        messages.success(request, "Estado de oferta actualizado.")
    return redirect("academico:oferta_detalle", pk=pk)


@institucion_required
def grados_secciones(request):
    ciclo, ciclos = _ciclo_seleccionado(request)
    grados = GradoInstitucion.objects.filter(institucion=request.institucion, ciclo=ciclo).select_related("oferta").prefetch_related("secciones__jornada") if ciclo else GradoInstitucion.objects.none()
    return render(request, "academico/grados_secciones.html", {"ciclo": ciclo, "ciclos": ciclos, "grados": grados})


@institucion_required
def grado_detalle(request, pk):
    grado = get_object_or_404(GradoInstitucion.objects.select_related("ciclo", "oferta"), pk=pk, institucion=request.institucion)
    return render(request, "academico/grado_detalle.html", {
        "grado": grado,
        "secciones": grado.secciones.filter(institucion=request.institucion).select_related("jornada"),
        "cursos": grado.cursos.filter(institucion=request.institucion).select_related("curso_catalogo"),
    })


@institucion_required
def seccion_detalle(request, pk):
    from alumnos.models import Inscripcion
    from docentes.models import AsignacionGuia

    seccion = get_object_or_404(Seccion.objects.select_related("ciclo", "grado__oferta", "jornada"), pk=pk, institucion=request.institucion)
    asignaciones = seccion.asignaciones_docentes.filter(institucion=request.institucion, activa=True).select_related("curso", "docente")
    return render(request, "academico/seccion_detalle.html", {
        "seccion": seccion,
        "guia": AsignacionGuia.objects.filter(institucion=request.institucion, seccion=seccion, activa=True).select_related("docente").first(),
        "asignaciones": asignaciones,
        "estudiantes": Inscripcion.objects.filter(institucion=request.institucion, seccion=seccion, estado="ACTIVA").select_related("alumno"),
    })


@administrador_institucion_required
def seccion_formulario(request, grado_pk=None, pk=None):
    ciclo, ciclos = _ciclo_seleccionado(request, requerido=True); _verificar_abierto(ciclo)
    seccion = get_object_or_404(Seccion, pk=pk, institucion=request.institucion, ciclo=ciclo) if pk else None
    grado = get_object_or_404(GradoInstitucion, pk=grado_pk, institucion=request.institucion, ciclo=ciclo) if grado_pk else seccion.grado
    form = SeccionForm(request.POST or None, instance=seccion, institucion=request.institucion, ciclo=ciclo)
    form.instance.institucion = request.institucion
    form.instance.ciclo = ciclo
    if not seccion: form.initial["grado"] = grado
    if request.method == "POST" and form.is_valid():
        guardada = form.save(commit=False); guardada.institucion=request.institucion; guardada.ciclo=ciclo; guardada.save()
        registrar_evento(request, "EDITAR_SECCION" if seccion else "CREAR_SECCION", guardada); messages.success(request, "Sección guardada correctamente.")
        return redirect(f"{redirect('academico:grados_secciones').url}?ciclo={ciclo.pk}")
    return render(request, "academico/formulario.html", {"form": form, "titulo": "Editar sección" if seccion else "Nueva sección", "volver": "academico:grados_secciones", "ciclo": ciclo})


@administrador_institucion_required
@require_POST
def seccion_estado(request, pk):
    seccion = get_object_or_404(Seccion, pk=pk, institucion=request.institucion); _verificar_abierto(seccion.ciclo)
    if request.method == "POST":
        seccion.activa = not seccion.activa; seccion.save(update_fields=("activa",)); registrar_evento(request, "EDITAR_SECCION", seccion)
    return redirect("academico:grados_secciones")


@institucion_required
def cursos_lista(request):
    ciclo, ciclos = _ciclo_seleccionado(request)
    cursos = CursoInstitucion.objects.filter(institucion=request.institucion, ciclo=ciclo).select_related("oferta", "grado", "curso_catalogo") if ciclo else CursoInstitucion.objects.none()
    if request.GET.get("oferta"): cursos = cursos.filter(oferta_id=request.GET["oferta"])
    if request.GET.get("grado"): cursos = cursos.filter(grado_id=request.GET["grado"])
    if request.GET.get("origen"): cursos = cursos.filter(origen=request.GET["origen"])
    if request.GET.get("estado") in {"1", "0"}: cursos = cursos.filter(activo=request.GET["estado"] == "1")
    return render(request, "academico/cursos_lista.html", {"ciclo": ciclo, "ciclos": ciclos, "cursos": cursos, "ofertas": ciclo.ofertas.filter(institucion=request.institucion) if ciclo else [], "grados": ciclo.grados.filter(institucion=request.institucion) if ciclo else [], "origenes": CursoInstitucion.Origen.choices})


@institucion_required
def curso_detalle(request, pk):
    curso = get_object_or_404(CursoInstitucion.objects.select_related("ciclo", "oferta", "grado", "curso_catalogo"), pk=pk, institucion=request.institucion)
    asignaciones = curso.asignaciones_docentes.filter(institucion=request.institucion).select_related("docente", "seccion")
    return render(request, "academico/curso_detalle.html", {"curso": curso, "asignaciones": asignaciones})


@administrador_institucion_required
def curso_formulario(request, grado_pk, pk=None):
    grado = get_object_or_404(GradoInstitucion.objects.select_related("ciclo", "oferta"), pk=grado_pk, institucion=request.institucion); _verificar_abierto(grado.ciclo)
    curso = get_object_or_404(CursoInstitucion, pk=pk, institucion=request.institucion, grado=grado) if pk else None
    form = CursoInstitucionForm(request.POST or None, instance=curso)
    form.instance.institucion = request.institucion
    form.instance.ciclo = grado.ciclo
    form.instance.oferta = grado.oferta
    form.instance.grado = grado
    if request.method == "POST" and form.is_valid():
        guardado=form.save(commit=False); guardado.institucion=request.institucion; guardado.ciclo=grado.ciclo; guardado.oferta=grado.oferta; guardado.grado=grado; guardado.save()
        registrar_evento(request, "EDITAR_CURSO_INSTITUCIONAL" if curso else "AGREGAR_CURSO_INSTITUCIONAL", guardado); messages.success(request, "Curso institucional guardado correctamente.")
        return redirect("academico:oferta_detalle", pk=grado.oferta_id)
    return render(request, "academico/formulario.html", {"form": form, "titulo": "Editar curso" if curso else "Agregar curso institucional", "volver": "academico:oferta_detalle", "volver_pk": grado.oferta_id})


@administrador_institucion_required
@require_POST
def curso_estado(request, pk):
    curso = get_object_or_404(CursoInstitucion.objects.select_related("ciclo"), pk=pk, institucion=request.institucion); _verificar_abierto(curso.ciclo)
    if request.method == "POST":
        curso.activo = not curso.activo; curso.save(update_fields=("activo",)); registrar_evento(request, "EDITAR_CURSO_INSTITUCIONAL", curso)
        messages.warning(request, "Curso oficial desactivado; el pensum global permanece intacto." if curso.curso_pensum_origen_id and not curso.activo else "Estado del curso actualizado.")
    return redirect("academico:oferta_detalle", pk=curso.oferta_id)
