from decimal import Decimal
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from alumnos.models import Inscripcion
from auditoria.services import registrar_evento
from .models import AplicacionPago,Cargo,ConceptoCobro,ConfiguracionFinanciera,Pago
GESTION={"PROPIETARIO","ADMINISTRADOR","CONTABILIDAD"};LECTURA=GESTION|{"DIRECTOR","SECRETARIA"};DESCUENTOS=GESTION|{"DIRECTOR"}
def rol(r):return r.asignacion_institucion.rol
def exigir_lectura(r):
 if rol(r) not in LECTURA:raise PermissionDenied
def exigir_gestion(r):
 if rol(r) not in GESTION|{"SECRETARIA"}:raise PermissionDenied
def config(inst):return ConfiguracionFinanciera.objects.get_or_create(institucion=inst)[0]
def actualizar_estado(cargo):
 if cargo.estado==Cargo.Estado.ANULADO:return cargo
 saldo=cargo.saldo
 cargo.estado=Cargo.Estado.PAGADO if saldo==0 else (Cargo.Estado.PARCIAL if saldo<cargo.monto_total else Cargo.Estado.PENDIENTE);cargo.save(update_fields=("estado","monto_total","fecha_actualizacion"));return cargo
def crear_cargo(request,**datos):
 if rol(request) not in GESTION:raise PermissionDenied
 if datos.get("descuento",0) and rol(request) not in DESCUENTOS:raise PermissionDenied
 if datos.get("descuento",0):datos["autorizado_por"]=request.user
 c=Cargo.objects.create(institucion=request.institucion,creado_por=request.user,**datos);registrar_evento(request,"CREAR_CARGO",c,detalles={"monto":str(c.monto_total),"descuento":str(c.descuento),"recargo":str(c.recargo)});return c
@transaction.atomic
def registrar_pago(request,*,alumno=None,familia=None,monto,metodo_pago,aplicaciones,referencia="",observaciones="",fecha_pago=None):
 exigir_gestion(request);monto=Decimal(str(monto));items={int(k):Decimal(str(v)) for k,v in aplicaciones.items() if Decimal(str(v))>0}
 if sum(items.values(),Decimal("0"))!=monto:raise ValidationError("El total aplicado debe ser igual al monto recibido.")
 cargos=list(Cargo.objects.select_for_update().filter(institucion=request.institucion,pk__in=sorted(items),estado__in=("PENDIENTE","PARCIAL")))
 if len(cargos)!=len(items):raise ValidationError("Uno o más cargos no están disponibles.")
 for c in cargos:
  if alumno and c.alumno_id!=alumno.pk:raise ValidationError("El cargo no pertenece al alumno.")
  if familia and c.familia_id!=familia.pk:raise ValidationError("El cargo no pertenece a la familia.")
  if items[c.pk]>c.saldo:raise ValidationError(f"La aplicación supera el saldo de {c.descripcion}.")
 cfg=config(request.institucion);cfg=ConfiguracionFinanciera.objects.select_for_update().get(pk=cfg.pk);cfg.numeracion_recibos+=1;cfg.save(update_fields=("numeracion_recibos","fecha_actualizacion"));recibo=f"{cfg.prefijo_recibo}-{(fecha_pago or timezone.now()).year}-{cfg.numeracion_recibos:06d}"
 p=Pago.objects.create(institucion=request.institucion,alumno=alumno,familia=familia,fecha_pago=fecha_pago or timezone.now(),monto=monto,metodo_pago=metodo_pago,referencia=referencia,observaciones=observaciones,estado=Pago.Estado.BORRADOR,registrado_por=request.user,recibo_numero=recibo)
 for c in cargos:AplicacionPago.objects.create(institucion=request.institucion,pago=p,cargo=c,monto_aplicado=items[c.pk])
 p.estado=Pago.Estado.CONFIRMADO;p.save(update_fields=("estado","fecha_actualizacion"))
 for c in cargos:actualizar_estado(c)
 registrar_evento(request,"REGISTRAR_PAGO",p,detalles={"recibo":recibo,"monto":str(monto),"cargos":[{"id":c.pk,"monto":str(items[c.pk])} for c in cargos]});return p
@transaction.atomic
def anular_pago(request,pago,motivo):
 if rol(request) not in GESTION:raise PermissionDenied
 if not motivo.strip():raise ValidationError("El motivo es obligatorio.")
 p=Pago.objects.select_for_update().get(institucion=request.institucion,pk=pago.pk)
 if p.estado!=Pago.Estado.CONFIRMADO:raise ValidationError("Solo puede anular un pago confirmado.")
 cargos=list(Cargo.objects.select_for_update().filter(aplicaciones__pago=p));p.estado=Pago.Estado.ANULADO;p.motivo_anulacion=motivo.strip();p.anulado_por=request.user;p.fecha_anulacion=timezone.now();p.save()
 for c in cargos:actualizar_estado(c)
 registrar_evento(request,"ANULAR_PAGO",p,detalles={"recibo":p.recibo_numero,"monto":str(p.monto),"motivo":motivo});return p
def vista_previa_aplicacion(cargos,monto):
 restante=Decimal(str(monto));resultado=[]
 for c in sorted(cargos,key=lambda x:(x.fecha_vencimiento,x.pk)):
  aplicar=min(c.saldo,restante)
  if aplicar>0:resultado.append((c,aplicar));restante-=aplicar
  if restante<=0:break
 return resultado,restante
@transaction.atomic
def generar_cargos_mensuales(request,*,ciclo,concepto,monto,fecha_emision,fecha_vencimiento,periodo_referencia,grado=None,seccion=None):
 if rol(request) not in GESTION:raise PermissionDenied
 ins=Inscripcion.objects.filter(institucion=request.institucion,ciclo=ciclo,estado=Inscripcion.Estado.ACTIVA).select_related("alumno","alumno__familia")
 if grado:ins=ins.filter(grado=grado)
 if seccion:ins=ins.filter(seccion=seccion)
 creados=0
 for i in ins:
  _,nuevo=Cargo.objects.get_or_create(institucion=request.institucion,alumno=i.alumno,concepto=concepto,periodo_referencia=periodo_referencia,defaults={"familia":i.alumno.familia,"ciclo":ciclo,"inscripcion":i,"descripcion":f"{concepto.nombre} {periodo_referencia}","fecha_emision":fecha_emision,"fecha_vencimiento":fecha_vencimiento,"monto_original":monto,"monto_total":monto,"creado_por":request.user});creados+=int(nuevo)
 registrar_evento(request,"GENERAR_CARGOS_MASIVOS",concepto,detalles={"periodo":periodo_referencia,"creados":creados,"monto":str(monto)});return creados,ins.count()-creados
def aplicar_mora(request,cargo,monto=None):
 if rol(request) not in GESTION:raise PermissionDenied
 cfg=config(request.institucion);valor=Decimal(str(monto if monto is not None else cfg.monto_mora_predeterminado))
 if not cargo.vencido:raise ValidationError("El cargo no está vencido con saldo.")
 cargo.recargo+=valor;cargo.save();registrar_evento(request,"APLICAR_RECARGO",cargo,detalles={"recargo":str(valor)});return cargo
