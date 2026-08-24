from django import forms
from academico.models import CicloEscolar
from docentes.models import AsignacionDocente
from .models import ActividadEvaluacion,PeriodoAcademico,TipoEvaluacion
class PeriodoForm(forms.ModelForm):
 class Meta:model=PeriodoAcademico;fields=("ciclo","nombre","codigo","numero_orden","fecha_inicio","fecha_fin","activo");widgets={"fecha_inicio":forms.DateInput(attrs={"type":"date"}),"fecha_fin":forms.DateInput(attrs={"type":"date"})}
 def __init__(self,*a,institucion,**kw):super().__init__(*a,**kw);self.fields["ciclo"].queryset=CicloEscolar.objects.filter(institucion=institucion)
class ActividadForm(forms.ModelForm):
 class Meta:model=ActividadEvaluacion;fields=("periodo","asignacion_docente","tipo_evaluacion","nombre","descripcion","fecha","fecha_entrega","punteo_maximo","ponderacion","es_recuperacion");widgets={"fecha":forms.DateInput(attrs={"type":"date"}),"fecha_entrega":forms.DateInput(attrs={"type":"date"})}
 def __init__(self,*a,request,**kw):
  super().__init__(*a,**kw);self.fields["periodo"].queryset=PeriodoAcademico.objects.filter(institucion=request.institucion,activo=True,cerrado=False);self.fields["asignacion_docente"].queryset=__import__('calificaciones.services',fromlist=['asignaciones_usuario']).asignaciones_usuario(request).select_related("curso","seccion");self.fields["tipo_evaluacion"].queryset=TipoEvaluacion.objects.filter(institucion=request.institucion,activo=True)
