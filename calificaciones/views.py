from io import BytesIO
from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import PermissionDenied,ValidationError
from django.db.models import Count,Q,Sum
from django.http import HttpResponse,JsonResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from core.decorators import institucion_required
from core.permissions import LECTURA_ACADEMICA
from alumnos.models import Alumno
from docentes.models import AsignacionDocente
from auditoria.services import registrar_evento
from .forms import ActividadForm,PeriodoForm
from .models import ActividadEvaluacion,Calificacion,PeriodoAcademico,TipoEvaluacion
from .services import GESTION,actividades_permitidas,asignaciones_usuario,cerrar_periodo,config,crear_actividad,guardar_calificacion,promedio_alumno,reabrir_periodo,resultado,rol

def acceso(r):
 if rol(r) not in LECTURA_ACADEMICA:raise PermissionDenied
def excel(nombre,headers,rows):
 w=Workbook();s=w.active;s.title=nombre[:31];s.append(headers)
 for x in rows:s.append(x)
 b=BytesIO();w.save(b);res=HttpResponse(b.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");res["Content-Disposition"]=f'attachment; filename="{nombre}.xlsx"';return res
@institucion_required
def dashboard(r):
 acceso(r);hoy=__import__('django.utils.timezone',fromlist=['localdate']).localdate();periodo=PeriodoAcademico.objects.filter(institucion=r.institucion,activo=True,fecha_inicio__lte=hoy,fecha_fin__gte=hoy).first();acts=actividades_permitidas(r).filter(activa=True);return render(r,"calificaciones/dashboard.html",{"periodo":periodo,"actividades":acts.count(),"pendientes":Calificacion.objects.filter(institucion=r.institucion,actividad__in=acts,estado="PENDIENTE").count(),"cerrados":PeriodoAcademico.objects.filter(institucion=r.institucion,cerrado=True).count()})
@institucion_required
def periodos(r):
 acceso(r);return render(r,"calificaciones/periodos.html",{"periodos":PeriodoAcademico.objects.filter(institucion=r.institucion).select_related("ciclo")})
@institucion_required
def periodo_form(r,pk=None):
 if rol(r) not in GESTION:raise PermissionDenied
 obj=get_object_or_404(PeriodoAcademico,institucion=r.institucion,pk=pk) if pk else None;f=PeriodoForm(r.POST or None,instance=obj,institucion=r.institucion)
 if r.method=="POST" and f.is_valid():x=f.save(commit=False);x.institucion=r.institucion;x.save();registrar_evento(r,"EDITAR_PERIODO" if obj else "CREAR_PERIODO",x);messages.success(r,"Período guardado.");return redirect("calificaciones:periodo_detalle",x.pk)
 return render(r,"calificaciones/form.html",{"form":f,"titulo":"Editar período" if obj else "Nuevo período"})
@institucion_required
def periodo_detalle(r,pk):
 acceso(r);p=get_object_or_404(PeriodoAcademico,institucion=r.institucion,pk=pk);acts=p.actividades.filter(activa=True);return render(r,"calificaciones/periodo_detalle.html",{"periodo":p,"actividades":acts.count(),"cursos":acts.values("curso","seccion").distinct().count(),"pendientes":Calificacion.objects.filter(actividad__in=acts,estado="PENDIENTE").count(),"gestion":rol(r) in GESTION})
@institucion_required
@require_POST
def periodo_cerrar(r,pk):
 p=get_object_or_404(PeriodoAcademico,institucion=r.institucion,pk=pk)
 try:(reabrir_periodo(r,p,r.POST.get("motivo","")) if p.cerrado else cerrar_periodo(r,p));messages.success(r,"Período reabierto." if p.cerrado else "Período cerrado.")
 except ValidationError as e:messages.error(r," ".join(e.messages))
 return redirect("calificaciones:periodo_detalle",pk)
@institucion_required
def tipos(r):
 if rol(r) not in GESTION:raise PermissionDenied
 if r.method=="POST":
  t=TipoEvaluacion(institucion=r.institucion,nombre=r.POST.get("nombre",""),codigo=r.POST.get("codigo",""),descripcion=r.POST.get("descripcion",""));t.full_clean();t.save();messages.success(r,"Tipo creado.")
 return render(r,"calificaciones/tipos.html",{"tipos":TipoEvaluacion.objects.filter(institucion=r.institucion)})
@institucion_required
def actividades(r):
 acceso(r);qs=actividades_permitidas(r).select_related("periodo","curso","seccion","tipo_evaluacion","asignacion_docente__docente");
 if r.GET.get("periodo"):qs=qs.filter(periodo_id=r.GET["periodo"])
 if r.GET.get("curso"):qs=qs.filter(curso_id=r.GET["curso"])
 return render(r,"calificaciones/actividades.html",{"actividades":qs,"periodos":PeriodoAcademico.objects.filter(institucion=r.institucion)})
@institucion_required
def actividad_nueva(r):
 if rol(r) not in GESTION|{"DOCENTE"}:raise PermissionDenied
 f=ActividadForm(r.POST or None,request=r)
 if r.method=="POST" and f.is_valid():
  d=f.cleaned_data;a=d.pop("asignacion_docente");d.update(asignacion_docente=a,ciclo=a.ciclo,curso=a.curso,grado=a.grado,seccion=a.seccion)
  try:x=crear_actividad(r,**d);messages.success(r,"Actividad creada y planilla inicializada.");return redirect("calificaciones:actividad_detalle",x.pk)
  except ValidationError as e:f.add_error(None,e)
 return render(r,"calificaciones/form.html",{"form":f,"titulo":"Nueva actividad"})
@institucion_required
def actividad_detalle(r,pk):
 acceso(r);a=get_object_or_404(actividades_permitidas(r).select_related("periodo","curso","seccion","tipo_evaluacion"),pk=pk);q=a.calificaciones.all();return render(r,"calificaciones/actividad_detalle.html",{"actividad":a,"calificados":q.filter(estado="CALIFICADO").count(),"pendientes":q.filter(estado="PENDIENTE").count(),"promedio":q.filter(estado="CALIFICADO").aggregate(x=__import__('django.db.models',fromlist=['Avg']).Avg("punteo_obtenido"))["x"]})
@institucion_required
def planillas(r):
 acceso(r);return render(r,"calificaciones/planillas.html",{"asignaciones":asignaciones_usuario(r).select_related("curso","grado","seccion","docente")})
@institucion_required
def planilla(r,asignacion_id):
 acceso(r);a=get_object_or_404(asignaciones_usuario(r).select_related("curso","grado","seccion","ciclo"),pk=asignacion_id);periodos=PeriodoAcademico.objects.filter(institucion=r.institucion,ciclo=a.ciclo);p=get_object_or_404(periodos,pk=r.GET.get("periodo")) if r.GET.get("periodo") else periodos.first();acts=list(actividades_permitidas(r).filter(asignacion_docente=a,periodo=p,activa=True).prefetch_related("calificaciones")) if p else [];ins=list(a.seccion.inscripciones.filter(institucion=r.institucion,ciclo=a.ciclo,estado="ACTIVA").select_related("alumno"));matrix=[]
 for i in ins:
  notas=[]
  for act in acts:notas.append(next((c for c in act.calificaciones.all() if c.alumno_id==i.alumno_id),None))
  matrix.append((i.alumno,notas,promedio_alumno(i.alumno,p,a.curso) if p else None))
 pond=sum((x.ponderacion for x in acts),Decimal("0"));return render(r,"calificaciones/planilla.html",{"asignacion":a,"periodos":periodos,"periodo":p,"actividades":acts,"matrix":matrix,"ponderacion":pond,"config":config(r.institucion)})
@institucion_required
@require_POST
def autosave(r,pk):
 c=get_object_or_404(Calificacion.objects.select_related("actividad__asignacion_docente","actividad__periodo","alumno"),institucion=r.institucion,pk=pk)
 try:guardar_calificacion(r,c,r.POST.get("estado","CALIFICADO"),r.POST.get("punteo"));return JsonResponse({"ok":True,"estado":c.estado,"punteo":str(c.punteo_obtenido) if c.punteo_obtenido is not None else None,"aporte":str(c.aporte) if c.aporte is not None else None})
 except (ValidationError,PermissionDenied) as e:return JsonResponse({"ok":False,"error":" ".join(e.messages) if hasattr(e,"messages") else "Sin permiso"},status=400 if isinstance(e,ValidationError) else 403)
@institucion_required
def alumno(r,pk):
 acceso(r);al=get_object_or_404(Alumno,institucion=r.institucion,pk=pk);periodos=PeriodoAcademico.objects.filter(institucion=r.institucion);p=get_object_or_404(periodos,pk=r.GET.get("periodo")) if r.GET.get("periodo") else periodos.first();cursos=AsignacionDocente.objects.filter(institucion=r.institucion,ciclo=p.ciclo,seccion__inscripciones__alumno=al,activa=True).select_related("curso").distinct() if p else [];cfg=config(r.institucion);filas=[(x.curso,promedio_alumno(al,p,x.curso),None) for x in cursos];filas=[(c,v,resultado(v,cfg)) for c,v,_ in filas];return render(r,"calificaciones/alumno.html",{"alumno":al,"periodos":periodos,"periodo":p,"filas":filas})
@institucion_required
def boletin(r,pk,periodo_id):
 acceso(r);al=get_object_or_404(Alumno,institucion=r.institucion,pk=pk);p=get_object_or_404(PeriodoAcademico,institucion=r.institucion,pk=periodo_id);ins=get_object_or_404(al.inscripciones, institucion=r.institucion,ciclo=p.ciclo);cursos=AsignacionDocente.objects.filter(institucion=r.institucion,ciclo=p.ciclo,seccion=ins.seccion,activa=True).select_related("curso");cfg=config(r.institucion);filas=[(x.curso,promedio_alumno(al,p,x.curso)) for x in cursos];return render(r,"calificaciones/boletin.html",{"alumno":al,"periodo":p,"inscripcion":ins,"filas":[(c,v,resultado(v,cfg)) for c,v in filas],"institucion":r.institucion})
@institucion_required
def reportes(r):
 acceso(r);p=PeriodoAcademico.objects.filter(institucion=r.institucion).first();q=Calificacion.objects.filter(institucion=r.institucion,actividad__periodo=p,estado="CALIFICADO").select_related("alumno","actividad__curso","actividad__seccion") if p else [];minima=config(r.institucion).nota_minima_aprobacion;bajo=[x for x in q if x.aporte is not None and x.aporte<x.actividad.ponderacion*minima/Decimal("100")];return render(r,"calificaciones/reportes.html",{"periodo":p,"bajo":bajo})
@institucion_required
def exportar_planilla(r,asignacion_id):
 a=get_object_or_404(asignaciones_usuario(r),pk=asignacion_id);q=Calificacion.objects.filter(institucion=r.institucion,actividad__asignacion_docente=a).select_related("alumno","actividad");return excel("planilla",["Alumno","Actividad","Punteo","Máximo","Estado"],((x.alumno.nombre_completo,x.actividad.nombre,x.punteo_obtenido,x.actividad.punteo_maximo,x.get_estado_display()) for x in q))
