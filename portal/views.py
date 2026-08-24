from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from alumnos.models import Alumno, Encargado
from asistencia.models import RegistroAsistencia
from calificaciones.models import Calificacion
from cuentas.models import Usuario
from finanzas.models import Cargo,Pago
from instituciones.models import UsuarioInstitucion
from tareas.models import AdjuntoEntrega,AdjuntoTarea,EntregaTarea,Tarea
from .forms import AccesoPortalForm,EntregaForm
from .permissions import alumnos_permitidos,get_alumno_portal,portal_role_required,rol_portal
from .services import resumen_alumno

@portal_role_required("PADRE","ALUMNO")
def dashboard(request):
    alumnos=list(alumnos_permitidos(request))
    from comunicaciones.models import Notificacion
    avisos=Notificacion.objects.filter(institucion=request.institucion,usuario=request.user,tipo_origen="COMUNICACION")[:3]
    if rol_portal(request)=="ALUMNO":
        if not alumnos: raise PermissionDenied
        context=resumen_alumno(alumnos[0]);context["avisos_recientes"]=avisos
        return render(request,"portal/alumno_dashboard.html",context)
    return render(request,"portal/padre_dashboard.html",{"estudiantes":[resumen_alumno(a) for a in alumnos],"avisos_recientes":avisos})

@portal_role_required("PADRE")
def seleccionar(request,pk):
    alumno=get_alumno_portal(request,pk);request.session["portal_alumno_id"]=alumno.pk
    return redirect("portal:estudiante",pk=alumno.pk)

@portal_role_required("PADRE","ALUMNO")
def estudiante(request,pk): return render(request,"portal/estudiante.html",resumen_alumno(get_alumno_portal(request,pk)))

@portal_role_required("PADRE","ALUMNO")
def asistencia(request,pk):
    alumno=get_alumno_portal(request,pk);registros=RegistroAsistencia.objects.filter(alumno=alumno).exclude(sesion__estado="ANULADA").select_related("sesion").order_by("-sesion__fecha")
    return render(request,"portal/asistencia.html",{"alumno":alumno,"registros":registros})

@portal_role_required("PADRE","ALUMNO")
def calificaciones(request,pk):
    alumno=get_alumno_portal(request,pk);notas=Calificacion.objects.filter(alumno=alumno,actividad__activa=True).select_related("actividad__curso","actividad__periodo")
    return render(request,"portal/calificaciones.html",{"alumno":alumno,"notas":notas})

@portal_role_required("PADRE","ALUMNO")
def tareas(request,pk):
    alumno=get_alumno_portal(request,pk);ins=alumno.inscripciones.filter(estado="ACTIVA").first();qs=Tarea.objects.none()
    if ins: qs=Tarea.objects.filter(institucion=request.institucion,seccion=ins.seccion,estado__in=("PUBLICADA","CERRADA"),activa=True).prefetch_related("entregas")
    return render(request,"portal/tareas.html",{"alumno":alumno,"tareas":qs})

@portal_role_required("PADRE","ALUMNO")
def tarea_detalle(request,pk,tarea_pk):
    alumno=get_alumno_portal(request,pk);tarea=get_object_or_404(Tarea,institucion=request.institucion,pk=tarea_pk,estado__in=("PUBLICADA","CERRADA"),entregas__alumno=alumno)
    entrega=get_object_or_404(EntregaTarea,tarea=tarea,alumno=alumno);form=EntregaForm(request.POST or None,request.FILES or None)
    if request.method=="POST":
        if not tarea.permite_entrega_archivo or tarea.estado!="PUBLICADA": raise PermissionDenied
        if form.is_valid():
            archivo=form.cleaned_data["archivo"]
            with transaction.atomic():
                AdjuntoEntrega.objects.create(institucion=request.institucion,entrega=entrega,archivo=archivo,nombre_original=archivo.name)
                entrega.comentario=form.cleaned_data["comentario"];entrega.fecha_entrega=timezone.now();entrega.entregada_por=request.user;entrega.estado="ENTREGADA_TARDE" if entrega.fecha_entrega>tarea.fecha_limite else "ENTREGADA";entrega.save()
            messages.success(request,"Entrega registrada correctamente.");return redirect("portal:tarea",pk=alumno.pk,tarea_pk=tarea.pk)
    return render(request,"portal/tarea.html",{"alumno":alumno,"tarea":tarea,"entrega":entrega,"form":form})

@portal_role_required("PADRE")
def finanzas(request,pk):
    alumno=get_alumno_portal(request,pk);cargos=Cargo.objects.filter(alumno=alumno).exclude(estado="ANULADO");return render(request,"portal/finanzas.html",{"alumno":alumno,"cargos":cargos})

@portal_role_required("PADRE")
def recibos(request,pk):
    alumno=get_alumno_portal(request,pk);pagos=Pago.objects.filter(institucion=request.institucion,estado="CONFIRMADO",alumno=alumno);return render(request,"portal/recibos.html",{"alumno":alumno,"pagos":pagos})

@portal_role_required("PADRE")
def recibo(request,pk,pago_pk):
    alumno=get_alumno_portal(request,pk);pago=get_object_or_404(Pago,institucion=request.institucion,alumno=alumno,pk=pago_pk,estado="CONFIRMADO");return render(request,"portal/recibo.html",{"alumno":alumno,"pago":pago})

@portal_role_required("PADRE","ALUMNO")
def descargar_tarea(request,pk,adjunto_pk):
    alumno=get_alumno_portal(request,pk);adj=get_object_or_404(AdjuntoTarea,pk=adjunto_pk,institucion=request.institucion,tarea__entregas__alumno=alumno,tarea__estado__in=("PUBLICADA","CERRADA"));return FileResponse(adj.archivo.open("rb"),as_attachment=True,filename=adj.nombre_original)

@portal_role_required("PADRE","ALUMNO")
def descargar_entrega(request,pk,adjunto_pk):
    alumno=get_alumno_portal(request,pk);adj=get_object_or_404(AdjuntoEntrega,pk=adjunto_pk,institucion=request.institucion,entrega__alumno=alumno);return FileResponse(adj.archivo.open("rb"),as_attachment=True,filename=adj.nombre_original)

def _puede_gestionar(request):
    return request.user.is_authenticated and request.institucion and rol_portal(request) in {"PROPIETARIO","DIRECTOR","ADMINISTRADOR"}

@transaction.atomic
def _crear_acceso(request,obj,rol):
    if not _puede_gestionar(request): raise PermissionDenied
    form=AccesoPortalForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        user=Usuario(username=form.cleaned_data["username"],email=form.cleaned_data["email"]);user.set_password(form.cleaned_data["password"]);user.save();UsuarioInstitucion.objects.create(usuario=user,institucion=request.institucion,rol=rol);obj.usuario=user;obj.save();messages.success(request,"Acceso al portal creado de forma segura.");return None,user
    return form,None

def acceso_encargado(request,pk):
    obj=get_object_or_404(Encargado,institucion=request.institucion,pk=pk);form,user=_crear_acceso(request,obj,"PADRE")
    if user:return redirect("alumnos:encargado_detalle",pk=obj.pk)
    return render(request,"portal/acceso_form.html",{"form":form,"persona":obj,"tipo":"padre / encargado"})

def acceso_alumno(request,pk):
    obj=get_object_or_404(Alumno,institucion=request.institucion,pk=pk);form,user=_crear_acceso(request,obj,"ALUMNO")
    if user:return redirect("alumnos:detalle",pk=obj.pk)
    return render(request,"portal/acceso_form.html",{"form":form,"persona":obj,"tipo":"alumno"})

def revocar_acceso(request,tipo,pk):
    if not _puede_gestionar(request) or request.method!="POST": raise PermissionDenied
    model=Encargado if tipo=="encargado" else Alumno;obj=get_object_or_404(model,institucion=request.institucion,pk=pk)
    if obj.usuario_id: UsuarioInstitucion.objects.filter(usuario=obj.usuario,institucion=request.institucion).update(activo=False);obj.usuario.is_active=False;obj.usuario.save(update_fields=("is_active",))
    messages.success(request,"Acceso desactivado sin eliminar su historial.");return redirect("alumnos:encargado_detalle" if tipo=="encargado" else "alumnos:detalle",pk=obj.pk)
