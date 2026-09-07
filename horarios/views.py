from django.contrib import messages
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from auditoria.services import registrar_evento
from core.decorators import institucion_required
from docentes.models import Docente
from portal.permissions import get_alumno_portal,portal_role_required
from suscripciones.services import modulo_habilitado
from academico.models import CicloEscolar,Seccion
from .forms import AulaForm,BloqueHorarioForm,GenerarBloquesForm,HorarioClaseForm
from .models import Aula,BloqueHorario,HorarioClase
from .services import horario_docente,horario_seccion,matriz_semanal,validar_carga_semanal

GESTION={"PROPIETARIO","DIRECTOR","ADMINISTRADOR","SECRETARIA"}
def acceso(request,gestion=False):
 if not modulo_habilitado(request.institucion,"HORARIOS"):raise PermissionDenied
 rol=request.asignacion_institucion.rol
 if gestion and rol not in GESTION:raise PermissionDenied
 if not gestion and rol not in GESTION|{"DOCENTE"}:raise PermissionDenied
def ciclo(request):return CicloEscolar.objects.filter(institucion=request.institucion,pk=request.GET.get("ciclo")).first() or CicloEscolar.objects.filter(institucion=request.institucion,es_actual=True).first()
@institucion_required
def dashboard(request):
 acceso(request);c=ciclo(request);secciones=Seccion.objects.filter(institucion=request.institucion,ciclo=c,activa=True);con=secciones.filter(horarios_clase__activo=True).distinct().count();return render(request,"horarios/dashboard.html",{"ciclo":c,"secciones":secciones.count(),"con_horario":con,"pendientes":secciones.count()-con,"docentes":Docente.objects.filter(institucion=request.institucion,asignaciones__horarios_clase__activo=True).distinct().count()})
@institucion_required
def aulas(request):acceso(request);return render(request,"horarios/aulas.html",{"items":Aula.objects.filter(institucion=request.institucion)})
@institucion_required
def aula_form(request,pk=None):
 acceso(request,True);obj=get_object_or_404(Aula,institucion=request.institucion,pk=pk) if pk else None;form=AulaForm(request.POST or None,instance=obj)
 if request.method=="POST" and form.is_valid():item=form.save(commit=False);item.institucion=request.institucion;item.save();registrar_evento(request,"EDITAR_AULA" if obj else "CREAR_AULA",item);return redirect("horarios:aulas")
 return render(request,"horarios/formulario.html",{"form":form,"titulo":"Editar aula" if obj else "Nueva aula"})
@institucion_required
def bloques(request):acceso(request);return render(request,"horarios/bloques.html",{"items":BloqueHorario.objects.filter(institucion=request.institucion).select_related("jornada")})
@institucion_required
def bloque_form(request,pk=None):
 acceso(request,True);obj=get_object_or_404(BloqueHorario,institucion=request.institucion,pk=pk) if pk else None;form=BloqueHorarioForm(request.POST or None,instance=obj,institucion=request.institucion)
 if request.method=="POST" and form.is_valid():item=form.save(commit=False);item.institucion=request.institucion;item.save();registrar_evento(request,"EDITAR_BLOQUE_HORARIO" if obj else "CREAR_BLOQUE_HORARIO",item);return redirect("horarios:bloques")
 return render(request,"horarios/formulario.html",{"form":form,"titulo":"Editar bloque" if obj else "Nuevo bloque"})
@institucion_required
def generar_bloques(request):
 acceso(request,True);form=GenerarBloquesForm(request.POST or None,institucion=request.institucion)
 if request.method=="POST" and form.is_valid():
  with transaction.atomic():
   for nombre,orden,inicio,fin,tipo in form.bloques():BloqueHorario.objects.create(institucion=request.institucion,jornada=form.cleaned_data["jornada"],nombre=nombre,orden=orden,hora_inicio=inicio,hora_fin=fin,tipo=tipo)
  messages.success(request,"Bloques generados correctamente.");return redirect("horarios:bloques")
 return render(request,"horarios/formulario.html",{"form":form,"titulo":"Generar bloques"})
@institucion_required
def secciones(request):acceso(request);c=ciclo(request);return render(request,"horarios/secciones.html",{"ciclo":c,"items":Seccion.objects.filter(institucion=request.institucion,ciclo=c,activa=True).select_related("grado","jornada") if c else []})
def contexto_semana(seccion,editable=False):
 items=horario_seccion(seccion);bloques=BloqueHorario.objects.filter(institucion=seccion.institucion,jornada=seccion.jornada,activo=True);matriz,dias=matriz_semanal(items,bloques);return {"seccion":seccion,"matriz":matriz,"dias":dias,"carga":validar_carga_semanal(seccion),"editable":editable}
@institucion_required
def seccion_horario(request,pk):
 acceso(request);s=get_object_or_404(Seccion,institucion=request.institucion,pk=pk);return render(request,"horarios/semana.html",contexto_semana(s,request.asignacion_institucion.rol in GESTION and not s.ciclo.cerrado))
@institucion_required
def clase_form(request,pk=None):
 acceso(request,True);obj=get_object_or_404(HorarioClase,institucion=request.institucion,pk=pk) if pk else None;initial={k:request.GET.get(k) for k in ("ciclo","jornada","seccion","dia_semana","bloque") if request.GET.get(k)};form=HorarioClaseForm(request.POST or None,instance=obj,initial=initial,institucion=request.institucion);form.instance.institucion=request.institucion
 if request.method=="POST" and form.is_valid():item=form.save();registrar_evento(request,"EDITAR_HORARIO_CLASE" if obj else "CREAR_HORARIO_CLASE",item);return redirect("horarios:seccion",pk=item.seccion_id)
 return render(request,"horarios/formulario.html",{"form":form,"titulo":"Editar clase" if obj else "Asignar clase"})
@institucion_required
@require_POST
def clase_estado(request,pk):
 acceso(request,True);item=get_object_or_404(HorarioClase,institucion=request.institucion,pk=pk);item.activo=not item.activo;item.save();registrar_evento(request,"DESACTIVAR_HORARIO_CLASE",item);return redirect("horarios:seccion",pk=item.seccion_id)
@institucion_required
def mi_horario(request):
 acceso(request);doc=get_object_or_404(Docente,institucion=request.institucion,usuario=request.user);items=horario_docente(doc);return render(request,"horarios/docente.html",{"docente":doc,"items":items,"total":items.count()})
@portal_role_required("PADRE","ALUMNO")
def portal_horario(request,alumno_pk):
 if not modulo_habilitado(request.institucion,"HORARIOS"):raise PermissionDenied
 alumno=get_alumno_portal(request,alumno_pk);ins=alumno.inscripciones.filter(estado="ACTIVA").select_related("seccion").first();return render(request,"horarios/portal.html",{"alumno":alumno,**(contexto_semana(ins.seccion) if ins else {})})
@institucion_required
def exportar(request,pk):
 acceso(request);s=get_object_or_404(Seccion,institucion=request.institucion,pk=pk);wb=Workbook();ws=wb.active;ws.append(["Día","Inicio","Fin","Curso","Docente","Grado","Sección","Aula"])
 for h in horario_seccion(s):ws.append([h.get_dia_semana_display(),h.bloque.hora_inicio,h.bloque.hora_fin,h.curso.nombre,h.docente.nombre_completo,h.grado.nombre,h.seccion.nombre,str(h.aula or "")])
 from io import BytesIO
 out=BytesIO();wb.save(out);out.seek(0);return FileResponse(out,as_attachment=True,filename=f"horario-{s.pk}.xlsx")
