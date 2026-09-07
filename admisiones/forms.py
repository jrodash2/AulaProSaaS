from django import forms
from academico.models import CicloEscolar,OfertaAcademica,GradoInstitucion,JornadaInstitucion,Seccion
from .models import *
class Style:
 def style(self):
  for f in self.fields.values():f.widget.attrs.setdefault('class','form-check-input' if isinstance(f.widget,forms.CheckboxInput) else 'form-select' if isinstance(f.widget,forms.Select) else 'form-control')
class PublicaForm(Style,forms.Form):
 nombres=forms.CharField(max_length=160);apellidos=forms.CharField(max_length=160);fecha_nacimiento=forms.DateField(widget=forms.DateInput(attrs={'type':'date'}));cui=forms.CharField(max_length=13,required=False);encargado_nombres=forms.CharField(max_length=160);encargado_apellidos=forms.CharField(max_length=160,required=False);telefono=forms.CharField(max_length=30);correo=forms.EmailField();ciclo=forms.ModelChoiceField(CicloEscolar.objects.none());oferta=forms.ModelChoiceField(OfertaAcademica.objects.none());grado=forms.ModelChoiceField(GradoInstitucion.objects.none());observaciones=forms.CharField(widget=forms.Textarea,required=False);website=forms.CharField(required=False,widget=forms.HiddenInput)
 def __init__(self,*a,institucion,**k):super().__init__(*a,**k);self.fields['ciclo'].queryset=CicloEscolar.objects.filter(institucion=institucion,cerrado=False);self.fields['oferta'].queryset=OfertaAcademica.objects.filter(institucion=institucion,activa=True);self.fields['grado'].queryset=GradoInstitucion.objects.filter(institucion=institucion,activo=True);self.style()
 def clean_website(self):
  if self.cleaned_data.get('website'):raise forms.ValidationError('Solicitud inválida.')
  return ''
 def clean(self):
  d=super().clean();oferta=d.get('oferta');grado=d.get('grado');ciclo=d.get('ciclo')
  if oferta and ciclo and oferta.ciclo_id!=ciclo.pk:self.add_error('oferta','La oferta no corresponde al ciclo.')
  if grado and oferta and grado.oferta_id!=oferta.pk:self.add_error('grado','El grado no corresponde a la oferta.')
  return d
class ConversionForm(Style,forms.Form):
 seccion=forms.ModelChoiceField(Seccion.objects.none())
 def __init__(self,*a,solicitud,**k):super().__init__(*a,**k);self.fields['seccion'].queryset=Seccion.objects.filter(institucion=solicitud.institucion,ciclo=solicitud.ciclo_solicitado,activa=True).select_related('grado');self.style()
class EntrevistaForm(Style,forms.ModelForm):
 class Meta:model=EntrevistaAdmision;exclude=('institucion','solicitud');widgets={'fecha_programada':forms.DateTimeInput(attrs={'type':'datetime-local'}),'fecha_realizada':forms.DateTimeInput(attrs={'type':'datetime-local'})}
 def __init__(self,*a,**k):super().__init__(*a,**k);self.style()
class EvaluacionForm(Style,forms.ModelForm):
 class Meta:model=EvaluacionAdmision;exclude=('institucion','solicitud','evaluado_por');widgets={'fecha':forms.DateInput(attrs={'type':'date'})}
 def __init__(self,*a,institucion,**k):super().__init__(*a,**k);self.fields['tipo_evaluacion'].queryset=TipoEvaluacionAdmision.objects.filter(institucion=institucion,activo=True);self.style()
