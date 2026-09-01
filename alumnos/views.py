from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count,Q
from django.http import FileResponse,JsonResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from openpyxl import Workbook
from auditoria.services import registrar_evento
from core.decorators import gestion_alumnos_required,institucion_required
from academico.models import CicloEscolar,GradoInstitucion,OfertaAcademica,ResultadoAnualAlumno,Seccion
from suscripciones.services import suscripcion_actual
from .forms import AlumnoForm,DocumentoAlumnoForm,EncargadoForm,FamiliaForm,ImportarForm,InscripcionForm,RequisitoDocumentoAlumnoForm,RetiroForm,RevisionDocumentoForm,TipoDocumentoAlumnoForm,VinculoForm
from .models import Alumno,AlumnoEncargado,DocumentoAlumno,Encargado,Familia,ImportacionAlumnos,Inscripcion,RequisitoDocumentoAlumno,TipoDocumentoAlumno
from .services import crear_plantilla,ejecutar_importacion,prevalidar,reinscripcion_masiva,resumen_expediente
from suscripciones.services import modulo_habilitado

def _alumnos(request): return Alumno.objects.filter(institucion=request.institucion)
def _expediente_habilitado(request):
    if not modulo_habilitado(request.institucion,"EXPEDIENTE"):raise PermissionDenied
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
    return render(request,"alumnos/detalle.html",{"alumno":alumno,"inscripcion_actual":alumno.inscripciones.filter(estado=Inscripcion.Estado.ACTIVA).first(),"eventos":alumno.eventos_auditoria.all()[:10] if hasattr(alumno,"eventos_auditoria") else [],"expediente":resumen_expediente(alumno) if modulo_habilitado(request.institucion,"EXPEDIENTE") else None})

@gestion_alumnos_required
def expedientes(request):
    _expediente_habilitado(request);qs=_filtrar(request,_alumnos(request).prefetch_related("inscripciones__grado","inscripciones__seccion"));filas=[]
    tipo_falta=request.GET.get("tipo_documento")
    for alumno in qs:
        resumen=resumen_expediente(alumno)
        if request.GET.get("estado")=="COMPLETO" and not resumen["completo"]:continue
        if request.GET.get("estado")=="INCOMPLETO" and resumen["completo"]:continue
        if tipo_falta and not any(str(x["requisito"].tipo_documento_id)==tipo_falta and x["estado"]!="APROBADO" for x in resumen["items"]):continue
        filas.append((alumno,resumen))
    return render(request,"alumnos/expedientes.html",{"filas":filas,"tipos":TipoDocumentoAlumno.objects.filter(institucion=request.institucion,activo=True),"ciclos":CicloEscolar.objects.filter(institucion=request.institucion),"grados":GradoInstitucion.objects.filter(institucion=request.institucion),"secciones":Seccion.objects.filter(institucion=request.institucion)})

@gestion_alumnos_required
def expediente_alumno(request,alumno_pk):
    _expediente_habilitado(request);alumno=get_object_or_404(_alumnos(request),pk=alumno_pk)
    return render(request,"alumnos/expediente_detalle.html",{"alumno":alumno,"resumen":resumen_expediente(alumno),"documentos":alumno.documentos.select_related("tipo_documento","cargado_por","revisado_por")})

@gestion_alumnos_required
def documento_subir(request,alumno_pk):
    _expediente_habilitado(request);alumno=get_object_or_404(_alumnos(request),pk=alumno_pk);reemplaza=get_object_or_404(alumno.documentos,pk=request.GET["reemplaza"]) if request.GET.get("reemplaza") else None;form=DocumentoAlumnoForm(request.POST or None,request.FILES or None,institucion=request.institucion,alumno=alumno,initial={"reemplaza_a":reemplaza,"tipo_documento":reemplaza.tipo_documento if reemplaza else None})
    if request.method=="POST" and form.is_valid():
        doc=form.save(commit=False);doc.institucion=request.institucion;doc.alumno=alumno;doc.cargado_por=request.user;doc.estado=DocumentoAlumno.Estado.ENTREGADO;doc.nombre_original=form.cleaned_data["archivo"].name.replace("\\","/").rsplit("/",1)[-1];doc.save();registrar_evento(request,"REEMPLAZAR_DOCUMENTO_ALUMNO" if doc.reemplaza_a_id else "SUBIR_DOCUMENTO_ALUMNO",doc);messages.success(request,"Documento cargado para revisión.");return redirect("alumnos:expediente_alumno",alumno_pk=alumno.pk)
    return render(request,"alumnos/formulario_simple.html",{"form":form,"titulo":"Subir documento","volver":"alumnos:expediente_alumno","volver_pk":alumno.pk})

@gestion_alumnos_required
@require_POST
def documento_revisar(request,pk):
    _expediente_habilitado(request);doc=get_object_or_404(DocumentoAlumno,institucion=request.institucion,pk=pk);form=RevisionDocumentoForm(request.POST)
    if form.is_valid():
        doc.estado=form.cleaned_data["estado"];motivo=form.cleaned_data["motivo"].strip();doc.motivo_rechazo=motivo if doc.estado=="RECHAZADO" else "";doc.observaciones=motivo if doc.estado=="NO_APLICA" else doc.observaciones;doc.revisado_por=request.user;doc.fecha_revision=timezone.now();doc.save();accion={"APROBADO":"APROBAR_DOCUMENTO_ALUMNO","RECHAZADO":"RECHAZAR_DOCUMENTO_ALUMNO","NO_APLICA":"MARCAR_NO_APLICA_DOCUMENTO"}[doc.estado];registrar_evento(request,accion,doc);messages.success(request,"Revisión registrada.")
    else:messages.error(request,"Revise los datos de la decisión.")
    return redirect("alumnos:expediente_alumno",alumno_pk=doc.alumno_id)

@institucion_required
def documento_descargar(request,pk):
    _expediente_habilitado(request);doc=get_object_or_404(DocumentoAlumno,institucion=request.institucion,pk=pk)
    if request.asignacion_institucion.rol not in ("PROPIETARIO","DIRECTOR","ADMINISTRADOR","SECRETARIA"):raise PermissionDenied
    if not doc.archivo:raise PermissionDenied
    return FileResponse(doc.archivo.open("rb"),as_attachment=True,filename=doc.nombre_original)

@gestion_alumnos_required
def tipos_documento(request):
    _expediente_habilitado(request);return render(request,"alumnos/tipos_documento.html",{"tipos":TipoDocumentoAlumno.objects.filter(institucion=request.institucion),"requisitos":RequisitoDocumentoAlumno.objects.filter(institucion=request.institucion).select_related("tipo_documento","aplica_a_nivel","aplica_a_oferta","aplica_a_grado","aplica_a_ciclo")})
@gestion_alumnos_required
def tipo_documento_form(request):
    _expediente_habilitado(request);form=TipoDocumentoAlumnoForm(request.POST or None)
    if request.method=="POST" and form.is_valid():obj=form.save(commit=False);obj.institucion=request.institucion;obj.save();registrar_evento(request,"CREAR_TIPO_DOCUMENTO",obj);return redirect("alumnos:tipos_documento")
    return render(request,"alumnos/formulario_simple.html",{"form":form,"titulo":"Nuevo tipo documental","volver":"alumnos:tipos_documento"})
@gestion_alumnos_required
def requisito_documento_form(request):
    _expediente_habilitado(request);form=RequisitoDocumentoAlumnoForm(request.POST or None,institucion=request.institucion)
    if request.method=="POST" and form.is_valid():obj=form.save(commit=False);obj.institucion=request.institucion;obj.save();registrar_evento(request,"CREAR_REQUISITO_DOCUMENTO",obj);return redirect("alumnos:tipos_documento")
    return render(request,"alumnos/formulario_simple.html",{"form":form,"titulo":"Nuevo requisito documental","volver":"alumnos:tipos_documento"})

@gestion_alumnos_required
def expedientes_exportar(request):
    _expediente_habilitado(request);wb=Workbook();ws=wb.active;ws.title="EXPEDIENTES";ws.append(["Alumno","CUI","Grado","Sección","Completitud","Pendientes","Rechazados"])
    for alumno in _alumnos(request):
        r=resumen_expediente(alumno);ins=alumno.inscripciones.filter(estado="ACTIVA").select_related("grado","seccion").first();ws.append([alumno.nombre_completo,alumno.cui or "",ins.grado.nombre if ins else "",ins.seccion.nombre if ins else "",r["porcentaje"],r["pendientes"],r["rechazados"]])
    from io import BytesIO
    out=BytesIO();wb.save(out);out.seek(0);return FileResponse(out,as_attachment=True,filename="expedientes-aulapro.xlsx")

@gestion_alumnos_required
def reinscripciones_inicio(request):
    ciclos=CicloEscolar.objects.filter(institucion=request.institucion).order_by("-anio")
    destino=get_object_or_404(ciclos,pk=request.GET["ciclo_destino"]) if request.GET.get("ciclo_destino") else ciclos.filter(estado=CicloEscolar.Estado.PLANIFICACION).first()
    if destino:return redirect("alumnos:reinscripciones_detalle",ciclo_destino=destino.pk)
    return render(request,"alumnos/reinscripciones_inicio.html",{"ciclos":ciclos})

def _reinscripciones_contexto(request,destino):
    origen=CicloEscolar.objects.filter(institucion=request.institucion,anio__lt=destino.anio,cerrado=True).order_by("-anio").first()
    resultados=ResultadoAnualAlumno.objects.none() if not origen else origen.resultados_anuales.select_related("alumno","inscripcion__grado","inscripcion__seccion").filter(resultado_final__in=("PROMOVIDO","NO_PROMOVIDO","EGRESADO"))
    filas=[]
    for r in resultados:
        orden=r.inscripcion.grado.orden+(1 if r.resultado_final=="PROMOVIDO" else 0)
        grado=destino.grados.filter(orden=orden).first() if r.resultado_final!="EGRESADO" else None
        existente=Inscripcion.objects.filter(alumno=r.alumno,ciclo=destino,estado="ACTIVA").first()
        filas.append({"resultado":r,"grado":grado,"secciones":destino.secciones.filter(grado=grado,activa=True).annotate(ocupados=Count("inscripciones",filter=Q(inscripciones__estado="ACTIVA"))) if grado else [],"existente":existente})
    sus=suscripcion_actual(request.institucion);usados=Inscripcion.objects.filter(institucion=request.institucion,ciclo=destino,estado="ACTIVA").count()
    return {"destino":destino,"origen":origen,"filas":filas,"elegibles":sum(1 for x in filas if x["grado"]),"egresados":sum(1 for x in filas if not x["grado"]),"ya_inscritos":sum(1 for x in filas if x["existente"]),"suscripcion":sus,"usados":usados}

@gestion_alumnos_required
def reinscripciones_detalle(request,ciclo_destino):
    destino=get_object_or_404(CicloEscolar,institucion=request.institucion,pk=ciclo_destino,cerrado=False)
    return render(request,"alumnos/reinscripciones.html",_reinscripciones_contexto(request,destino))

@gestion_alumnos_required
@require_POST
def reinscripciones_procesar(request,ciclo_destino):
    destino=get_object_or_404(CicloEscolar,institucion=request.institucion,pk=ciclo_destino,cerrado=False)
    asignaciones=[]
    for rid in request.POST.getlist("resultado"):
        resultado=get_object_or_404(ResultadoAnualAlumno,institucion=request.institucion,pk=rid)
        seccion=get_object_or_404(Seccion,institucion=request.institucion,ciclo=destino,pk=request.POST.get(f"seccion_{rid}"))
        asignaciones.append((resultado,destino,seccion))
    try: procesadas=reinscripcion_masiva(asignaciones=asignaciones)
    except ValidationError as exc: messages.error(request,"; ".join(exc.messages))
    else:
        creadas=sum(1 for _,creada in procesadas if creada);omitidas=len(procesadas)-creadas
        registrar_evento(request,"REINSCRIPCION_MASIVA",destino,{"ciclo_destino":destino.anio,"alumnos":creadas})
        messages.success(request,f"Reinscripción completada: {creadas} creadas, {omitidas} ya existentes.")
    return redirect("alumnos:reinscripciones_detalle",ciclo_destino=destino.pk)

@gestion_alumnos_required
def reinscripciones_inicio(request):
    ciclos=CicloEscolar.objects.filter(institucion=request.institucion).order_by("-anio")
    destino=get_object_or_404(ciclos,pk=request.GET["ciclo_destino"]) if request.GET.get("ciclo_destino") else ciclos.filter(estado=CicloEscolar.Estado.PLANIFICACION).first()
    if destino:return redirect("alumnos:reinscripciones_detalle",ciclo_destino=destino.pk)
    return render(request,"alumnos/reinscripciones_inicio.html",{"ciclos":ciclos})

def _reinscripciones_contexto(request,destino):
    origen=CicloEscolar.objects.filter(institucion=request.institucion,anio__lt=destino.anio,cerrado=True).order_by("-anio").first()
    resultados=ResultadoAnualAlumno.objects.none() if not origen else origen.resultados_anuales.select_related("alumno","inscripcion__grado","inscripcion__seccion").filter(resultado_final__in=("PROMOVIDO","NO_PROMOVIDO","EGRESADO"))
    filas=[]
    for r in resultados:
        orden=r.inscripcion.grado.orden+(1 if r.resultado_final=="PROMOVIDO" else 0)
        grado=destino.grados.filter(orden=orden).first() if r.resultado_final!="EGRESADO" else None
        existente=Inscripcion.objects.filter(alumno=r.alumno,ciclo=destino,estado="ACTIVA").first()
        filas.append({"resultado":r,"grado":grado,"secciones":destino.secciones.filter(grado=grado,activa=True).annotate(ocupados=Count("inscripciones",filter=Q(inscripciones__estado="ACTIVA"))) if grado else [],"existente":existente})
    sus=suscripcion_actual(request.institucion);usados=Inscripcion.objects.filter(institucion=request.institucion,ciclo=destino,estado="ACTIVA").count()
    return {"destino":destino,"origen":origen,"filas":filas,"elegibles":sum(1 for x in filas if x["grado"]),"egresados":sum(1 for x in filas if not x["grado"]),"ya_inscritos":sum(1 for x in filas if x["existente"]),"suscripcion":sus,"usados":usados}

@gestion_alumnos_required
def reinscripciones_detalle(request,ciclo_destino):
    destino=get_object_or_404(CicloEscolar,institucion=request.institucion,pk=ciclo_destino,cerrado=False)
    return render(request,"alumnos/reinscripciones.html",_reinscripciones_contexto(request,destino))

@gestion_alumnos_required
@require_POST
def reinscripciones_procesar(request,ciclo_destino):
    destino=get_object_or_404(CicloEscolar,institucion=request.institucion,pk=ciclo_destino,cerrado=False)
    asignaciones=[]
    for rid in request.POST.getlist("resultado"):
        resultado=get_object_or_404(ResultadoAnualAlumno,institucion=request.institucion,pk=rid)
        seccion=get_object_or_404(Seccion,institucion=request.institucion,ciclo=destino,pk=request.POST.get(f"seccion_{rid}"))
        asignaciones.append((resultado,destino,seccion))
    try: procesadas=reinscripcion_masiva(asignaciones=asignaciones)
    except ValidationError as exc: messages.error(request,"; ".join(exc.messages))
    else:
        creadas=sum(1 for _,creada in procesadas if creada);omitidas=len(procesadas)-creadas
        registrar_evento(request,"REINSCRIPCION_MASIVA",destino,{"ciclo_destino":destino.anio,"alumnos":creadas})
        messages.success(request,f"Reinscripción completada: {creadas} creadas, {omitidas} ya existentes.")
    return redirect("alumnos:reinscripciones_detalle",ciclo_destino=destino.pk)

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
