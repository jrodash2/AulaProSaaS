from pathlib import Path
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import PermissionDenied,ValidationError
from django.http import FileResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from core.decorators import institucion_required
from instituciones.models import Institucion
from suscripciones.services import modulo_habilitado
from auditoria.services import registrar_evento
from .forms import *
from .models import *
from .services import *
ROLES={"PROPIETARIO","DIRECTOR","ADMINISTRADOR","SECRETARIA"}
def acceso(r):
 if not modulo_habilitado(r.institucion,"ADMISIONES") or r.asignacion_institucion.rol not in ROLES:raise PermissionDenied
def qs(r):return SolicitudAdmision.objects.filter(institucion=r.institucion).select_related('aspirante','ciclo_solicitado','oferta_solicitada','grado_solicitado').prefetch_related('documentos','entrevistas','evaluaciones','aspirante__encargados')
@institucion_required
def dashboard(r):
 acceso(r);q=qs(r);total=q.exclude(estado="CANCELADA").count();ins=q.filter(estado="INSCRITA").count();return render(r,'admisiones/dashboard.html',{'metrics':{'Solicitudes':total,'Nuevas':q.filter(estado='NUEVA').count(),'En revisión':q.filter(estado='EN_REVISION').count(),'Documentación pendiente':q.filter(estado='DOCUMENTACION_PENDIENTE').count(),'Evaluación pendiente':q.filter(estado='EVALUACION_PENDIENTE').count(),'Aprobadas':q.filter(estado='APROBADA').count(),'Inscritas':ins},'conversion':round(ins*100/total,1) if total else 0})
@institucion_required
def solicitudes(r):
 acceso(r);q=qs(r)
 for k in ('estado','origen'):
  if r.GET.get(k):q=q.filter(**{k:r.GET[k]})
 if r.GET.get('buscar'):
  from django.db.models import Q
  x=r.GET['buscar'];q=q.filter(Q(numero_solicitud__icontains=x)|Q(aspirante__nombres__icontains=x)|Q(aspirante__apellidos__icontains=x)|Q(aspirante__cui__icontains=x)|Q(aspirante__encargados__telefono__icontains=x)|Q(aspirante__encargados__correo__icontains=x)).distinct()
 return render(r,'admisiones/solicitudes.html',{'items':q,'estados':SolicitudAdmision.Estado.choices})
@institucion_required
def detalle(r,pk):acceso(r);s=get_object_or_404(qs(r),pk=pk);return render(r,'admisiones/detalle.html',{'solicitud':s,'conversion_form':ConversionForm(solicitud=s),'entrevista_form':EntrevistaForm(),'evaluacion_form':EvaluacionForm(institucion=r.institucion)})
@institucion_required
@require_POST
def estado(r,pk):
 acceso(r);s=get_object_or_404(qs(r),pk=pk);nuevo=r.POST.get('estado');motivo=r.POST.get('motivo','')
 if nuevo=='APROBADA':aprobar(s)
 else:cambiar_estado(s,nuevo,motivo)
 registrar_evento(r,'CAMBIAR_ESTADO_ADMISION',s,{'estado':nuevo});return redirect('admisiones:detalle',pk=pk)
@institucion_required
@require_POST
def convertir(r,pk):
 acceso(r);s=get_object_or_404(qs(r),pk=pk);f=ConversionForm(r.POST,solicitud=s)
 if f.is_valid():alumno,ins=convertir_solicitud_a_alumno(s,f.cleaned_data['seccion'],r.user);registrar_evento(r,'CONVERTIR_ADMISION_ALUMNO',s,{'alumno':alumno.pk,'inscripcion':ins.pk});messages.success(r,'Aspirante convertido e inscrito correctamente.')
 return redirect('admisiones:detalle',pk=pk)
@institucion_required
@require_POST
def entrevista(r,pk):
 acceso(r);s=get_object_or_404(qs(r),pk=pk);f=EntrevistaForm(r.POST)
 if f.is_valid():o=f.save(commit=False);o.institucion=r.institucion;o.solicitud=s;o.save();registrar_evento(r,'PROGRAMAR_ENTREVISTA',o)
 return redirect('admisiones:detalle',pk=pk)
@institucion_required
@require_POST
def evaluacion(r,pk):
 acceso(r);s=get_object_or_404(qs(r),pk=pk);f=EvaluacionForm(r.POST,institucion=r.institucion)
 if f.is_valid():o=f.save(commit=False);o.institucion=r.institucion;o.solicitud=s;o.evaluado_por=r.user;o.save();registrar_evento(r,'REGISTRAR_EVALUACION',o)
 return redirect('admisiones:detalle',pk=pk)
def solicitar(r,codigo):
 inst=get_object_or_404(Institucion,codigo=codigo,activa=True);config=get_object_or_404(ConfiguracionAdmision,institucion=inst,admisiones_abiertas=True);f=PublicaForm(r.POST or None,institucion=inst)
 if r.method=='POST':
  key=f"adm:{inst.pk}:{r.META.get('REMOTE_ADDR','')}";intentos=cache.get(key,0)
  if intentos>=5:raise PermissionDenied
  cache.set(key,intentos+1,3600)
  if f.is_valid() and config.requiere_cui and not f.cleaned_data['cui']:f.add_error('cui','El CUI es obligatorio para esta institución.')
  elif f.is_valid():
   d=f.cleaned_data;dup=posibles_duplicados(inst,d['nombres'],d['apellidos'],d['fecha_nacimiento'],d['cui'],d['correo']);a=Aspirante.objects.create(institucion=inst,nombres=d['nombres'],apellidos=d['apellidos'],cui=d['cui'] or None,fecha_nacimiento=d['fecha_nacimiento'],correo=d['correo'],estado='EN_PROCESO',posible_duplicado=dup);EncargadoAspirante.objects.create(institucion=inst,aspirante=a,nombres=d['encargado_nombres'],apellidos=d['encargado_apellidos'],telefono=d['telefono'],correo=d['correo']);s=SolicitudAdmision.objects.create(institucion=inst,aspirante=a,ciclo_solicitado=d['ciclo'],oferta_solicitada=d['oferta'],grado_solicitado=d['grado'],origen='PAGINA_WEB',observaciones=d['observaciones']);return render(r,'admisiones/confirmacion.html',{'numero':s.numero_solicitud,'token':s.token})
 return render(r,'admisiones/publica.html',{'institucion':inst,'config':config,'form':f})
def portal(r,token):
 s=get_object_or_404(SolicitudAdmision.objects.select_related('institucion','aspirante'),token=token);return render(r,'admisiones/portal.html',{'solicitud':s,'config':getattr(s.institucion,'configuracion_admision',None)})
@require_POST
def documento_publico(r,token):
 s=get_object_or_404(SolicitudAdmision,token=token);config=get_object_or_404(ConfiguracionAdmision,institucion=s.institucion,admisiones_abiertas=True,permitir_carga_documentos=True);tipo=get_object_or_404(TipoDocumentoAdmision,institucion=s.institucion,pk=r.POST.get('tipo'),activo=True);f=r.FILES.get('archivo')
 if f:DocumentoAdmision.objects.create(institucion=s.institucion,solicitud=s,tipo=tipo,archivo=f,nombre_original=Path(f.name).name)
 return redirect('admisiones:portal',token=token)
