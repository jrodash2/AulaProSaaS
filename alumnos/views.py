from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count,Q
from django.http import FileResponse,JsonResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from openpyxl import Workbook
from auditoria.services import registrar_evento
from core.decorators import gestion_alumnos_required,institucion_required
from academico.models import CicloEscolar,GradoInstitucion,OfertaAcademica,Seccion
from .forms import AlumnoForm,EncargadoForm,FamiliaForm,ImportarForm,InscripcionForm,RetiroForm,VinculoForm
from .models import Alumno,AlumnoEncargado,Encargado,Familia,ImportacionAlumnos,Inscripcion
from .services import crear_plantilla,ejecutar_importacion,prevalidar

def _alumnos(request): return Alumno.objects.filter(institucion=request.institucion)
def _filtrar(request,qs):
    q=request.GET.get("q","").strip()
    if q:
        for term in q.split(): qs=qs.filter(Q(cui__icontains=term)|Q(primer_nombre__icontains=term)|Q(segundo_nombre__icontains=term)|Q(primer_apellido__icontains=term)|Q(segundo_apellido__icontains=term))
    if request.GET.get("estado"): qs=qs.filter(estado=request.GET["estado"])
    ciclo=request.GET.get("ciclo")
    if ciclo: qs=qs.filter(inscripciones__ciclo_id=ciclo)
    for key,lookup in (("nivel","inscripciones__oferta_academica__nivel_id"),("oferta","inscripciones__oferta_academica_id"),("grado","inscripciones__grado_id"),("seccion","inscripciones__seccion_id")):
        if request.GET.get(key): qs=qs.filter(**{lookup:request.GET[key]})
    return qs.distinct()

@institucion_required
def landing(request):
    return render(request,"alumnos/landing.html",{"alumnos":_alumnos(request).count(),"familias":request.institucion.familias.count(),"inscripciones":request.institucion.inscripciones.filter(estado=Inscripcion.Estado.ACTIVA).count()})

@institucion_required
def lista(request):
    qs=_filtrar(request,_alumnos(request).prefetch_related("inscripciones__ciclo","inscripciones__grado","inscripciones__seccion"))
    pagina=Paginator(qs,25).get_page(request.GET.get("page")); ciclos=CicloEscolar.objects.filter(institucion=request.institucion)
    return render(request,"alumnos/lista.html",{"pagina":pagina,"alumnos":pagina,"ciclos":ciclos,"ofertas":OfertaAcademica.objects.filter(institucion=request.institucion),"grados":GradoInstitucion.objects.filter(institucion=request.institucion),"secciones":Seccion.objects.filter(institucion=request.institucion),"estados":Alumno.Estado.choices,"q":request.GET.get("q","")})

@gestion_alumnos_required
@transaction.atomic
def crear(request):
    cui_encargado=(request.POST.get("encargado-cui") or "").strip() if request.method=="POST" else ""
    encargado_existente=Encargado.objects.filter(institucion=request.institucion,cui=cui_encargado).first() if cui_encargado else None
    af=AlumnoForm(request.POST or None,request.FILES or None,institucion=request.institucion,prefix="alumno")
    ff=FamiliaForm(request.POST or None,prefix="familia"); ef=EncargadoForm(request.POST or None,instance=encargado_existente,prefix="encargado"); vf=VinculoForm(request.POST or None,prefix="vinculo"); inf=InscripcionForm(request.POST or None,institucion=request.institucion,prefix="inscripcion")
    af.instance.institucion=request.institucion; ff.instance.institucion=request.institucion; ef.instance.institucion=request.institucion; inf.instance.institucion=request.institucion
    crear_familia=request.POST.get("crear_familia")=="1"; crear_encargado=request.POST.get("crear_encargado")=="1"
    valid=request.method=="POST" and af.is_valid() and inf.is_valid() and (not crear_familia or ff.is_valid()) and (not crear_encargado or ef.is_valid() and vf.is_valid())
    if valid:
        familia=None
        if crear_familia:
            familia=ff.save(commit=False); familia.institucion=request.institucion; familia.save(); registrar_evento(request,"CREAR_FAMILIA",familia)
        alumno=af.save(commit=False); alumno.institucion=request.institucion; alumno.familia=familia or alumno.familia; alumno.save(); registrar_evento(request,"CREAR_ALUMNO",alumno)
        if crear_encargado:
            cui=ef.cleaned_data.get("cui"); encargado=encargado_existente
            if not encargado: encargado=ef.save(commit=False); encargado.institucion=request.institucion; encargado.save(); registrar_evento(request,"CREAR_ENCARGADO",encargado)
            vinculo=vf.save(commit=False); vinculo.institucion=request.institucion; vinculo.alumno=alumno; vinculo.encargado=encargado; vinculo.save(); registrar_evento(request,"VINCULAR_ENCARGADO",vinculo)
        ins=inf.save(commit=False); ins.institucion=request.institucion; ins.alumno=alumno; ins.save(); registrar_evento(request,"CREAR_INSCRIPCION",ins)
        messages.success(request,"Estudiante e inscripción creados correctamente."); return redirect("alumnos:detalle",pk=alumno.pk)
    return render(request,"alumnos/formulario_alumno.html",{"alumno_form":af,"familia_form":ff,"encargado_form":ef,"vinculo_form":vf,"inscripcion_form":inf,"crear_familia":crear_familia,"crear_encargado":crear_encargado})

@institucion_required
def detalle(request,pk):
    alumno=get_object_or_404(_alumnos(request).select_related("familia").prefetch_related("inscripciones__ciclo","inscripciones__oferta_academica","inscripciones__grado","inscripciones__seccion","vinculos_encargados__encargado"),pk=pk)
    return render(request,"alumnos/detalle.html",{"alumno":alumno,"inscripcion_actual":alumno.inscripciones.filter(estado=Inscripcion.Estado.ACTIVA).first(),"eventos":alumno.eventos_auditoria.all()[:10] if hasattr(alumno,"eventos_auditoria") else []})

@gestion_alumnos_required
def editar(request,pk):
    alumno=get_object_or_404(_alumnos(request),pk=pk); form=AlumnoForm(request.POST or None,request.FILES or None,instance=alumno,institucion=request.institucion)
    form.instance.institucion=request.institucion
    if request.method=="POST" and form.is_valid(): form.save(); registrar_evento(request,"EDITAR_ALUMNO",alumno); messages.success(request,"Expediente actualizado."); return redirect("alumnos:detalle",pk=pk)
    return render(request,"alumnos/formulario_simple.html",{"form":form,"titulo":"Editar estudiante","volver":"alumnos:detalle","volver_pk":pk})

@institucion_required
def cui_disponible(request):
    cui=request.GET.get("cui",""); alumno=_alumnos(request).filter(cui=cui).first()
    return JsonResponse({"disponible":not bool(alumno),"alumno":{"id":alumno.pk,"nombre":alumno.nombre_completo,"url":f"/alumnos/estudiantes/{alumno.pk}/"} if alumno else None})

@institucion_required
def opciones_inscripcion(request):
    if request.GET.get("ciclo"):
        qs=OfertaAcademica.objects.filter(institucion=request.institucion,ciclo_id=request.GET["ciclo"],activa=True); campo="nombre_mostrado"
    elif request.GET.get("oferta"):
        qs=GradoInstitucion.objects.filter(institucion=request.institucion,oferta_id=request.GET["oferta"],activo=True); campo="nombre"
    elif request.GET.get("grado"):
        qs=Seccion.objects.filter(institucion=request.institucion,grado_id=request.GET["grado"],activa=True); campo="nombre"
    else: return JsonResponse({"resultados":[]})
    return JsonResponse({"resultados":[{"id":x.pk,"nombre":getattr(x,campo)} for x in qs]})

@institucion_required
def familias(request):
    qs=request.institucion.familias.annotate(total_alumnos=Count("alumnos")); return render(request,"alumnos/familias.html",{"familias":qs})
@gestion_alumnos_required
def familia_form(request,pk=None):
    obj=get_object_or_404(request.institucion.familias,pk=pk) if pk else None; form=FamiliaForm(request.POST or None,instance=obj)
    if request.method=="POST" and form.is_valid(): item=form.save(commit=False); item.institucion=request.institucion; item.save(); registrar_evento(request,"EDITAR_FAMILIA" if obj else "CREAR_FAMILIA",item); return redirect("alumnos:familia_detalle",pk=item.pk)
    return render(request,"alumnos/formulario_simple.html",{"form":form,"titulo":"Editar familia" if obj else "Nueva familia","volver":"alumnos:familias"})
@institucion_required
def familia_detalle(request,pk): return render(request,"alumnos/familia_detalle.html",{"familia":get_object_or_404(request.institucion.familias.prefetch_related("alumnos__vinculos_encargados__encargado"),pk=pk)})

@institucion_required
def encargados(request): return render(request,"alumnos/encargados.html",{"encargados":request.institucion.encargados.annotate(total_alumnos=Count("vinculos_alumnos"))})
@gestion_alumnos_required
def encargado_form(request,pk=None):
    obj=get_object_or_404(request.institucion.encargados,pk=pk) if pk else None; form=EncargadoForm(request.POST or None,instance=obj)
    if request.method=="POST" and form.is_valid(): item=form.save(commit=False); item.institucion=request.institucion; item.save(); registrar_evento(request,"EDITAR_ENCARGADO" if obj else "CREAR_ENCARGADO",item); return redirect("alumnos:encargado_detalle",pk=item.pk)
    return render(request,"alumnos/formulario_simple.html",{"form":form,"titulo":"Editar encargado" if obj else "Nuevo encargado","volver":"alumnos:encargados"})
@institucion_required
def encargado_detalle(request,pk): return render(request,"alumnos/encargado_detalle.html",{"encargado":get_object_or_404(request.institucion.encargados.prefetch_related("vinculos_alumnos__alumno"),pk=pk)})

@institucion_required
def inscripciones(request):
    qs=request.institucion.inscripciones.select_related("alumno","ciclo","oferta_academica","grado","seccion")
    for key in ("ciclo","oferta_academica","grado","seccion","estado"):
        if request.GET.get(key): qs=qs.filter(**{key:request.GET[key]})
    return render(request,"alumnos/inscripciones.html",{"inscripciones":qs,"ciclos":CicloEscolar.objects.filter(institucion=request.institucion),"estados":Inscripcion.Estado.choices})
@institucion_required
def inscripcion_detalle(request,pk):
    inscripcion=get_object_or_404(request.institucion.inscripciones.select_related("alumno","ciclo","oferta_academica","grado","seccion"),pk=pk)
    return render(request,"alumnos/inscripcion_detalle.html",{"inscripcion":inscripcion})
@gestion_alumnos_required
def inscripcion_form(request,alumno_pk,pk=None):
    alumno=get_object_or_404(_alumnos(request),pk=alumno_pk); obj=get_object_or_404(request.institucion.inscripciones,pk=pk,alumno=alumno) if pk else None; form=InscripcionForm(request.POST or None,instance=obj,institucion=request.institucion); form.instance.institucion=request.institucion; form.instance.alumno=alumno
    if request.method=="POST" and form.is_valid(): item=form.save(); registrar_evento(request,"EDITAR_INSCRIPCION" if obj else "CREAR_INSCRIPCION",item); return redirect("alumnos:detalle",pk=alumno.pk)
    return render(request,"alumnos/formulario_simple.html",{"form":form,"titulo":"Editar inscripción" if obj else "Nueva inscripción","volver":"alumnos:detalle","volver_pk":alumno.pk})
@gestion_alumnos_required
def retirar(request,pk):
    ins=get_object_or_404(request.institucion.inscripciones,pk=pk,estado=Inscripcion.Estado.ACTIVA); form=RetiroForm(request.POST or None)
    if request.method=="POST" and form.is_valid(): ins.estado=Inscripcion.Estado.RETIRADA; ins.fecha_retiro=form.cleaned_data["fecha_retiro"]; ins.motivo_retiro=form.cleaned_data["motivo_retiro"]; ins.save(); registrar_evento(request,"RETIRAR_ALUMNO",ins); messages.warning(request,"Inscripción retirada; el expediente se conserva."); return redirect("alumnos:detalle",pk=ins.alumno_id)
    return render(request,"alumnos/formulario_simple.html",{"form":form,"titulo":"Retirar del ciclo","volver":"alumnos:detalle","volver_pk":ins.alumno_id})

@gestion_alumnos_required
def importar(request):
    form=ImportarForm(request.POST or None,request.FILES or None,institucion=request.institucion); preview=None; registro=None
    if request.method=="POST" and form.is_valid():
        registro=ImportacionAlumnos.objects.create(institucion=request.institucion,usuario=request.user,ciclo=form.cleaned_data["ciclo"],archivo_original=form.cleaned_data["archivo"],nombre_archivo=form.cleaned_data["archivo"].name)
        preview=prevalidar(registro.archivo_original,request.institucion,registro.ciclo); registro.total_filas=len(preview["filas"]); registro.errores=len(preview["errores"]); registro.detalle_errores=preview["errores"]; registro.estado=ImportacionAlumnos.Estado.LISTA if not preview["errores"] else ImportacionAlumnos.Estado.FALLIDA; registro.save()
    return render(request,"alumnos/importar.html",{"form":form,"preview":preview,"registro":registro})
@gestion_alumnos_required
def confirmar_importacion(request,pk):
    registro=get_object_or_404(request.institucion.importaciones_alumnos,pk=pk,estado=ImportacionAlumnos.Estado.LISTA)
    if request.method=="POST":
        try: ejecutar_importacion(registro)
        except ValidationError as exc: messages.error(request,str(exc))
        else: registrar_evento(request,"IMPORTAR_ALUMNOS",registro); messages.success(request,"Importación completada correctamente.")
    return redirect("alumnos:importacion_detalle",pk=pk)
@institucion_required
def importaciones(request): return render(request,"alumnos/importaciones.html",{"importaciones":request.institucion.importaciones_alumnos.select_related("ciclo","usuario")})
@institucion_required
def importacion_detalle(request,pk): return render(request,"alumnos/importacion_detalle.html",{"item":get_object_or_404(request.institucion.importaciones_alumnos,pk=pk)})
@institucion_required
def plantilla(request):
    ciclo=get_object_or_404(CicloEscolar,pk=request.GET.get("ciclo"),institucion=request.institucion); return FileResponse(crear_plantilla(request.institucion,ciclo),as_attachment=True,filename=f"plantilla-alumnos-{ciclo.anio}.xlsx")
@institucion_required
def exportar(request):
    qs=_filtrar(request,_alumnos(request)).prefetch_related("inscripciones__ciclo","inscripciones__oferta_academica","inscripciones__grado","inscripciones__seccion"); wb=Workbook(); ws=wb.active; ws.title="ALUMNOS"; ws.append(["CUI","Alumno","Ciclo","Oferta","Grado","Sección","Estado"])
    for a in qs:
        i=next((x for x in a.inscripciones.all() if x.estado==Inscripcion.Estado.ACTIVA),None); ws.append([a.cui or "",a.nombre_completo,i.ciclo.nombre if i else "",i.oferta_academica.nombre_mostrado if i else "",i.grado.nombre if i else "",i.seccion.nombre if i else "",a.get_estado_display()])
    from io import BytesIO
    out=BytesIO(); wb.save(out); out.seek(0); return FileResponse(out,as_attachment=True,filename="estudiantes-aulapro.xlsx")
