from django import forms
from academico.models import CicloEscolar,GradoInstitucion,Seccion
from alumnos.models import Alumno,Familia
from .models import Cargo,ConceptoCobro,ConfiguracionFinanciera,MetodoPago
class ConceptoForm(forms.ModelForm):
 class Meta:model=ConceptoCobro;fields=("codigo","nombre","descripcion","tipo_general","monto_predeterminado","activo","recurrente","orden")
class ConfiguracionForm(forms.ModelForm):
 class Meta:model=ConfiguracionFinanciera;fields=("moneda","simbolo_moneda","dia_vencimiento_mensualidad","aplicar_mora","monto_mora_predeterminado","prefijo_recibo")
class CargoForm(forms.ModelForm):
 class Meta:model=Cargo;fields=("alumno","familia","ciclo","inscripcion","concepto","descripcion","fecha_emision","fecha_vencimiento","monto_original","descuento","motivo_descuento","recargo","referencia");widgets={"fecha_emision":forms.DateInput(attrs={"type":"date"}),"fecha_vencimiento":forms.DateInput(attrs={"type":"date"})}
 def __init__(self,*a,request,**kw):
  super().__init__(*a,**kw);inst=request.institucion;self.fields["alumno"].queryset=Alumno.objects.filter(institucion=inst);self.fields["familia"].queryset=Familia.objects.filter(institucion=inst);self.fields["ciclo"].queryset=CicloEscolar.objects.filter(institucion=inst);self.fields["inscripcion"].queryset=__import__('alumnos.models',fromlist=['Inscripcion']).Inscripcion.objects.filter(institucion=inst);self.fields["concepto"].queryset=ConceptoCobro.objects.filter(institucion=inst,activo=True)
class PagoForm(forms.Form):
 alumno=forms.ModelChoiceField(Alumno.objects.none(),required=False);familia=forms.ModelChoiceField(Familia.objects.none(),required=False);monto=forms.DecimalField(max_digits=12,decimal_places=2,min_value=0.01);metodo_pago=forms.ModelChoiceField(MetodoPago.objects.none());referencia=forms.CharField(required=False,max_length=120);observaciones=forms.CharField(required=False,widget=forms.Textarea)
 def __init__(self,*a,institucion,**kw):super().__init__(*a,**kw);self.fields["alumno"].queryset=Alumno.objects.filter(institucion=institucion);self.fields["familia"].queryset=Familia.objects.filter(institucion=institucion);self.fields["metodo_pago"].queryset=MetodoPago.objects.filter(institucion=institucion,activo=True)
 def clean(self):
  d=super().clean()
  if bool(d.get("alumno"))==bool(d.get("familia")):raise forms.ValidationError("Seleccione un alumno o una familia.")
  return d
class GenerarForm(forms.Form):
 ciclo=forms.ModelChoiceField(CicloEscolar.objects.none());concepto=forms.ModelChoiceField(ConceptoCobro.objects.none());grado=forms.ModelChoiceField(GradoInstitucion.objects.none(),required=False);seccion=forms.ModelChoiceField(Seccion.objects.none(),required=False);periodo_referencia=forms.RegexField(r"^\d{4}-(0[1-9]|1[0-2])$",help_text="Formato YYYY-MM");monto=forms.DecimalField(max_digits=12,decimal_places=2,min_value=.01);fecha_emision=forms.DateField(widget=forms.DateInput(attrs={"type":"date"}));fecha_vencimiento=forms.DateField(widget=forms.DateInput(attrs={"type":"date"}))
 def __init__(self,*a,institucion,**kw):super().__init__(*a,**kw);self.fields["ciclo"].queryset=CicloEscolar.objects.filter(institucion=institucion);self.fields["concepto"].queryset=ConceptoCobro.objects.filter(institucion=institucion,activo=True);self.fields["grado"].queryset=GradoInstitucion.objects.filter(institucion=institucion);self.fields["seccion"].queryset=Seccion.objects.filter(institucion=institucion)
