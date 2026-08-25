from decimal import Decimal
from django.db.models import Count,Q,Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from finanzas.models import Cargo,Pago
def datos(institucion,params):
 pagos=Pago.objects.filter(institucion=institucion)
 if params.get("desde"):pagos=pagos.filter(fecha_pago__date__gte=params["desde"])
 if params.get("hasta"):pagos=pagos.filter(fecha_pago__date__lte=params["hasta"])
 ingresos=pagos.filter(estado="CONFIRMADO").aggregate(x=Sum("monto"))["x"] or Decimal("0")
 cargos=Cargo.objects.filter(institucion=institucion).exclude(estado="ANULADO").select_related("alumno","familia","inscripcion__grado","inscripcion__seccion").annotate(pagado_calc=Coalesce(Sum("aplicaciones__monto_aplicado",filter=Q(aplicaciones__pago__estado="CONFIRMADO")),Decimal("0")))
 rows=[];saldo=Decimal("0");vencido=Decimal("0");hoy=timezone.localdate()
 for c in cargos:
  c.saldo_calc=max(c.monto_total-c.pagado_calc,Decimal("0"));c.vencido_calc=c.saldo_calc if c.fecha_vencimiento<hoy else Decimal("0");c.dias_vencido=(hoy-c.fecha_vencimiento).days if c.vencido_calc else 0;saldo+=c.saldo_calc;vencido+=c.vencido_calc;rows.append(c)
 return {"ingresos":ingresos,"cargos_emitidos":sum((c.monto_total for c in rows),Decimal("0")),"saldo":saldo,"vencido":vencido,"pagos_anulados":pagos.filter(estado="ANULADO").count(),"cargos":rows}
