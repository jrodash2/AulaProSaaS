from io import BytesIO
from django.contrib import messages
from django.core.exceptions import PermissionDenied,ValidationError
from django.db.models import Count,Q
from django.http import FileResponse,HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from alumnos.models import Alumno,Inscripcion
from core.decorators import institucion_required
from core.permissions import LECTURA_ACADEMICA
from .forms import TareaForm
from .models import AdjuntoTarea,EntregaTarea,Tarea
from .services import GESTION,agregar_adjunto,cambiar_estado,crear_tarea,editar_tarea,puede_editar,rol,sincronizar_entregas_tarea,tareas_permitidas

def acceso(r):
 if rol(r) not in LECTURA_ACADEMICA:raise PermissionDenied
def base_qs(r):return tareas_permitidas(r).select_related("ciclo","curso","grado","seccion","asignacion_docente__docente","creada_por")
@institucion_required
def dashboard(r):
 acceso(r);h=timezone.now();q=base_qs(r);return render(r,"tareas/dashboard.html",{"publicadas":q.filter(estado="PUBLICADA").count(),"proximas":q.filter(estado="PUBLICADA",fecha_limite__gte=h,fecha_limite__lte=h+timezone.timedelta(days=7)).count(),"cerradas":q.filter(estado="CERRADA").count(),"docentes":q.values("asignacion_docente__docente").distinct().count()})
@institucion_required
def lista(r):
 acceso(r);q=base_qs(r)
 if r.GET.get("q"):q=q.filter(Q(titulo__icontains=r.GET["q"])|Q(curso__nombre_mostrado__icontains=r.GET["q"])|Q(asignacion_docente__docente__primer_nombre__icontains=r.GET["q"])|Q(asignacion_docente__docente__primer_apellido__icontains=r.GET["q"]))
 for f in ("ciclo","curso","grado","seccion"):
  if r.GET.get(f):q=q.filter(**{f+"_id":r.GET[f]})
 if r.GET.get("estado"):q=q.filter(estado=r.GET["estado"])
 return render(r,"tareas/lista.html",{"tareas":q,"estados":Tarea.Estado.choices})
@institucion_required
def proximas(r):
 acceso(r);h=timezone.now();q=base_qs(r).filter(estado="PUBLICADA",fecha_limite__gte=h).order_by("fecha_limite");return render(r,"tareas/proximas.html",{"tareas":q})
@institucion_required
def formulario(r,pk=None):
 if rol(r) not in GESTION|{"DOCENTE"}:raise PermissionDenied
 obj=get_object_or_404(tareas_permitidas(r),pk=pk) if pk else None
 if obj and not puede_editar(r,obj):raise PermissionDenied
 f=TareaForm(r.POST or None,r.FILES or None,request=r,instance=obj,asignacion_id=r.GET.get("clase"))
 if r.method=="POST" and f.is_valid():
  d=f.cleaned_data.copy();asig=d.pop("asignacion_docente");archivos=d.pop("archivos",[]);publicar=d.pop("publicar_ahora",False);d.pop("actividad_evaluacion",None) if d.get("actividad_evaluacion") is None else None
  try:
   if obj:d.pop("asignacion_docente",None);x=editar_tarea(r,obj,**d)
   else:x=crear_tarea(r,asig,**d)
   for archivo in archivos:agregar_adjunto(r,x,archivo)
   if publicar and x.estado=="BORRADOR":cambiar_estado(r,x,"PUBLICADA")
   messages.success(r,"Tarea guardada.");return redirect("tareas:detalle",x.pk)
  except (ValidationError,PermissionDenied) as e:f.add_error(None,e)
 return render(r,"tareas/formulario.html",{"form":f,"tarea":obj})
@institucion_required
def detalle(r,pk):
 acceso(r);t=get_object_or_404(base_qs(r).prefetch_related("adjuntos"),pk=pk);sincronizar_entregas_tarea(t) if t.estado=="PUBLICADA" else None;res=t.entregas.aggregate(total=Count("id"),entregadas=Count("id",filter=Q(estado__in=("ENTREGADA","ENTREGADA_TARDE"))),pendientes=Count("id",filter=Q(estado="PENDIENTE")));return render(r,"tareas/detalle.html",{"tarea":t,"resumen":res,"editable":puede_editar(r,t),"gestion":rol(r) in GESTION})
@institucion_required
@require_POST
def estado(r,pk):
 t=get_object_or_404(tareas_permitidas(r),pk=pk)
 try:cambiar_estado(r,t,r.POST.get("estado",""),r.POST.get("motivo",""));messages.success(r,"Estado actualizado.")
 except (ValidationError,PermissionDenied) as e:messages.error(r," ".join(e.messages) if hasattr(e,"messages") else "Sin permiso")
 return redirect("tareas:detalle",pk)
@institucion_required
def descargar(r,pk,adjunto_id):
 acceso(r);t=get_object_or_404(tareas_permitidas(r),pk=pk);a=get_object_or_404(AdjuntoTarea,institucion=r.institucion,tarea=t,pk=adjunto_id);return FileResponse(a.archivo.open("rb"),as_attachment=True,filename=a.nombre_original)
@institucion_required
def reportes(r):
 acceso(r);q=base_qs(r).annotate(total=Count("entregas"),entregadas=Count("entregas",filter=Q(entregas__estado__in=("ENTREGADA","ENTREGADA_TARDE"))),pendientes=Count("entregas",filter=Q(entregas__estado="PENDIENTE")));return render(r,"tareas/reportes.html",{"tareas":q})
@institucion_required
def exportar(r):
 acceso(r);q=base_qs(r).annotate(total=Count("entregas"),entregadas_n=Count("entregas",filter=Q(entregas__estado__in=("ENTREGADA","ENTREGADA_TARDE"))),pendientes_n=Count("entregas",filter=Q(entregas__estado="PENDIENTE")));w=Workbook();s=w.active;s.title="Tareas";s.append(["Título","Curso","Sección","Docente","Publicación","Límite","Estado","Alumnos","Entregadas","Pendientes"])
 for t in q:s.append([t.titulo,t.curso.nombre,t.seccion.nombre,t.asignacion_docente.docente.nombre_completo,t.fecha_publicacion.replace(tzinfo=None),t.fecha_limite.replace(tzinfo=None),t.get_estado_display(),t.total,t.entregadas_n,t.pendientes_n])
 b=BytesIO();w.save(b);x=HttpResponse(b.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");x["Content-Disposition"]='attachment; filename="tareas.xlsx"';return x
@institucion_required
def alumno(r,pk):
 acceso(r);a=get_object_or_404(Alumno,institucion=r.institucion,pk=pk);secciones=Inscripcion.objects.filter(institucion=r.institucion,alumno=a).values_list("seccion_id",flat=True);q=Tarea.objects.filter(institucion=r.institucion,seccion_id__in=secciones,estado__in=("PUBLICADA","CERRADA")).select_related("curso","asignacion_docente__docente").order_by("fecha_limite");return render(r,"tareas/alumno.html",{"alumno":a,"tareas":q})
