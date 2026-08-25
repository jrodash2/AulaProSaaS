from django import forms
from core.forms import AulaProFormMixin
from .models import Comunicacion,ComunicacionDestino,AdjuntoComunicacion
class ComunicacionForm(AulaProFormMixin,forms.ModelForm):
    audiencias=forms.MultipleChoiceField(choices=(("PADRE","Padres"),("ALUMNO","Alumnos"),("DOCENTE","Docentes"),("PROPIETARIO","Administración")),widget=forms.CheckboxSelectMultiple)
    publicar_ahora=forms.BooleanField(required=False)
    class Meta:model=Comunicacion;fields=("titulo","tipo","prioridad","resumen","contenido","fecha_publicacion","fecha_expiracion");widgets={"fecha_publicacion":forms.DateTimeInput(attrs={"type":"datetime-local"}),"fecha_expiracion":forms.DateTimeInput(attrs={"type":"datetime-local"})}
class DestinoForm(AulaProFormMixin,forms.ModelForm):
    class Meta:model=ComunicacionDestino;fields=("tipo_destino","rol","ciclo","grado","seccion","curso","usuario")
    def __init__(self,*a,institucion=None,**kw):
        super().__init__(*a,**kw)
        if institucion:
            for f in ("ciclo","grado","seccion","curso"):self.fields[f].queryset=self.fields[f].queryset.filter(institucion=institucion)
            self.fields["usuario"].queryset=self.fields["usuario"].queryset.filter(asignaciones_institucion__institucion=institucion,asignaciones_institucion__activo=True).distinct()
class AdjuntoForm(AulaProFormMixin,forms.ModelForm):
    class Meta:model=AdjuntoComunicacion;fields=("archivo",)
