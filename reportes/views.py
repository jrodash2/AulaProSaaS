from django.core.paginator import Paginator
from django.shortcuts import render,redirect
from django.utils import timezone
from .permissions import reporte_required,es_docente,puede_finanzas,rol
from .services.base import ciclo_actual,filtros_context
from .services.dashboard import datos as dashboard_datos,asignaciones_docente
from .services import alumnos as salumnos,academico as sacademico,asistencia as sasistencia,calificaciones as scalificaciones,docentes as sdocentes,tareas as stareas,finanzas as sfinanzas,comunicaciones as scomunicaciones
from .exporters import excel_response

def _base(request):
 ciclo=ciclo_actual(request.institucion,request.GET.get("ciclo"));ctx=filtros_context(request.institucion,ciclo);ctx.update({"generado":timezone.now(),"querystring":request.GET.urlencode()});return ciclo,ctx
def _asigs(request,ciclo):return asignaciones_docente(request,ciclo) if es_docente(request) else None
def _page(request,items):return Paginator(items,25).get_page(request.GET.get("page"))
@reporte_required("dashboard")
def dashboard(request):
 if rol(request)=="CONTABILIDAD":return redirect("reportes:finanzas")
 ciclo,ctx=_base(request);asigs=_asigs(request,ciclo);ctx["metricas"]=dashboard_datos(request.institucion,ciclo,request.GET,puede_finanzas(request),asigs);ctx["docente"]=es_docente(request)
 if es_docente(request):ctx["asignaciones"]=asigs.select_related("curso","grado","seccion")
 else:
  ctx["distribucion"]=list(request.institucion.inscripciones.filter(ciclo=ciclo,estado="ACTIVA").values("seccion__grado__nombre","seccion__nombre").annotate(total=__import__("django.db.models",fromlist=["Count"]).Count("id"))) if ciclo else []
 return render(request,"reportes/dashboard.html",ctx)
@reporte_required("alumnos")
def alumnos(request):
 ciclo,ctx=_base(request);qs=salumnos.queryset(request.institucion,ciclo,request.GET);ctx.update(salumnos.estadisticas(request.institucion,qs));ctx["filas"]=_page(request,salumnos.filas(qs,ciclo));ctx["inscripciones"]=_page(request,salumnos.inscripciones(request.institucion,ciclo,request.GET));return render(request,"reportes/alumnos.html",ctx)
@reporte_required("academico")
def academico(request):
 ciclo,ctx=_base(request);ctx.update(sacademico.datos(request.institucion,ciclo) if ciclo else {});return render(request,"reportes/academico.html",ctx)
@reporte_required("asistencia")
def asistencia(request):
 ciclo,ctx=_base(request);qs=sasistencia.registros(request.institucion,ciclo,request.GET,_asigs(request,ciclo));umbral=int(request.GET.get("umbral","80")) if request.GET.get("umbral","80").isdigit() else 80;umbral=max(0,min(100,umbral));ctx.update(sasistencia.resumen(qs));ctx["filas"]=_page(request,sasistencia.por_alumno(qs,umbral));ctx["umbral"]=umbral;return render(request,"reportes/asistencia.html",ctx)
@reporte_required("calificaciones")
def calificaciones(request):
 ciclo,ctx=_base(request);rows=scalificaciones.filas(scalificaciones.queryset(request.institucion,ciclo,request.GET,_asigs(request,ciclo)),request.institucion);ctx.update(scalificaciones.resumen(rows));ctx["filas"]=_page(request,rows);return render(request,"reportes/calificaciones.html",ctx)
@reporte_required("docentes")
def docentes(request):
 ciclo,ctx=_base(request);ctx.update(sdocentes.datos(request.institucion,ciclo) if ciclo else {});return render(request,"reportes/docentes.html",ctx)
@reporte_required("tareas")
def tareas(request):
 ciclo,ctx=_base(request);ctx.update(stareas.datos(request.institucion,ciclo,request.GET,_asigs(request,ciclo)));ctx["tareas"]=_page(request,ctx["tareas"]);return render(request,"reportes/tareas.html",ctx)
@reporte_required("finanzas")
def finanzas(request):
 ciclo,ctx=_base(request);ctx.update(sfinanzas.datos(request.institucion,request.GET));ctx["cargos"]=_page(request,ctx["cargos"]);return render(request,"reportes/finanzas.html",ctx)
@reporte_required("comunicacion")
def comunicacion(request):
 ciclo,ctx=_base(request);ctx["comunicaciones"]=_page(request,scomunicaciones.datos(request.institucion));return render(request,"reportes/comunicacion.html",ctx)
@reporte_required("alumnos")
def exportar_alumnos(request):
 ciclo,_=_base(request);qs=salumnos.queryset(request.institucion,ciclo,request.GET);rows=salumnos.filas(qs,ciclo);data=[(r["alumno"].codigo_interno,r["alumno"].nombre_completo,r["alumno"].cui or "",str(r["inscripcion"].grado) if r["inscripcion"] else "",str(r["inscripcion"].seccion) if r["inscripcion"] else "",r["alumno"].get_estado_display(),r["encargado"].nombre_completo if r["encargado"] else "",r["encargado"].telefono if r["encargado"] else "") for r in rows]
 return excel_response(institucion=request.institucion,titulo="Reporte de alumnos",encabezados=("Código","Alumno","CUI","Grado","Sección","Estado alumno","Encargado","Teléfono"),filas=data,nombre=f"aulapro_alumnos_{ciclo.anio if ciclo else 'todos'}.xlsx",ciclo=ciclo,filtros=request.GET.urlencode())
@reporte_required("asistencia")
def exportar_asistencia(request):
 ciclo,_=_base(request);rows=sasistencia.por_alumno(sasistencia.registros(request.institucion,ciclo,request.GET,_asigs(request,ciclo)));data=[(f'{r["alumno__primer_nombre"]} {r["alumno__primer_apellido"]}',r["presentes"],r["ausentes"],r["tardes"],r["justificadas"],r["porcentaje"]) for r in rows]
 return excel_response(institucion=request.institucion,titulo="Reporte de asistencia",encabezados=("Alumno","Presentes","Ausentes","Tardanzas","Justificadas","% asistencia"),filas=data,nombre=f"aulapro_asistencia_{timezone.localdate()}.xlsx",ciclo=ciclo,filtros=request.GET.urlencode())
@reporte_required("finanzas")
def exportar_finanzas(request):
 _,_= _base(request);d=sfinanzas.datos(request.institucion,request.GET);rows=[(c.alumno.nombre_completo,c.descripcion,c.monto_total,c.pagado_calc,c.saldo_calc,c.vencido_calc,c.dias_vencido) for c in d["cargos"]]
 return excel_response(institucion=request.institucion,titulo="Cuentas por cobrar",encabezados=("Alumno","Concepto","Cargo","Pagado","Saldo","Saldo vencido","Días vencido"),filas=rows,nombre=f"aulapro_morosidad_{timezone.localdate()}.xlsx",filtros=request.GET.urlencode())
