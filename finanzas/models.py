from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q,Sum
from django.utils import timezone

class ConfiguracionFinanciera(models.Model):
 institucion=models.OneToOneField("instituciones.Institucion",on_delete=models.CASCADE,related_name="configuracion_financiera");moneda=models.CharField(max_length=3,default="GTQ");simbolo_moneda=models.CharField(max_length=5,default="Q");dia_vencimiento_mensualidad=models.PositiveSmallIntegerField(default=10);aplicar_mora=models.BooleanField(default=False);monto_mora_predeterminado=models.DecimalField(max_digits=10,decimal_places=2,default=0);permitir_pago_mayor_saldo=models.BooleanField(default=False);numeracion_recibos=models.PositiveBigIntegerField(default=0);prefijo_recibo=models.CharField(max_length=20,default="REC");fecha_actualizacion=models.DateTimeField(auto_now=True)
 def clean(self):
  if not 1<=self.dia_vencimiento_mensualidad<=28:raise ValidationError({"dia_vencimiento_mensualidad":"Debe estar entre 1 y 28."})
 def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
class ConceptoCobro(models.Model):
 class Tipo(models.TextChoices):INSCRIPCION="INSCRIPCION","Inscripción";MENSUALIDAD="MENSUALIDAD","Mensualidad";EXTRAORDINARIO="EXTRAORDINARIO","Extraordinario";OTRO="OTRO","Otro"
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="conceptos_cobro");codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=140);descripcion=models.TextField(blank=True);tipo_general=models.CharField(max_length=20,choices=Tipo.choices,default=Tipo.OTRO);monto_predeterminado=models.DecimalField(max_digits=12,decimal_places=2,default=0);activo=models.BooleanField(default=True);recurrente=models.BooleanField(default=False);orden=models.PositiveSmallIntegerField(default=0);fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
 class Meta:ordering=("orden","nombre");constraints=[models.UniqueConstraint(fields=("institucion","codigo"),name="concepto_cobro_codigo_unico")]
 def clean(self):
  if self.monto_predeterminado<0:raise ValidationError({"monto_predeterminado":"No puede ser negativo."})
 def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
 def __str__(self):return self.nombre
class MetodoPago(models.Model):
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="metodos_pago");codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=80);activo=models.BooleanField(default=True);orden=models.PositiveSmallIntegerField(default=0)
 class Meta:ordering=("orden","nombre");constraints=[models.UniqueConstraint(fields=("institucion","codigo"),name="metodo_pago_codigo_unico")]
 def __str__(self):return self.nombre
class Cargo(models.Model):
 class Estado(models.TextChoices):PENDIENTE="PENDIENTE","Pendiente";PARCIAL="PARCIAL","Parcial";PAGADO="PAGADO","Pagado";ANULADO="ANULADO","Anulado"
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="cargos");alumno=models.ForeignKey("alumnos.Alumno",on_delete=models.PROTECT,related_name="cargos");familia=models.ForeignKey("alumnos.Familia",null=True,blank=True,on_delete=models.SET_NULL,related_name="cargos");ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="cargos");inscripcion=models.ForeignKey("alumnos.Inscripcion",null=True,blank=True,on_delete=models.PROTECT,related_name="cargos");concepto=models.ForeignKey(ConceptoCobro,on_delete=models.PROTECT,related_name="cargos");descripcion=models.CharField(max_length=220);fecha_emision=models.DateField();fecha_vencimiento=models.DateField();monto_original=models.DecimalField(max_digits=12,decimal_places=2);descuento=models.DecimalField(max_digits=12,decimal_places=2,default=0);motivo_descuento=models.CharField(max_length=220,blank=True);autorizado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="descuentos_autorizados");recargo=models.DecimalField(max_digits=12,decimal_places=2,default=0);monto_total=models.DecimalField(max_digits=12,decimal_places=2,editable=False);estado=models.CharField(max_length=10,choices=Estado.choices,default=Estado.PENDIENTE);referencia=models.CharField(max_length=80,blank=True);periodo_referencia=models.CharField(max_length=7,blank=True);creado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="cargos_creados");fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
 class Meta:
  ordering=("fecha_vencimiento","alumno__primer_apellido");constraints=[models.UniqueConstraint(fields=("institucion","alumno","concepto","periodo_referencia"),condition=~Q(periodo_referencia=""),name="cargo_recurrente_unico_alumno")];indexes=[models.Index(fields=("institucion","fecha_emision"),name="cargo_inst_emision_idx"),models.Index(fields=("institucion","fecha_vencimiento"),name="cargo_inst_vence_idx"),models.Index(fields=("institucion","concepto"),name="cargo_inst_concepto_idx"),models.Index(fields=("alumno","estado"),name="cargo_alumno_estado_idx"),models.Index(fields=("familia","estado"),name="cargo_familia_estado_idx")]
 def clean(self):
  e={}
  for f in ("alumno","familia","ciclo","inscripcion","concepto"):
   o=getattr(self,f,None)
   if o and o.institucion_id!=self.institucion_id:e[f]="Debe pertenecer a la institución."
  if self.inscripcion_id and self.inscripcion.alumno_id!=self.alumno_id:e["inscripcion"]="No corresponde al alumno."
  if self.fecha_vencimiento and self.fecha_emision and self.fecha_vencimiento<self.fecha_emision:e["fecha_vencimiento"]="Debe ser igual o posterior a emisión."
  for f in ("monto_original","descuento","recargo"):
   if getattr(self,f,0)<0:e[f]="No puede ser negativo."
  total=(self.monto_original or 0)-(self.descuento or 0)+(self.recargo or 0)
  if total<0:e["descuento"]="El descuento no puede producir un total negativo."
  if self.descuento and (not self.motivo_descuento.strip() or not self.autorizado_por_id):e["motivo_descuento"]="El descuento requiere motivo y autorización."
  if e:raise ValidationError(e)
 def save(self,*a,**kw):self.monto_total=self.monto_original-self.descuento+self.recargo;self.full_clean();return super().save(*a,**kw)
 @property
 def pagado(self):return self.aplicaciones.filter(pago__estado="CONFIRMADO").aggregate(x=Sum("monto_aplicado"))["x"] or Decimal("0")
 @property
 def saldo(self):return max(self.monto_total-self.pagado,Decimal("0")) if self.estado!="ANULADO" else Decimal("0")
 @property
 def vencido(self):return self.saldo>0 and self.fecha_vencimiento<timezone.localdate() and self.estado!="ANULADO"
class Pago(models.Model):
 class Estado(models.TextChoices):BORRADOR="BORRADOR","Borrador";CONFIRMADO="CONFIRMADO","Confirmado";ANULADO="ANULADO","Anulado"
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="pagos");alumno=models.ForeignKey("alumnos.Alumno",null=True,blank=True,on_delete=models.PROTECT,related_name="pagos");familia=models.ForeignKey("alumnos.Familia",null=True,blank=True,on_delete=models.PROTECT,related_name="pagos");fecha_pago=models.DateTimeField(default=timezone.now);monto=models.DecimalField(max_digits=12,decimal_places=2);metodo_pago=models.ForeignKey(MetodoPago,on_delete=models.PROTECT,related_name="pagos");referencia=models.CharField(max_length=120,blank=True);observaciones=models.TextField(blank=True);estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.BORRADOR);registrado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="pagos_registrados");recibo_numero=models.CharField(max_length=50,blank=True);motivo_anulacion=models.TextField(blank=True);anulado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="pagos_anulados");fecha_anulacion=models.DateTimeField(null=True,blank=True);fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
 class Meta:ordering=("-fecha_pago",);constraints=[models.UniqueConstraint(fields=("institucion","recibo_numero"),condition=~Q(recibo_numero=""),name="recibo_unico_institucion")];indexes=[models.Index(fields=("institucion","fecha_pago"),name="pago_inst_fecha_idx")]
 def clean(self):
  e={}
  if self.monto is not None and self.monto<=0:e["monto"]="Debe ser mayor que cero."
  if not self.alumno_id and not self.familia_id:e["alumno"]="Seleccione alumno o familia."
  for f in ("alumno","familia","metodo_pago"):
   o=getattr(self,f,None)
   if o and o.institucion_id!=self.institucion_id:e[f]="Debe pertenecer a la institución."
  if e:raise ValidationError(e)
 def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
 @property
 def aplicado(self):return self.aplicaciones.aggregate(x=Sum("monto_aplicado"))["x"] or Decimal("0")
class AplicacionPago(models.Model):
 institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="aplicaciones_pago");pago=models.ForeignKey(Pago,on_delete=models.PROTECT,related_name="aplicaciones");cargo=models.ForeignKey(Cargo,on_delete=models.PROTECT,related_name="aplicaciones");monto_aplicado=models.DecimalField(max_digits=12,decimal_places=2);fecha_creacion=models.DateTimeField(auto_now_add=True)
 class Meta:constraints=[models.UniqueConstraint(fields=("pago","cargo"),name="aplicacion_unica_pago_cargo")]
 def clean(self):
  e={}
  if self.monto_aplicado<=0:e["monto_aplicado"]="Debe ser mayor que cero."
  if self.pago_id and self.pago.institucion_id!=self.institucion_id:e["pago"]="No pertenece a la institución."
  if self.cargo_id and self.cargo.institucion_id!=self.institucion_id:e["cargo"]="No pertenece a la institución."
  if e:raise ValidationError(e)
 def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
