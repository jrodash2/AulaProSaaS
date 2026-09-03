from django import forms
from alumnos.models import Inscripcion,Encargado
from academico.models import CursoInstitucion
from docentes.models import Docente
from .models import *
class Styled:
 def style(self):
  for f in self.fields.values():f.widget.attrs.setdefault("class","form-check-input" if isinstance(f.widget,forms.CheckboxInput) else "form-select" if isinstance(f.widget,forms.Select) else "form-control")
class CategoriaForm(Styled,forms.ModelForm):
 class Meta:model=CategoriaSeguimiento;exclude=("institucion",)
 def __init__(self,*a,**k):super().__init__(*a,**k);self.style()
class RegistroForm(Styled,forms.ModelForm):
 class Meta:model=RegistroSeguimiento;fields=("inscripcion","categoria","tipo","fecha","titulo","descripcion","gravedad","confidencialidad","curso","docente");widgets={"fecha":forms.DateInput(attrs={"type":"date"})}
 def __init__(self,*a,institucion,alumnos=None,**k):
  super().__init__(*a,**k);self.fields["inscripcion"].queryset=Inscripcion.objects.filter(institucion=institucion,alumno__in=alumnos or []).select_related("alumno","grado","seccion");self.fields["categoria"].queryset=CategoriaSeguimiento.objects.filter(institucion=institucion,activo=True);self.fields["curso"].queryset=CursoInstitucion.objects.filter(institucion=institucion,activo=True);self.fields["docente"].queryset=Docente.objects.filter(institucion=institucion,activo=True);self.style()
class CompromisoForm(Styled,forms.ModelForm):
 class Meta:model=CompromisoSeguimiento;fields=("descripcion","responsable","fecha_compromiso","fecha_limite");widgets={"fecha_compromiso":forms.DateInput(attrs={"type":"date"}),"fecha_limite":forms.DateInput(attrs={"type":"date"})}
 def __init__(self,*a,**k):super().__init__(*a,**k);self.style()
class NotaForm(Styled,forms.ModelForm):
 class Meta:model=NotaSeguimiento;fields=("fecha","comentario","visible_padre");widgets={"fecha":forms.DateInput(attrs={"type":"date"})}
 def __init__(self,*a,**k):super().__init__(*a,**k);self.style()
class ReunionForm(Styled,forms.ModelForm):
 class Meta:model=ReunionSeguimiento;fields=("fecha","encargado","participantes","motivo","acuerdos","observaciones");widgets={"fecha":forms.DateTimeInput(attrs={"type":"datetime-local"})}
 def __init__(self,*a,institucion,**k):super().__init__(*a,**k);self.fields["encargado"].queryset=Encargado.objects.filter(institucion=institucion,activo=True);self.style()
