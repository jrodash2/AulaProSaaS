from django import forms
from django.utils import timezone
from academico.models import CicloEscolar, CursoInstitucion, GradoInstitucion, OfertaAcademica, Seccion
from .models import SesionAsistencia

class SesionForm(forms.Form):
    ciclo = forms.ModelChoiceField(CicloEscolar.objects.none())
    oferta = forms.ModelChoiceField(OfertaAcademica.objects.none(), label="Oferta académica")
    grado = forms.ModelChoiceField(GradoInstitucion.objects.none())
    seccion = forms.ModelChoiceField(Seccion.objects.none())
    tipo = forms.ChoiceField(choices=SesionAsistencia.Tipo.choices)
    curso = forms.ModelChoiceField(CursoInstitucion.objects.none(), required=False)
    fecha = forms.DateField(widget=forms.DateInput(attrs={"type":"date"}), initial=timezone.localdate)
    def __init__(self, *args, institucion, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.fields: self.fields[name].widget.attrs.setdefault("class", "form-select" if name != "fecha" else "form-control")
        self.fields["ciclo"].queryset = CicloEscolar.objects.filter(institucion=institucion, activo=True)
        self.fields["oferta"].queryset = OfertaAcademica.objects.filter(institucion=institucion, activa=True)
        self.fields["grado"].queryset = GradoInstitucion.objects.filter(institucion=institucion, activo=True)
        self.fields["seccion"].queryset = Seccion.objects.filter(institucion=institucion, activa=True)
        self.fields["curso"].queryset = CursoInstitucion.objects.filter(institucion=institucion, activo=True)
        if request and request.asignacion_institucion.rol == "DOCENTE":
            from docentes.models import AsignacionDocente, AsignacionGuia, Docente
            docente = Docente.objects.filter(institucion=institucion, usuario=request.user).first()
            asignaciones = AsignacionDocente.objects.filter(institucion=institucion, docente=docente, activa=True) if docente else AsignacionDocente.objects.none()
            guias = AsignacionGuia.objects.filter(institucion=institucion, docente=docente, activa=True) if docente else AsignacionGuia.objects.none()
            ciclos = set(asignaciones.values_list("ciclo_id", flat=True)) | set(guias.values_list("ciclo_id", flat=True))
            secciones = set(asignaciones.values_list("seccion_id", flat=True)) | set(guias.values_list("seccion_id", flat=True))
            self.fields["ciclo"].queryset = self.fields["ciclo"].queryset.filter(pk__in=ciclos)
            self.fields["oferta"].queryset = self.fields["oferta"].queryset.filter(grados__secciones__pk__in=secciones).distinct()
            self.fields["grado"].queryset = self.fields["grado"].queryset.filter(secciones__pk__in=secciones).distinct()
            self.fields["seccion"].queryset = self.fields["seccion"].queryset.filter(pk__in=secciones)
            self.fields["curso"].queryset = self.fields["curso"].queryset.filter(asignaciones_docentes__in=asignaciones).distinct()
    def clean(self):
        data = super().clean()
        if data.get("fecha") and data["fecha"] > timezone.localdate(): self.add_error("fecha", "No se permiten fechas futuras.")
        if data.get("tipo") == SesionAsistencia.Tipo.CURSO and not data.get("curso"): self.add_error("curso", "Seleccione un curso.")
        return data
