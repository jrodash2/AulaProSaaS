from pathlib import Path
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from django.utils import timezone
from core.decorators import institucion_required
from portal.permissions import portal_role_required,get_alumno_portal
from suscripciones.services import modulo_habilitado
from auditoria.services import registrar_evento
from .forms import *
from .models import *
from .services import *
def acceso(request):
 if not modulo_habilitado(request.institucion,"SEGUIMIENTO") or rol(request)=="CONTABILIDAD":raise PermissionDenied
@institucion_required
def dashboard(request):
 acceso(request);q=registros_visibles_para_usuario(request);hoy=timezone.localdate();return render(request,"seguimiento/dashboard.html",{"abiertos":q.filter(estado="ABIERTO").count(),"en_seguimiento":q.filter(estado="EN_SEGUIMIENTO").count(),"reconocimientos":q.filter(tipo="POSITIVO",fecha__year=hoy.year,fecha__month=hoy.month).count(),"compromisos":CompromisoSeguimiento.objects.filter(registro__in=q,estado="PENDIENTE").count()})
@institucion_required
def casos(request):
 acceso(request);q=registros_visibles_para_usuario(request)
 for key in ("ciclo","categoria","tipo","estado","gravedad"):
  if request.GET.get(key):q=q.filter(**{f"{key}_id" if key in ("ciclo","categoria") else key:request.GET[key]})
 return render(request,"seguimiento/casos.html",{"items":q,"categorias":CategoriaSeguimiento.objects.filter(institucion=request.institucion),"estados":RegistroSeguimiento.Estado.choices,"tipos":CategoriaSeguimiento.Tipo.choices})
@institucion_required
def nuevo(request,alumno_pk=None):
 acceso(request);alumnos=alumnos_registrables(request);initial={}
 if alumno_pk:initial["inscripcion"]=get_object_or_404(alumnos,pk=alumno_pk).inscripciones.filter(estado="ACTIVA").first()
 form=RegistroForm(request.POST or None,institucion=request.institucion,alumnos=alumnos,initial=initial)
 if rol(request)=="DOCENTE":form.fields["confidencialidad"].choices=[x for x in RegistroSeguimiento.Confidencialidad.choices if x[0]!="INTERNO"]
 if request.method=="POST" and form.is_valid():
  r=form.save(commit=False);r.institucion=request.institucion;r.alumno=r.inscripcion.alumno;r.ciclo=r.inscripcion.ciclo;r.registrado_por=request.user
  if rol(request)=="DOCENTE" and r.ciclo.cerrado:raise PermissionDenied
  if rol(request)=="SECRETARIA" and r.confidencialidad=="INTERNO":raise PermissionDenied
  r.save();registrar_evento(request,"CREAR_SEGUIMIENTO",r);return redirect("seguimiento:detalle",pk=r.pk)
 return render(request,"seguimiento/form.html",{"form":form,"titulo":"Nuevo seguimiento"})
@institucion_required
def detalle(request,pk):
 acceso(request);r=get_object_or_404(registros_visibles_para_usuario(request),pk=pk);return render(request,"seguimiento/detalle.html",{"registro":r,"editable":puede_editar_registro(request,r),"nota_form":NotaForm(),"compromiso_form":CompromisoForm(),"reunion_form":ReunionForm(institucion=request.institucion)})
@institucion_required
@require_POST
def agregar_nota(request,pk):
 acceso(request);r=get_object_or_404(registros_visibles_para_usuario(request),pk=pk)
 if not puede_editar_registro(request,r):raise PermissionDenied
 f=NotaForm(request.POST)
 if f.is_valid():o=f.save(commit=False);o.institucion=request.institucion;o.registro=r;o.autor=request.user;o.save();registrar_evento(request,"AGREGAR_NOTA_SEGUIMIENTO",o)
 return redirect("seguimiento:detalle",pk=pk)
@institucion_required
@require_POST
def agregar_compromiso(request,pk):
 acceso(request);r=get_object_or_404(registros_visibles_para_usuario(request),pk=pk)
 if not puede_editar_registro(request,r):raise PermissionDenied
 f=CompromisoForm(request.POST)
 if f.is_valid():o=f.save(commit=False);o.institucion=request.institucion;o.registro=r;o.creado_por=request.user;o.save();registrar_evento(request,"AGREGAR_COMPROMISO",o)
 return redirect("seguimiento:detalle",pk=pk)
@institucion_required
@require_POST
def agregar_reunion(request,pk):
 acceso(request);r=get_object_or_404(registros_visibles_para_usuario(request),pk=pk);f=ReunionForm(request.POST,institucion=request.institucion)
 if not puede_editar_registro(request,r):raise PermissionDenied
 if f.is_valid():o=f.save(commit=False);o.institucion=request.institucion;o.alumno=r.alumno;o.registro=r;o.creado_por=request.user;o.save();registrar_evento(request,"REGISTRAR_REUNION_SEGUIMIENTO",o)
 return redirect("seguimiento:detalle",pk=pk)
@institucion_required
@require_POST
def agregar_adjunto(request,pk):
 acceso(request);r=get_object_or_404(registros_visibles_para_usuario(request),pk=pk)
 if not puede_editar_registro(request,r):raise PermissionDenied
 archivo=request.FILES.get("archivo")
 if archivo:
  o=AdjuntoSeguimiento(institucion=request.institucion,registro=r,archivo=archivo,nombre_original=Path(archivo.name).name,cargado_por=request.user);o.save();registrar_evento(request,"ADJUNTAR_SEGUIMIENTO",o)
 return redirect("seguimiento:detalle",pk=pk)
@institucion_required
@require_POST
def cerrar(request,pk):
 acceso(request);r=get_object_or_404(registros_visibles_para_usuario(request),pk=pk);cerrar_registro(request,r,request.POST.get("conclusion","").strip());registrar_evento(request,"CERRAR_SEGUIMIENTO",r);return redirect("seguimiento:detalle",pk=pk)
@institucion_required
@require_POST
def notificar(request,pk):
 acceso(request);r=get_object_or_404(registros_visibles_para_usuario(request),pk=pk);notificar_encargados(request,r);messages.success(request,"Notificación disponible para el encargado.");return redirect("seguimiento:detalle",pk=pk)
@institucion_required
def categorias(request):acceso(request);return render(request,"seguimiento/categorias.html",{"items":CategoriaSeguimiento.objects.filter(institucion=request.institucion)})
@institucion_required
def categoria_form(request,pk=None):
 acceso(request)
 if rol(request) not in {"PROPIETARIO","DIRECTOR","ADMINISTRADOR"}:raise PermissionDenied
 o=get_object_or_404(CategoriaSeguimiento,institucion=request.institucion,pk=pk) if pk else None;f=CategoriaForm(request.POST or None,instance=o)
 if request.method=="POST" and f.is_valid():x=f.save(commit=False);x.institucion=request.institucion;x.save();registrar_evento(request,"EDITAR_TIPO_SEGUIMIENTO" if o else "CREAR_TIPO_SEGUIMIENTO",x);return redirect("seguimiento:categorias")
 return render(request,"seguimiento/form.html",{"form":f,"titulo":"Categoría"})
@portal_role_required("PADRE","ALUMNO")
def portal(request,alumno_pk):
 if not modulo_habilitado(request.institucion,"SEGUIMIENTO"):raise PermissionDenied
 a=get_alumno_portal(request,alumno_pk);q=a.registros_seguimiento.filter(institucion=request.institucion,confidencialidad__in=("PADRES","PUBLICABLE_PORTAL")).exclude(estado="ANULADO").select_related("categoria")
 if rol(request)=="ALUMNO":q=q.filter(confidencialidad="PUBLICABLE_PORTAL")
 return render(request,"seguimiento/portal.html",{"alumno":a,"items":q})
@institucion_required
def descargar(request,pk):
 acceso(request);a=get_object_or_404(AdjuntoSeguimiento.objects.filter(institucion=request.institucion,registro__in=registros_visibles_para_usuario(request)),pk=pk);return FileResponse(a.archivo.open("rb"),as_attachment=True,filename=Path(a.nombre_original).name)
