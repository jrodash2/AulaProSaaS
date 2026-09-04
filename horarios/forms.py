from datetime import datetime,timedelta
from django import forms
from academico.models import CicloEscolar,JornadaInstitucion,Seccion
from docentes.models import AsignacionDocente
from .models import Aula,BloqueHorario,HorarioClase

class StyledMixin:
 def style(self):
  for f in self.fields.values():f.widget.attrs.setdefault("class","form-check-input" if isinstance(f.widget,forms.CheckboxInput) else "form-select" if isinstance(f.widget,forms.Select) else "form-control")
class AulaForm(StyledMixin,forms.ModelForm):
 class Meta:model=Aula;exclude=("institucion","fecha_creacion","fecha_actualizacion")
 def __init__(self,*a,**kw):super().__init__(*a,**kw);self.style()
class BloqueHorarioForm(StyledMixin,forms.ModelForm):
 class Meta:model=BloqueHorario;exclude=("institucion",);widgets={"hora_inicio":forms.TimeInput(attrs={"type":"time"}),"hora_fin":forms.TimeInput(attrs={"type":"time"})}
 def __init__(self,*a,institucion,**kw):super().__init__(*a,**kw);self.fields["jornada"].queryset=JornadaInstitucion.objects.filter(institucion=institucion,activa=True);self.style()
class HorarioClaseForm(StyledMixin,forms.ModelForm):
 class Meta:model=HorarioClase;exclude=("institucion","fecha_creacion","fecha_actualizacion")
 def __init__(self,*a,institucion,**kw):
  super().__init__(*a,**kw);self.fields["ciclo"].queryset=CicloEscolar.objects.filter(institucion=institucion,cerrado=False);self.fields["jornada"].queryset=JornadaInstitucion.objects.filter(institucion=institucion,activa=True);self.fields["seccion"].queryset=Seccion.objects.filter(institucion=institucion,activa=True);self.fields["bloque"].queryset=BloqueHorario.objects.filter(institucion=institucion,activo=True,tipo="CLASE");self.fields["aula"].queryset=Aula.objects.filter(institucion=institucion,activa=True)
  asignaciones=AsignacionDocente.objects.filter(institucion=institucion,activa=True).select_related("curso","docente")
  seccion=(self.data.get("seccion") if self.is_bound else self.initial.get("seccion") or getattr(self.instance,"seccion_id",None));ciclo=(self.data.get("ciclo") if self.is_bound else self.initial.get("ciclo") or getattr(self.instance,"ciclo_id",None))
  if seccion:asignaciones=asignaciones.filter(seccion_id=seccion)
  if ciclo:asignaciones=asignaciones.filter(ciclo_id=ciclo)
  self.fields["asignacion_docente"].queryset=asignaciones;self.style()
class GenerarBloquesForm(StyledMixin,forms.Form):
 jornada=forms.ModelChoiceField(JornadaInstitucion.objects.none());hora_inicial=forms.TimeField(widget=forms.TimeInput(attrs={"type":"time"}));duracion=forms.IntegerField(min_value=15,max_value=180,initial=45);cantidad=forms.IntegerField(min_value=1,max_value=15,initial=7);recreo_despues=forms.IntegerField(min_value=0,max_value=14,initial=3);duracion_recreo=forms.IntegerField(min_value=5,max_value=90,initial=20)
 def __init__(self,*a,institucion,**kw):super().__init__(*a,**kw);self.fields["jornada"].queryset=JornadaInstitucion.objects.filter(institucion=institucion,activa=True);self.style()
 def bloques(self):
  d=self.cleaned_data;actual=datetime.combine(datetime.today(),d["hora_inicial"]);items=[]
  for n in range(1,d["cantidad"]+1):
   fin=actual+timedelta(minutes=d["duracion"]);items.append((f"Período {n}",n*10,actual.time(),fin.time(),"CLASE"));actual=fin
   if d["recreo_despues"]==n:
    fin=actual+timedelta(minutes=d["duracion_recreo"]);items.append(("Recreo",n*10+1,actual.time(),fin.time(),"RECREO"));actual=fin
  return items
