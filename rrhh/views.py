from datetime import date
from pathlib import Path
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from django.utils import timezone
from core.decorators import institucion_required
from suscripciones.services import modulo_habilitado
from auditoria.services import registrar_evento
from .forms import *
from .models import *
from .services import *
def acceso(r):
 if not modulo_habilitado(r.institucion,"RRHH") or r.asignacion_institucion.rol in {"PADRE","ALUMNO"}:raise PermissionDenied
@institucion_required
def dashboard(r):
 acceso(r)
 if rol(r) not in ADMIN|{"SECRETARIA","CONTABILIDAD"}:return redirect("rrhh:mi_perfil")
 return render(r,"rrhh/dashboard.html",{"activos":Empleado.objects.filter(institucion=r.institucion,estado=Empleado.Estado.ACTIVO).count(),"contratos":contratos_por_vencer(r.institucion).count(),"documentos":sum(resumen_expediente(e)["pendientes"] for e in Empleado.objects.filter(institucion=r.institucion,estado=Empleado.Estado.ACTIVO)),"permisos":PermisoLaboral.objects.filter(institucion=r.institucion,estado=PermisoLaboral.Estado.PENDIENTE).count()})
@institucion_required
def empleados(r):
 acceso(r);q=empleados_visibles(r)
 if r.GET.get("estado"):q=q.filter(estado=r.GET["estado"])
 if r.GET.get("area"):q=q.filter(area_id=r.GET["area"])
 if r.GET.get("q"):
  from django.db.models import Q
  x=r.GET["q"];q=q.filter(Q(nombres__icontains=x)|Q(apellidos__icontains=x)|Q(codigo_empleado__icontains=x)|Q(cui__icontains=x)|Q(dpi__icontains=x)|Q(correo__icontains=x))
 return render(r,"rrhh/empleados.html",{"items":q,"areas":AreaLaboral.objects.filter(institucion=r.institucion),"estados":Empleado.Estado.choices})
@institucion_required
def empleado_form(r,pk=None):
 acceso(r)
 if not puede_gestionar(r) and rol(r)!="SECRETARIA":raise PermissionDenied
 obj=get_object_or_404(Empleado,institucion=r.institucion,pk=pk) if pk else None;form=EmpleadoForm(r.POST or None,r.FILES or None,instance=obj,institucion=r.institucion)
 if r.method=="POST" and form.is_valid():e=form.save(commit=False);e.institucion=r.institucion;e.creado_por=e.creado_por or r.user;e.save();registrar_evento(r,"EDITAR_EMPLEADO" if obj else "CREAR_EMPLEADO",e);return redirect("rrhh:empleado",pk=e.pk)
 return render(r,"rrhh/form.html",{"form":form,"titulo":"Editar empleado" if obj else "Nuevo empleado","multipart":True})
@institucion_required
def empleado(r,pk):
 acceso(r);e=get_object_or_404(empleados_visibles(r),pk=pk);return render(r,"rrhh/empleado.html",{"empleado":e,"expediente":resumen_expediente(e),"ver_salario":puede_ver_salario(r),"puede_gestionar":puede_gestionar(r),"contrato_form":ContratoForm(institucion=r.institucion,ver_salario=puede_ver_salario(r)),"permiso_form":PermisoForm(),"documento_form":DocumentoForm(institucion=r.institucion)})
@institucion_required
@require_POST
def contrato_crear(r,pk):
 acceso(r);e=get_object_or_404(Empleado,institucion=r.institucion,pk=pk)
 if not puede_gestionar(r):raise PermissionDenied
 f=ContratoForm(r.POST,r.FILES,institucion=r.institucion,ver_salario=puede_ver_salario(r))
 if f.is_valid():c=f.save(commit=False);c.institucion=r.institucion;c.empleado=e;c.creado_por=r.user;c.save();registrar_evento(r,"CREAR_CONTRATO",c)
 return redirect("rrhh:empleado",pk=pk)
@institucion_required
@require_POST
def contrato_finalizar(r,pk):
 acceso(r);c=get_object_or_404(ContratoLaboral,institucion=r.institucion,pk=pk)
 if not puede_gestionar(r):raise PermissionDenied
 c.estado=ContratoLaboral.Estado.FINALIZADO;c.fecha_fin=r.POST.get("fecha") or timezone.localdate();c.motivo_finalizacion=r.POST.get("motivo","");c.save();registrar_evento(r,"FINALIZAR_CONTRATO",c);return redirect("rrhh:empleado",pk=c.empleado_id)
@institucion_required
@require_POST
def permiso_crear(r,pk):
 acceso(r);e=get_object_or_404(empleados_visibles(r),pk=pk)
 if e.usuario_id != r.user.id and not (puede_gestionar(r) or rol(r)=="SECRETARIA"):raise PermissionDenied
 f=PermisoForm(r.POST)
 if f.is_valid():p=f.save(commit=False);p.institucion=r.institucion;p.empleado=e;p.solicitado_por=r.user;p.save();registrar_evento(r,"SOLICITAR_PERMISO",p)
 return redirect("rrhh:empleado",pk=pk)
@institucion_required
@require_POST
def permiso_resolver(r,pk):
 acceso(r);p=get_object_or_404(PermisoLaboral,institucion=r.institucion,pk=pk);resolver_permiso(r,p,r.POST.get("estado"));registrar_evento(r,"APROBAR_PERMISO" if p.estado=="APROBADO" else "RECHAZAR_PERMISO",p);return redirect("rrhh:empleado",pk=p.empleado_id)
@institucion_required
@require_POST
def documento_subir(r,pk):
 acceso(r)
 if not puede_gestionar(r):raise PermissionDenied
 e=get_object_or_404(Empleado,institucion=r.institucion,pk=pk);f=DocumentoForm(r.POST,r.FILES,institucion=r.institucion)
 if f.is_valid():d=f.save(commit=False);d.institucion=r.institucion;d.empleado=e;d.nombre_original=Path(d.archivo.name).name;d.cargado_por=r.user;d.save();registrar_evento(r,"SUBIR_DOCUMENTO_EMPLEADO",d)
 return redirect("rrhh:empleado",pk=pk)
@institucion_required
def documento_descargar(r,pk):
 acceso(r)
 visibles=empleados_visibles(r)
 if not puede_gestionar(r):visibles=visibles.filter(usuario=r.user)
 d=get_object_or_404(DocumentoEmpleado.objects.filter(institucion=r.institucion,empleado__in=visibles),pk=pk);return FileResponse(d.archivo.open("rb"),as_attachment=True,filename=Path(d.nombre_original).name)
@institucion_required
@require_POST
def empleado_cambiar_puesto(r,pk):
 acceso(r)
 if not puede_gestionar(r):raise PermissionDenied
 e=get_object_or_404(Empleado,institucion=r.institucion,pk=pk);puesto=get_object_or_404(PuestoLaboral,institucion=r.institucion,pk=r.POST.get("puesto"))
 movimiento=cambiar_puesto(e,puesto,puesto.area,date.fromisoformat(r.POST["fecha"]),r.POST.get("motivo","").strip() or "Cambio administrativo",r.user);registrar_evento(r,"CAMBIAR_PUESTO",movimiento);return redirect("rrhh:empleado",pk=pk)
@institucion_required
@require_POST
def empleado_egreso(r,pk):
 acceso(r)
 if not puede_gestionar(r):raise PermissionDenied
 e=get_object_or_404(Empleado,institucion=r.institucion,pk=pk);movimiento=registrar_egreso(e,date.fromisoformat(r.POST["fecha"]),r.POST.get("motivo","").strip() or "Egreso registrado",r.user,r.POST.get("desactivar_usuario")=="on");registrar_evento(r,"REGISTRAR_EGRESO",movimiento);return redirect("rrhh:empleado",pk=pk)
@institucion_required
def catalogos(r,tipo):
 acceso(r)
 if rol(r) not in ADMIN:raise PermissionDenied
 modelo,formulario=(AreaLaboral,AreaForm) if tipo=="areas" else (PuestoLaboral,PuestoForm);obj=None;form=formulario(r.POST or None,**({"institucion":r.institucion} if tipo!="areas" else {}))
 if r.method=="POST" and form.is_valid():obj=form.save(commit=False);obj.institucion=r.institucion;obj.save();registrar_evento(r,"CREAR_AREA_LABORAL" if tipo=="areas" else "CREAR_PUESTO_LABORAL",obj);return redirect("rrhh:catalogos",tipo=tipo)
 return render(r,"rrhh/catalogos.html",{"titulo":"Áreas laborales" if tipo=="areas" else "Puestos laborales","items":modelo.objects.filter(institucion=r.institucion),"form":form})
@institucion_required
def mi_perfil(r):
 acceso(r);e=get_object_or_404(Empleado,institucion=r.institucion,usuario=r.user);return render(r,"rrhh/mi_perfil.html",{"empleado":e,"expediente":resumen_expediente(e),"permiso_form":PermisoForm()})
