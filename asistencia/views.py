from io import BytesIO
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl import Workbook
from core.decorators import institucion_required
from alumnos.models import Alumno
from .forms import SesionForm
from .models import RegistroAsistencia, SesionAsistencia
from .services import ROLES_GESTION, anular_sesion, cerrar_sesion, crear_sesion, guardar_registros, justificar, puede_editar_sesion, reabrir_sesion, resumen_alumno, rol, sesiones_permitidas

def _permitir_lectura(request):
    if rol(request) == "CONTABILIDAD": raise PermissionDenied

def _sesion(request, pk):
    return get_object_or_404(sesiones_permitidas(request).select_related("ciclo", "oferta_academica", "grado", "seccion", "curso", "creada_por", "docente"), pk=pk)

@institucion_required
def dashboard(request):
    _permitir_lectura(request); hoy = timezone.localdate()
    qs = sesiones_permitidas(request)
    registros = RegistroAsistencia.objects.filter(institucion=request.institucion, sesion__in=qs, sesion__fecha=hoy).exclude(sesion__estado=SesionAsistencia.Estado.ANULADA)
    total = registros.exclude(estado=RegistroAsistencia.Estado.SIN_MARCAR).count(); asistieron = registros.filter(estado__in=("PRESENTE", "TARDE")).count()
    return render(request, "asistencia/dashboard.html", {"asistencia_hoy": round(asistieron*100/total,1) if total else None, "abiertas":qs.filter(estado="ABIERTA").count(), "cerradas_hoy":qs.filter(fecha=hoy,estado="CERRADA").count(), "ausencias":registros.filter(estado="AUSENTE").count(), "tardanzas":registros.filter(estado="TARDE").count()})

@institucion_required
def nueva(request):
    _permitir_lectura(request)
    form = SesionForm(request.POST or None, institucion=request.institucion, request=request)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            sesion, creada = crear_sesion(request=request, ciclo=d["ciclo"], oferta=d["oferta"], grado=d["grado"], seccion=d["seccion"], tipo=d["tipo"], fecha=d["fecha"], curso=d.get("curso"))
            messages.success(request, "Sesión creada con estudiantes sin marcar." if creada else "Ya existe una asistencia para esta sección y fecha. Continúa el registro.")
            return redirect("asistencia:tomar", sesion.pk)
        except ValidationError as exc: form.add_error(None, exc)
    return render(request, "asistencia/nueva.html", {"form":form})

@institucion_required
def sesiones(request):
    _permitir_lectura(request)
    qs = sesiones_permitidas(request).select_related("ciclo","grado","seccion","curso","creada_por").annotate(total=Count("registros"), registrados=Count("registros", filter=~Q(registros__estado="SIN_MARCAR")))
    for field in ("ciclo", "grado", "seccion", "curso"):
        if request.GET.get(field): qs = qs.filter(**{f"{field}_id":request.GET[field]})
    if request.GET.get("estado"): qs=qs.filter(estado=request.GET["estado"])
    if request.GET.get("desde"): qs=qs.filter(fecha__gte=request.GET["desde"])
    if request.GET.get("hasta"): qs=qs.filter(fecha__lte=request.GET["hasta"])
    return render(request,"asistencia/sesiones.html",{"sesiones":qs[:200],"estados":SesionAsistencia.Estado.choices})

@institucion_required
def detalle(request, pk):
    _permitir_lectura(request); sesion=_sesion(request,pk)
    registros=sesion.registros.select_related("alumno","inscripcion","justificada_por")
    resumen=registros.aggregate(presentes=Count("id",filter=Q(estado="PRESENTE")),ausentes=Count("id",filter=Q(estado="AUSENTE")),tardanzas=Count("id",filter=Q(estado="TARDE")),justificados=Count("id",filter=Q(estado="AUSENTE",justificada=True)))
    return render(request,"asistencia/detalle.html",{"sesion":sesion,"registros":registros,"resumen":resumen,"puede_gestionar":rol(request) in ROLES_GESTION})

@institucion_required
def tomar(request, pk):
    _permitir_lectura(request); sesion=_sesion(request,pk)
    if not puede_editar_sesion(request, sesion): raise PermissionDenied
    if request.method == "POST":
        try:
            guardar_registros(sesion, {k[7:]:v for k,v in request.POST.items() if k.startswith("estado_")}, request.user, request)
            if request.POST.get("accion") == "cerrar": cerrar_sesion(sesion,request.user,request)
            messages.success(request,"Asistencia cerrada." if request.POST.get("accion")=="cerrar" else "Borrador guardado.")
            return redirect("asistencia:detalle",sesion.pk) if request.POST.get("accion")=="cerrar" else redirect("asistencia:tomar",sesion.pk)
        except ValidationError as exc: messages.error(request," ".join(exc.messages))
    registros=sesion.registros.select_related("alumno"); total=registros.count(); pendientes=registros.filter(estado="SIN_MARCAR").count()
    return render(request,"asistencia/tomar.html",{"sesion":sesion,"registros":registros,"total":total,"pendientes":pendientes,"registrados":total-pendientes,"porcentaje":round((total-pendientes)*100/total) if total else 0,"editable":sesion.estado in ("ABIERTA","BORRADOR")})

@institucion_required
def reabrir(request, pk):
    if rol(request) not in ROLES_GESTION: raise PermissionDenied
    sesion=_sesion(request,pk)
    if request.method == "POST":
        try: reabrir_sesion(sesion,request.user,request.POST.get("motivo",""),request); messages.success(request,"Asistencia reabierta.")
        except ValidationError as exc: messages.error(request," ".join(exc.messages))
    return redirect("asistencia:detalle",pk)

@institucion_required
def anular(request, pk):
    if rol(request) not in ROLES_GESTION: raise PermissionDenied
    sesion=_sesion(request,pk)
    if request.method == "POST":
        try: anular_sesion(sesion,request.user,request.POST.get("motivo",""),request); messages.success(request,"Asistencia anulada sin eliminar su historial.")
        except ValidationError as exc: messages.error(request," ".join(exc.messages))
    return redirect("asistencia:detalle",pk)

@institucion_required
def justificaciones(request):
    if rol(request) not in ROLES_GESTION|{"SECRETARIA"}: raise PermissionDenied
    qs=RegistroAsistencia.objects.filter(institucion=request.institucion,estado="AUSENTE").select_related("alumno","sesion__grado","sesion__seccion")
    if request.GET.get("q"): qs=qs.filter(Q(alumno__primer_nombre__icontains=request.GET["q"])|Q(alumno__primer_apellido__icontains=request.GET["q"])|Q(alumno__cui__icontains=request.GET["q"]))
    if request.GET.get("justificada") in ("si","no"): qs=qs.filter(justificada=request.GET["justificada"]=="si")
    return render(request,"asistencia/justificaciones.html",{"registros":qs[:200]})

@institucion_required
def justificar_view(request, pk):
    if rol(request) not in ROLES_GESTION|{"SECRETARIA"}: raise PermissionDenied
    registro=get_object_or_404(RegistroAsistencia,institucion=request.institucion,pk=pk,estado="AUSENTE")
    if request.method=="POST":
        try: justificar(registro,request.user,request.POST.get("motivo",""),request); messages.success(request,"Ausencia justificada.")
        except ValidationError as exc: messages.error(request," ".join(exc.messages))
    return redirect("asistencia:justificaciones")

@institucion_required
def reportes(request):
    _permitir_lectura(request); fecha=request.GET.get("fecha") or str(timezone.localdate())
    qs=sesiones_permitidas(request).filter(fecha=fecha,tipo="GENERAL",estado="CERRADA").select_related("grado","seccion").annotate(inscritos=Count("registros"),presentes=Count("registros",filter=Q(registros__estado="PRESENTE")),ausentes=Count("registros",filter=Q(registros__estado="AUSENTE")),tardanzas=Count("registros",filter=Q(registros__estado="TARDE")))
    return render(request,"asistencia/reportes.html",{"filas":qs,"fecha":fecha})

def _excel(nombre, encabezados, filas):
    wb=Workbook(); ws=wb.active; ws.title=nombre[:31]; ws.append(encabezados)
    for fila in filas: ws.append(fila)
    out=BytesIO(); wb.save(out); response=HttpResponse(out.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"); response["Content-Disposition"]=f'attachment; filename="{nombre}.xlsx"'; return response

@institucion_required
def exportar_sesiones(request):
    _permitir_lectura(request); qs=sesiones_permitidas(request).select_related("grado","seccion","curso","creada_por")
    return _excel("sesiones-asistencia",["Fecha","Tipo","Grado","Sección","Curso","Estado","Creada por"],((s.fecha,s.get_tipo_display(),s.grado.nombre,s.seccion.nombre,s.curso.nombre if s.curso else "General",s.get_estado_display(),s.creada_por.username if s.creada_por else "") for s in qs))

@institucion_required
def alumno_historial(request, pk):
    _permitir_lectura(request); alumno=get_object_or_404(Alumno,institucion=request.institucion,pk=pk); ciclo=alumno.inscripciones.order_by("-ciclo__anio").first(); ciclo=ciclo.ciclo if ciclo else None
    registros=RegistroAsistencia.objects.filter(institucion=request.institucion,alumno=alumno,sesion__estado="CERRADA").select_related("sesion__curso").order_by("-sesion__fecha")
    return render(request,"asistencia/alumno_historial.html",{"alumno":alumno,"ciclo":ciclo,"resumen":resumen_alumno(alumno,ciclo),"registros":registros})

@institucion_required
def exportar_alumno(request, pk):
    alumno=get_object_or_404(Alumno,institucion=request.institucion,pk=pk); qs=RegistroAsistencia.objects.filter(institucion=request.institucion,alumno=alumno).select_related("sesion__curso")
    return _excel("asistencia-alumno",["Fecha","Tipo","Curso","Estado","Justificada","Observación"],((r.sesion.fecha,r.sesion.get_tipo_display(),r.sesion.curso.nombre if r.sesion.curso else "",r.get_estado_display(),"Sí" if r.justificada else "No",r.observacion) for r in qs))
