from core.forms import AulaProFormMixin
from django import forms
from calificaciones.models import ActividadEvaluacion
from .models import Tarea
class MultipleFileInput(forms.ClearableFileInput):
 allow_multiple_selected=True
class MultipleFileField(forms.FileField):
 def __init__(self,*a,**kw):kw.setdefault("widget",MultipleFileInput());super().__init__(*a,**kw)
 def clean(self,data,initial=None):return [super(MultipleFileField,self).clean(x,initial) for x in (data if isinstance(data,(list,tuple)) else [data])] if data else []
class TareaForm(AulaProFormMixin, forms.ModelForm):
 publicar_ahora=forms.BooleanField(required=False)
 archivos=MultipleFileField(required=False,widget=MultipleFileInput(attrs={"accept":".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png,.webp"}))
 class Meta:model=Tarea;fields=("asignacion_docente","actividad_evaluacion","titulo","descripcion","instrucciones","fecha_publicacion","fecha_limite","permite_entrega_archivo");widgets={"fecha_publicacion":forms.DateTimeInput(attrs={"type":"datetime-local"}),"fecha_limite":forms.DateTimeInput(attrs={"type":"datetime-local"})}
 def __init__(self,*a,request,instance=None,asignacion_id=None,**kw):
  super().__init__(*a,instance=instance,**kw);from .services import asignaciones_usuario
  self.fields["asignacion_docente"].queryset=asignaciones_usuario(request).select_related("curso","seccion");self.fields["actividad_evaluacion"].queryset=ActividadEvaluacion.objects.filter(institucion=request.institucion,asignacion_docente__in=self.fields["asignacion_docente"].queryset)
  if asignacion_id:self.fields["asignacion_docente"].initial=asignacion_id
  if instance and instance.pk and instance.estado!="BORRADOR":self.fields["asignacion_docente"].disabled=True
