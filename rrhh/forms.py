from django import forms
from instituciones.models import UsuarioInstitucion
from docentes.models import Docente
from .models import *
class Styled:
 def style(self):
  for f in self.fields.values():f.widget.attrs.setdefault("class","form-check-input" if isinstance(f.widget,forms.CheckboxInput) else "form-select" if isinstance(f.widget,forms.Select) else "form-control")
class EmpleadoForm(Styled,forms.ModelForm):
 class Meta:model=Empleado;exclude=("institucion","codigo_empleado","secuencia","creado_por","fecha_creacion","fecha_actualizacion");widgets={"fecha_nacimiento":forms.DateInput(attrs={"type":"date"}),"fecha_ingreso":forms.DateInput(attrs={"type":"date"}),"fecha_egreso":forms.DateInput(attrs={"type":"date"})}
 def __init__(self,*a,institucion,**k):
  super().__init__(*a,**k);self.fields["area"].queryset=AreaLaboral.objects.filter(institucion=institucion,activa=True);self.fields["puesto"].queryset=PuestoLaboral.objects.filter(institucion=institucion,activo=True);self.fields["usuario"].queryset=__import__('django.contrib.auth',fromlist=['get_user_model']).get_user_model().objects.filter(asignaciones_institucion__institucion=institucion,asignaciones_institucion__activo=True).distinct();self.fields["docente"].queryset=Docente.objects.filter(institucion=institucion,activo=True);self.style()
class AreaForm(Styled,forms.ModelForm):
 class Meta:model=AreaLaboral;exclude=("institucion",)
 def __init__(self,*a,**k):super().__init__(*a,**k);self.style()
class PuestoForm(Styled,forms.ModelForm):
 class Meta:model=PuestoLaboral;exclude=("institucion",)
 def __init__(self,*a,institucion,**k):super().__init__(*a,**k);self.fields["area"].queryset=AreaLaboral.objects.filter(institucion=institucion);self.style()
class ContratoForm(Styled,forms.ModelForm):
 class Meta:model=ContratoLaboral;exclude=("institucion","empleado","creado_por","fecha_creacion","motivo_finalizacion");widgets={"fecha_inicio":forms.DateInput(attrs={"type":"date"}),"fecha_fin":forms.DateInput(attrs={"type":"date"})}
 def __init__(self,*a,institucion,ver_salario=False,**k):super().__init__(*a,**k);self.fields["puesto"].queryset=PuestoLaboral.objects.filter(institucion=institucion);self.style();self.fields.pop("salario_referencia") if not ver_salario else None
class PermisoForm(Styled,forms.ModelForm):
 class Meta:model=PermisoLaboral;fields=("tipo","fecha_inicio","fecha_fin","hora_inicio","hora_fin","motivo","observaciones");widgets={"fecha_inicio":forms.DateInput(attrs={"type":"date"}),"fecha_fin":forms.DateInput(attrs={"type":"date"}),"hora_inicio":forms.TimeInput(attrs={"type":"time"}),"hora_fin":forms.TimeInput(attrs={"type":"time"})}
 def __init__(self,*a,**k):super().__init__(*a,**k);self.style()
class DocumentoForm(Styled,forms.ModelForm):
 class Meta:model=DocumentoEmpleado;fields=("tipo_documento","archivo","fecha_emision","fecha_vencimiento","observaciones");widgets={"fecha_emision":forms.DateInput(attrs={"type":"date"}),"fecha_vencimiento":forms.DateInput(attrs={"type":"date"})}
 def __init__(self,*a,institucion,**k):super().__init__(*a,**k);self.fields["tipo_documento"].queryset=TipoDocumentoEmpleado.objects.filter(institucion=institucion,activo=True);self.style()
