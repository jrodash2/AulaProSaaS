from django.views.decorators.http import require_POST
from io import BytesIO
from django.contrib import messages
from django.db import transaction
from django.db.models import Count,Q,Sum
from django.http import FileResponse,JsonResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from openpyxl import Workbook
from auditoria.services import registrar_evento
from core.decorators import administrador_institucion_required,institucion_required,lectura_docentes_required
from academico.models import CicloEscolar,CursoInstitucion,GradoInstitucion,OfertaAcademica,Seccion
from alumnos.models import Inscripcion
from .forms import AccesoForm,AsignacionForm,CrearDocenteForm,DocenteForm,GuiaForm
from .models import AsignacionDocente,AsignacionGuia,Docente
from .services import cambiar_acceso_docente,crear_acceso_docente

def _docentes(request): return Docente.objects.filter(institucion=request.institucion)
def _ciclo(request):
 qs=CicloEscolar.objects.filter(institucion=request.institucion); ident=request.GET.get("ciclo") or request.POST.get("ciclo")
 return get_object_or_404(qs,pk=ident) if ident else qs.filter(es_actual=True).first() or qs.first()
def _filtrar(request,qs):
 q=request.GET.get("q","").strip()
 if q:
  for term in q.split(): qs=qs.filter(Q(codigo__icontains=term)|Q(cui__icontains=term)|Q(primer_nombre__icontains=term)|Q(primer_apellido__icontains=term)|Q(email__icontains=term))
 if request.GET.get("estado"): qs=qs.filter(estado=request.GET["estado"])
 if request.GET.get("acceso")=="si": qs=qs.filter(usuario__isnull=False)
 if request.GET.get("acceso")=="no": qs=qs.filter(usuario__isnull=True)
 if request.GET.get("especialidad"): qs=qs.filter(especialidad__icontains=request.GET["especialidad"])
 return qs

@lectura_docentes_required
def lista(request):
 qs=_filtrar(request,_docentes(request).annotate(total_asignaciones=Count("asignaciones",filter=Q(asignaciones__activa=True))))
 context={"docentes":qs,"estados":Docente.Estado.choices,"activos":_docentes(request).filter(estado=Docente.Estado.ACTIVO).count(),"con_acceso":_docentes(request).filter(usuario__isnull=False).count(),"sin_acceso":_docentes(request).filter(usuario__isnull=True).count(),"asignaciones":request.institucion.asignaciones_docentes.filter(activa=True).count()}
 return render(request,"docentes/lista.html",context)

@administrador_institucion_required
@transaction.atomic
def crear(request):
 form=CrearDocenteForm(request.POST or None,request.FILES or None); form.instance.institucion=request.institucion
 if request.method=="POST" and form.is_valid():
  docente=form.save(commit=False); docente.institucion=request.institucion; docente.save(); registrar_evento(request,"CREAR_DOCENTE",docente)
  if form.cleaned_data["crear_acceso"]:
   crear_acceso_docente(docente,{"username":form.cleaned_data["username"],"email":form.cleaned_data["email_acceso"],"password":form.cleaned_data["password"]}); registrar_evento(request,"CREAR_ACCESO_DOCENTE",docente)
  messages.success(request,"Docente creado correctamente."); return redirect("docentes:detalle",pk=docente.pk)
 return render(request,"docentes/formulario.html",{"form":form,"titulo":"Nuevo docente"})

@lectura_docentes_required
def detalle(request,pk):
 docente=get_object_or_404(_docentes(request).select_related("usuario").prefetch_related("asignaciones__ciclo","asignaciones__curso","asignaciones__grado","asignaciones__seccion","secciones_guia__seccion"),pk=pk)
 ciclo=_ciclo(request); carga=docente.asignaciones.filter(ciclo=ciclo,activa=True).select_related("curso","grado","seccion") if ciclo else docente.asignaciones.none()
 return render(request,"docentes/detalle.html",{"docente":docente,"ciclo":ciclo,"ciclos":CicloEscolar.objects.filter(institucion=request.institucion),"carga":carga,"periodos":carga.aggregate(v=Sum("curso__periodos_semanales"))["v"] or 0})

@administrador_institucion_required
def editar(request,pk):
 docente=get_object_or_404(_docentes(request),pk=pk); anterior=docente.estado; form=DocenteForm(request.POST or None,request.FILES or None,instance=docente); form.instance.institucion=request.institucion
 if request.method=="POST" and form.is_valid():
  form.save(); registrar_evento(request,"EDITAR_DOCENTE",docente)
  if anterior!=docente.estado: registrar_evento(request,"CAMBIAR_ESTADO_DOCENTE",docente); messages.warning(request,"Las asignaciones históricas se conservaron.")
  return redirect("docentes:detalle",pk=pk)
 return render(request,"docentes/formulario.html",{"form":form,"titulo":"Editar docente","docente":docente})

@administrador_institucion_required
def crear_acceso(request,pk):
 docente=get_object_or_404(_docentes(request),pk=pk,usuario__isnull=True); form=AccesoForm(request.POST or None)
 if request.method=="POST" and form.is_valid(): crear_acceso_docente(docente,form.cleaned_data); registrar_evento(request,"CREAR_ACCESO_DOCENTE",docente); messages.success(request,"Acceso docente creado."); return redirect("docentes:detalle",pk=pk)
 return render(request,"docentes/formulario.html",{"form":form,"titulo":"Crear acceso al sistema","docente":docente})

@administrador_institucion_required
@require_POST
def acceso_estado(request,pk):
 docente=get_object_or_404(_docentes(request).exclude(usuario=None),pk=pk)
 if request.method=="POST":
  asignacion=docente.usuario.asignaciones_institucion.get(institucion=request.institucion); nuevo_estado=not asignacion.activo; cambiar_acceso_docente(docente,nuevo_estado); registrar_evento(request,"CREAR_ACCESO_DOCENTE" if nuevo_estado else "DESACTIVAR_ACCESO_DOCENTE",docente); messages.success(request,"Estado del acceso actualizado.")
 return redirect("docentes:detalle",pk=pk)

@administrador_institucion_required
def asignaciones(request):
 ciclo=_ciclo(request); qs=request.institucion.asignaciones_docentes.select_related("docente","ciclo","oferta_academica","grado","seccion","curso")
 if ciclo: qs=qs.filter(ciclo=ciclo)
 for key in ("docente","oferta_academica","grado","seccion","curso"):
  if request.GET.get(key): qs=qs.filter(**{key:request.GET[key]})
 if request.GET.get("estado") in ("1","0"): qs=qs.filter(activa=request.GET["estado"]=="1")
 return render(request,"docentes/asignaciones.html",{"items":qs,"ciclo":ciclo,"ciclos":CicloEscolar.objects.filter(institucion=request.institucion),"docentes":_docentes(request),"ofertas":OfertaAcademica.objects.filter(institucion=request.institucion,ciclo=ciclo) if ciclo else []})

@lectura_docentes_required
def asignacion_detalle(request,pk):
 item=get_object_or_404(request.institucion.asignaciones_docentes.select_related("docente","ciclo","oferta_academica","grado","seccion","curso"),pk=pk)
 return render(request,"docentes/asignacion_detalle.html",{"item":item})

@administrador_institucion_required
def asignacion_form(request,pk=None):
 obj=get_object_or_404(request.institucion.asignaciones_docentes,pk=pk) if pk else None; form=AsignacionForm(request.POST or None,instance=obj,institucion=request.institucion); form.instance.institucion=request.institucion
 if request.method=="POST" and form.is_valid(): item=form.save(); registrar_evento(request,"EDITAR_ASIGNACION_DOCENTE" if obj else "CREAR_ASIGNACION_DOCENTE",item); messages.success(request,"Asignación guardada."); return redirect("docentes:asignaciones")
 return render(request,"docentes/asignacion_form.html",{"form":form,"titulo":"Editar asignación" if obj else "Nueva asignación"})

@administrador_institucion_required
@require_POST
def asignacion_estado(request,pk):
 item=get_object_or_404(request.institucion.asignaciones_docentes,pk=pk)
 if request.method=="POST": item.activa=not item.activa; item.fecha_fin=None if item.activa else timezone.localdate(); item.save(); registrar_evento(request,"EDITAR_ASIGNACION_DOCENTE" if item.activa else "FINALIZAR_ASIGNACION_DOCENTE",item)
 return redirect("docentes:asignaciones")

@administrador_institucion_required
@transaction.atomic
def asignacion_rapida(request,seccion_pk):
 seccion=get_object_or_404(Seccion.objects.select_related("ciclo","grado__oferta"),pk=seccion_pk,institucion=request.institucion); cursos=CursoInstitucion.objects.filter(institucion=request.institucion,grado=seccion.grado,activo=True); docentes=_docentes(request).filter(estado=Docente.Estado.ACTIVO)
 if request.method=="POST":
  for curso in cursos:
   docente_id=request.POST.get(f"curso_{curso.pk}")
   if docente_id:
    docente=get_object_or_404(docentes,pk=docente_id)
    AsignacionDocente.objects.filter(institucion=request.institucion,ciclo=seccion.ciclo,seccion=seccion,curso=curso,es_titular=True,activa=True).exclude(docente=docente).update(activa=False,fecha_fin=timezone.localdate())
    actual=AsignacionDocente.objects.filter(institucion=request.institucion,ciclo=seccion.ciclo,seccion=seccion,curso=curso,docente=docente,activa=True).first()
    if actual:
     actual.es_titular=True; actual.fecha_fin=None; actual.save(update_fields=("es_titular","fecha_fin","fecha_actualizacion"))
    else:
     AsignacionDocente.objects.create(institucion=request.institucion,ciclo=seccion.ciclo,seccion=seccion,curso=curso,docente=docente,oferta_academica=seccion.grado.oferta,grado=seccion.grado,fecha_inicio=timezone.localdate(),activa=True,es_titular=True)
  registrar_evento(request,"CREAR_ASIGNACION_DOCENTE",seccion); messages.success(request,"Asignaciones de sección guardadas."); return redirect("academico:grados_secciones")
 return render(request,"docentes/asignacion_rapida.html",{"seccion":seccion,"cursos":cursos,"docentes":docentes})

@administrador_institucion_required
def guia(request,seccion_pk):
 seccion=get_object_or_404(Seccion.objects.select_related("ciclo"),pk=seccion_pk,institucion=request.institucion); actual=AsignacionGuia.objects.filter(institucion=request.institucion,seccion=seccion,activa=True).first(); form=GuiaForm(request.POST or None,institucion=request.institucion)
 if request.method=="POST" and form.is_valid():
  if actual: actual.activa=False; actual.fecha_fin=timezone.localdate(); actual.save()
  item=form.save(commit=False); item.pk=None; item.institucion=request.institucion; item.ciclo=seccion.ciclo; item.seccion=seccion; item.activa=True; item.save(); registrar_evento(request,"ASIGNAR_DOCENTE_GUIA",item); return redirect("academico:grados_secciones")
 return render(request,"docentes/formulario.html",{"form":form,"titulo":f"Docente guía · {seccion}"})

@lectura_docentes_required
def carga(request):
 ciclo=_ciclo(request); docentes=_docentes(request).annotate(total_asignaciones=Count("asignaciones",filter=Q(asignaciones__ciclo=ciclo,asignaciones__activa=True)),periodos=Sum("asignaciones__curso__periodos_semanales",filter=Q(asignaciones__ciclo=ciclo,asignaciones__activa=True)))
 return render(request,"docentes/carga.html",{"docentes":docentes,"ciclo":ciclo,"ciclos":CicloEscolar.objects.filter(institucion=request.institucion)})

@institucion_required
def mis_clases(request):
 docente=get_object_or_404(Docente,usuario=request.user,institucion=request.institucion); ciclo=_ciclo(request); clases=docente.asignaciones.filter(ciclo=ciclo,activa=True).select_related("curso","seccion","grado") if ciclo else docente.asignaciones.none(); return render(request,"docentes/mis_clases.html",{"docente":docente,"clases":clases,"ciclo":ciclo})
@institucion_required
def mi_clase(request,pk):
 docente=get_object_or_404(Docente,usuario=request.user,institucion=request.institucion); clase=get_object_or_404(docente.asignaciones.select_related("curso","seccion","grado","ciclo"),pk=pk,institucion=request.institucion,activa=True); estudiantes=Inscripcion.objects.filter(institucion=request.institucion,ciclo=clase.ciclo,grado=clase.grado,seccion=clase.seccion,estado=Inscripcion.Estado.ACTIVA).select_related("alumno"); return render(request,"docentes/mi_clase.html",{"clase":clase,"estudiantes":estudiantes})

@institucion_required
def opciones(request):
 if request.GET.get("ciclo"): qs=OfertaAcademica.objects.filter(institucion=request.institucion,ciclo_id=request.GET["ciclo"],activa=True); campo="nombre_mostrado"
 elif request.GET.get("oferta"): qs=GradoInstitucion.objects.filter(institucion=request.institucion,oferta_id=request.GET["oferta"],activo=True); campo="nombre"
 elif request.GET.get("grado") and request.GET.get("tipo")=="secciones": qs=Seccion.objects.filter(institucion=request.institucion,grado_id=request.GET["grado"],activa=True); campo="nombre"
 elif request.GET.get("grado"): qs=CursoInstitucion.objects.filter(institucion=request.institucion,grado_id=request.GET["grado"],activo=True); campo="nombre"
 else: return JsonResponse({"resultados":[]})
 return JsonResponse({"resultados":[{"id":x.pk,"nombre":getattr(x,campo)} for x in qs]})

@lectura_docentes_required
def exportar(request):
 qs=_filtrar(request,_docentes(request).annotate(total_asignaciones=Count("asignaciones",filter=Q(asignaciones__activa=True)),periodos=Sum("asignaciones__curso__periodos_semanales",filter=Q(asignaciones__activa=True)))); wb=Workbook(); ws=wb.active; ws.append(["Código","CUI","Nombre","Especialidad","Teléfono","Email","Estado","Asignaciones","Carga semanal"])
 for d in qs: ws.append([d.codigo,d.cui or "",d.nombre_completo,d.especialidad,d.telefono,d.email,d.get_estado_display(),d.total_asignaciones,d.periodos or 0])
 out=BytesIO(); wb.save(out); out.seek(0); return FileResponse(out,as_attachment=True,filename="docentes-aulapro.xlsx")
@lectura_docentes_required
def exportar_carga(request):
 ciclo=_ciclo(request); qs=request.institucion.asignaciones_docentes.filter(ciclo=ciclo,activa=True).select_related("docente","curso","grado","seccion","ciclo"); wb=Workbook(); ws=wb.active; ws.append(["Docente","Curso","Grado","Sección","Ciclo","Períodos semanales"])
 for a in qs: ws.append([a.docente.nombre_completo,a.curso.nombre,a.grado.nombre,a.seccion.nombre,a.ciclo.nombre,a.curso.periodos_semanales or 0])
 out=BytesIO(); wb.save(out); out.seek(0); return FileResponse(out,as_attachment=True,filename="carga-docente.xlsx")
