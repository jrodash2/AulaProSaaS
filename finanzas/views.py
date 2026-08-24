from io import BytesIO
from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import PermissionDenied,ValidationError
from django.db.models import Q,Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from alumnos.models import Alumno,Familia
from auditoria.services import registrar_evento
from core.decorators import institucion_required
from .forms import CargoForm,ConceptoForm,ConfiguracionForm,GenerarForm,PagoForm
from .models import Cargo,ConceptoCobro,ConfiguracionFinanciera,Pago
from .services import GESTION,LECTURA,anular_pago,config,crear_cargo,exigir_gestion,exigir_lectura,generar_cargos_mensuales,registrar_pago,rol

def cargos_q(r):return Cargo.objects.filter(institucion=r.institucion).select_related("alumno","familia","concepto","ciclo","inscripcion__grado","inscripcion__seccion")
def pagos_q(r):return Pago.objects.filter(institucion=r.institucion).select_related("alumno","familia","metodo_pago","registrado_por")
def moneda(v):return f"Q {v:,.2f}"
@institucion_required
def dashboard(r):
 exigir_lectura(r);h=timezone.localdate();ps=pagos_q(r).filter(estado="CONFIRMADO",fecha_pago__year=h.year,fecha_pago__month=h.month);cs=list(cargos_q(r).exclude(estado="ANULADO"));return render(r,"finanzas/dashboard.html",{"ingresos":ps.aggregate(x=Sum("monto"))["x"] or 0,"pendiente":sum((x.saldo for x in cs),Decimal("0")),"vencidos":sum(1 for x in cs if x.vencido),"pagos_hoy":pagos_q(r).filter(estado="CONFIRMADO",fecha_pago__date=h).count()})
@institucion_required
def configuracion(r):
 if rol(r) not in GESTION:raise PermissionDenied
 obj=config(r.institucion);f=ConfiguracionForm(r.POST or None,instance=obj)
 if r.method=="POST" and f.is_valid():f.save();registrar_evento(r,"CONFIGURAR_FINANZAS",obj);messages.success(r,"Configuración guardada.");return redirect("finanzas:configuracion")
 return render(r,"finanzas/form.html",{"form":f,"titulo":"Configuración financiera"})
@institucion_required
def conceptos(r):
 exigir_lectura(r);return render(r,"finanzas/conceptos.html",{"conceptos":ConceptoCobro.objects.filter(institucion=r.institucion)})
@institucion_required
def concepto_form(r):
 if rol(r) not in GESTION:raise PermissionDenied
 f=ConceptoForm(r.POST or None)
 if r.method=="POST" and f.is_valid():x=f.save(commit=False);x.institucion=r.institucion;x.save();registrar_evento(r,"CREAR_CONCEPTO_COBRO",x);return redirect("finanzas:conceptos")
 return render(r,"finanzas/form.html",{"form":f,"titulo":"Nuevo concepto"})
@institucion_required
def cargos(r):
 exigir_lectura(r);q=cargos_q(r)
 if r.GET.get("q"):q=q.filter(Q(alumno__primer_nombre__icontains=r.GET["q"])|Q(alumno__primer_apellido__icontains=r.GET["q"])|Q(concepto__nombre__icontains=r.GET["q"]))
 if r.GET.get("estado"):q=q.filter(estado=r.GET["estado"])
 if r.GET.get("concepto"):q=q.filter(concepto_id=r.GET["concepto"])
 if r.GET.get("vencidos"):q=[x for x in q if x.vencido]
 return render(r,"finanzas/cargos.html",{"cargos":q,"estados":Cargo.Estado.choices,"conceptos":ConceptoCobro.objects.filter(institucion=r.institucion)})
@institucion_required
def cargo_form(r):
 if rol(r) not in GESTION:raise PermissionDenied
 f=CargoForm(r.POST or None,request=r)
 if r.method=="POST" and f.is_valid():
  try:x=crear_cargo(r,**f.cleaned_data);messages.success(r,"Cargo creado.");return redirect("finanzas:alumno",x.alumno_id)
  except (ValidationError,PermissionDenied) as e:f.add_error(None,e)
 return render(r,"finanzas/form.html",{"form":f,"titulo":"Agregar cargo"})
@institucion_required
def generar(r):
 if rol(r) not in GESTION:raise PermissionDenied
 f=GenerarForm(r.POST or None,institucion=r.institucion)
 if r.method=="POST" and f.is_valid():
  try:c,e=generar_cargos_mensuales(r,**f.cleaned_data);messages.success(r,f"Se crearon {c} cargos; {e} ya existían.");return redirect("finanzas:cargos")
  except ValidationError as x:f.add_error(None,x)
 return render(r,"finanzas/generar.html",{"form":f})
@institucion_required
def pagos(r):
 exigir_lectura(r);return render(r,"finanzas/pagos.html",{"pagos":pagos_q(r)[:300]})
@institucion_required
def pago_form(r):
 exigir_gestion(r);f=PagoForm(r.POST or None,institucion=r.institucion);alumno_id=r.POST.get("alumno") or r.GET.get("alumno");familia_id=r.POST.get("familia") or r.GET.get("familia");q=cargos_q(r).filter(estado__in=("PENDIENTE","PARCIAL"))
 if alumno_id:q=q.filter(alumno_id=alumno_id)
 elif familia_id:q=q.filter(familia_id=familia_id)
 else:q=q.none()
 if r.method=="POST" and f.is_valid():
  aplicaciones={k[6:]:v for k,v in r.POST.items() if k.startswith("cargo_") and v}
  try:p=registrar_pago(r,alumno=f.cleaned_data["alumno"],familia=f.cleaned_data["familia"],monto=f.cleaned_data["monto"],metodo_pago=f.cleaned_data["metodo_pago"],referencia=f.cleaned_data["referencia"],observaciones=f.cleaned_data["observaciones"],aplicaciones=aplicaciones);messages.success(r,"Pago confirmado y recibo generado.");return redirect("finanzas:pago_detalle",p.pk)
  except (ValidationError,PermissionDenied) as e:f.add_error(None,e)
 return render(r,"finanzas/pago_form.html",{"form":f,"cargos":q})
@institucion_required
def pago_detalle(r,pk):
 exigir_lectura(r);p=get_object_or_404(pagos_q(r).prefetch_related("aplicaciones__cargo__concepto"),pk=pk);return render(r,"finanzas/recibo.html",{"pago":p,"institucion":r.institucion,"puede_anular":rol(r) in GESTION})
@institucion_required
@require_POST
def pago_anular(r,pk):
 p=get_object_or_404(pagos_q(r),pk=pk)
 try:anular_pago(r,p,r.POST.get("motivo",""));messages.success(r,"Pago anulado; los saldos fueron restaurados.")
 except (ValidationError,PermissionDenied) as e:messages.error(r," ".join(e.messages) if hasattr(e,"messages") else "Sin permiso")
 return redirect("finanzas:pago_detalle",pk)
@institucion_required
def alumno_estado(r,pk):
 exigir_lectura(r);a=get_object_or_404(Alumno,institucion=r.institucion,pk=pk);cs=list(cargos_q(r).filter(alumno=a));return render(r,"finanzas/estado_alumno.html",{"alumno":a,"cargos":cs,"total":sum((x.monto_total for x in cs if x.estado!="ANULADO"),Decimal("0")),"pagado":sum((x.pagado for x in cs),Decimal("0")),"saldo":sum((x.saldo for x in cs),Decimal("0")),"vencidos":sum(1 for x in cs if x.vencido)})
@institucion_required
def familia_estado(r,pk):
 exigir_lectura(r);f=get_object_or_404(Familia,institucion=r.institucion,pk=pk);cs=list(cargos_q(r).filter(Q(familia=f)|Q(alumno__familia=f)).distinct());alumnos={}
 for c in cs:alumnos.setdefault(c.alumno,Decimal("0"));alumnos[c.alumno]+=c.saldo
 return render(r,"finanzas/estado_familia.html",{"familia":f,"alumnos":alumnos.items(),"saldo":sum(alumnos.values(),Decimal("0"))})
@institucion_required
def reportes(r):
 exigir_lectura(r);cs=list(cargos_q(r).exclude(estado="ANULADO"));ps=pagos_q(r).filter(estado="CONFIRMADO");saldo_total=sum((x.saldo for x in cs),Decimal("0"));saldo_vencido=sum((x.saldo for x in cs if x.vencido),Decimal("0"));return render(r,"finanzas/reportes.html",{"saldo_total":saldo_total,"saldo_vencido":saldo_vencido,"saldo_no_vencido":saldo_total-saldo_vencido,"morosos":[x for x in cs if x.vencido],"pagos_metodo":ps.values("metodo_pago__nombre").annotate(total=Sum("monto")),"cargos_concepto":Cargo.objects.filter(institucion=r.institucion).values("concepto__nombre").annotate(total=Sum("monto_total"))})
@institucion_required
def exportar(r,tipo):
 exigir_lectura(r);w=Workbook();s=w.active
 if tipo=="pagos":
  s.title="Pagos";s.append(["Recibo","Fecha","Alumno/Familia","Monto","Método","Estado"]);rows=((p.recibo_numero,p.fecha_pago.replace(tzinfo=None),p.alumno.nombre_completo if p.alumno else p.familia.nombre_referencia,p.monto,p.metodo_pago.nombre,p.get_estado_display()) for p in pagos_q(r))
 else:
  s.title="Cargos";s.append(["Alumno","Concepto","Emisión","Vencimiento","Monto","Pagado","Saldo","Estado"]);rows=((c.alumno.nombre_completo,c.concepto.nombre,c.fecha_emision,c.fecha_vencimiento,c.monto_total,c.pagado,c.saldo,"Vencido" if c.vencido else c.get_estado_display()) for c in cargos_q(r))
 for x in rows:s.append(x)
 b=BytesIO();w.save(b);res=HttpResponse(b.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");res["Content-Disposition"]=f'attachment; filename="{tipo}.xlsx"';return res
