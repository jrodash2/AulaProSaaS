from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count,Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from auditoria.services import registrar_evento
from .forms import AdjuntoForm,ComunicacionForm,DestinoForm
from .models import AdjuntoComunicacion,Comunicacion,ComunicacionAudiencia,Notificacion
from .services import anular,comunicaciones_visibles,puede_gestionar,puede_crear,publicar,sincronizar_notificaciones

def _inst(request):
    if not request.user.is_authenticated or not request.institucion:raise PermissionDenied
@login_required
def notificaciones(request):
    _inst(request);qs=Notificacion.objects.filter(institucion=request.institucion,usuario=request.user)
    if request.GET.get("filtro")=="no-leidas":qs=qs.filter(leida=False)
    return render(request,"comunicaciones/notificaciones.html",{"notificaciones":qs})
@login_required
def abrir_notificacion(request,pk):
    _inst(request);n=get_object_or_404(Notificacion,institucion=request.institucion,usuario=request.user,pk=pk)
    if not n.leida:n.leida=True;n.fecha_lectura=timezone.now();n.save(update_fields=("leida","fecha_lectura"))
    return redirect(n.url_destino or "comunicaciones:notificaciones")
@login_required
@require_POST
def marcar_todas(request):
    _inst(request)
    if request.method!="POST":raise PermissionDenied
    Notificacion.objects.filter(institucion=request.institucion,usuario=request.user,leida=False).update(leida=True,fecha_lectura=timezone.now());return redirect("comunicaciones:notificaciones")
@login_required
def dashboard(request):
    _inst(request)
    if not puede_gestionar(request):return redirect("comunicaciones:avisos")
    qs=Comunicacion.objects.filter(institucion=request.institucion);publicadas=qs.filter(estado="PUBLICADA").count();programadas=qs.filter(estado="PROGRAMADA").count();urgentes=qs.filter(prioridad="URGENTE",estado="PUBLICADA").count();tot=Notificacion.objects.filter(institucion=request.institucion).count();leidas=Notificacion.objects.filter(institucion=request.institucion,leida=True).count()
    return render(request,"comunicaciones/dashboard.html",{"publicadas":publicadas,"programadas":programadas,"urgentes":urgentes,"lectura":round(leidas*100/tot,2) if tot else 0,"comunicaciones":qs[:8]})
@login_required
def lista(request):
    _inst(request)
    if not puede_gestionar(request):raise PermissionDenied
    qs=Comunicacion.objects.filter(institucion=request.institucion).annotate(total=Count("notificaciones"),leidas=Count("notificaciones",filter=Q(notificaciones__leida=True)))
    if request.GET.get("estado"):qs=qs.filter(estado=request.GET["estado"])
    return render(request,"comunicaciones/lista.html",{"comunicaciones":qs})
@login_required
def avisos(request):
    _inst(request);return render(request,"comunicaciones/avisos.html",{"comunicaciones":comunicaciones_visibles(request.user,request.institucion)})
@login_required
@transaction.atomic
def formulario(request,pk=None):
    _inst(request)
    if not puede_crear(request):raise PermissionDenied
    obj=get_object_or_404(Comunicacion,institucion=request.institucion,pk=pk) if pk else None
    if obj and not puede_gestionar(request) and obj.creada_por_id!=request.user.id:raise PermissionDenied
    form=ComunicacionForm(request.POST or None,instance=obj);destino=DestinoForm(request.POST or None,institucion=request.institucion,prefix="destino")
    if request.method=="POST" and form.is_valid() and destino.is_valid():
        com=form.save(commit=False);com.institucion=request.institucion;com.creada_por=com.creada_por or request.user;com.estado="BORRADOR";com.save();ComunicacionAudiencia.objects.filter(comunicacion=com).delete();ComunicacionAudiencia.objects.bulk_create([ComunicacionAudiencia(comunicacion=com,rol=r) for r in form.cleaned_data["audiencias"]]);d=destino.save(commit=False);d.institucion=request.institucion;d.comunicacion=com;d.save();registrar_evento(request,"EDITAR_COMUNICACION" if obj else "CREAR_COMUNICACION",com)
        if form.cleaned_data["publicar_ahora"]:publicar(request,com)
        messages.success(request,"Comunicación guardada correctamente.");return redirect("comunicaciones:detalle",pk=com.pk)
    return render(request,"comunicaciones/formulario.html",{"form":form,"destino":destino,"comunicacion":obj})
@login_required
def detalle(request,pk):
    _inst(request);com=get_object_or_404(Comunicacion,institucion=request.institucion,pk=pk)
    notificacion=Notificacion.objects.filter(comunicacion=com,usuario=request.user).first()
    es_autor=com.creada_por_id==request.user.id
    if not puede_gestionar(request) and not notificacion and not es_autor:raise PermissionDenied
    if not puede_gestionar(request) and not com.visible and not es_autor:raise PermissionDenied
    total=com.notificaciones.count();leidas=com.notificaciones.filter(leida=True).count()
    return render(request,"comunicaciones/detalle.html",{"comunicacion":com,"total":total,"leidas":leidas,"pendientes":total-leidas,"tasa":round(leidas*100/total,2) if total else 0})
@login_required
@require_POST
def publicar_view(request,pk):
    _inst(request)
    if request.method!="POST":raise PermissionDenied
    publicar(request,get_object_or_404(Comunicacion,institucion=request.institucion,pk=pk));messages.success(request,"Comunicación publicada y notificaciones sincronizadas.");return redirect("comunicaciones:detalle",pk=pk)
@login_required
def adjuntar(request,pk):
    _inst(request);com=get_object_or_404(Comunicacion,institucion=request.institucion,pk=pk)
    if not puede_gestionar(request) and com.creada_por_id!=request.user.id:raise PermissionDenied
    form=AdjuntoForm(request.POST or None,request.FILES or None)
    if request.method=="POST" and form.is_valid():
        a=form.save(commit=False);a.institucion=request.institucion;a.comunicacion=com;a.nombre_original=a.archivo.name;a.save();registrar_evento(request,"AGREGAR_ADJUNTO_COMUNICACION",a);return redirect("comunicaciones:detalle",pk=pk)
    return render(request,"comunicaciones/adjunto.html",{"form":form,"comunicacion":com})
@login_required
def descargar(request,pk):
    _inst(request);a=get_object_or_404(AdjuntoComunicacion,institucion=request.institucion,pk=pk)
    if not puede_gestionar(request) and not a.comunicacion.notificaciones.filter(usuario=request.user).exists():raise PermissionDenied
    return FileResponse(a.archivo.open("rb"),as_attachment=True,filename=a.nombre_original)
@login_required
def reportes(request):
    _inst(request)
    if not puede_gestionar(request):raise PermissionDenied
    qs=Comunicacion.objects.filter(institucion=request.institucion).annotate(total=Count("notificaciones"),leidas=Count("notificaciones",filter=Q(notificaciones__leida=True)),pendientes=Count("notificaciones",filter=Q(notificaciones__leida=False)))
    return render(request,"comunicaciones/reportes.html",{"comunicaciones":qs})

@login_required
@require_POST
def cambiar_estado(request,pk,estado):
    _inst(request)
    if request.method!="POST" or not puede_gestionar(request):raise PermissionDenied
    com=get_object_or_404(Comunicacion,institucion=request.institucion,pk=pk)
    if estado=="ANULADA":anular(request,com,request.POST.get("motivo", ""))
    elif estado=="ARCHIVADA":
        com.estado="ARCHIVADA";com.save();registrar_evento(request,"ARCHIVAR_COMUNICACION",com)
    else:raise PermissionDenied
    return redirect("comunicaciones:detalle",pk=pk)
