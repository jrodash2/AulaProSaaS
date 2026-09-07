from django import forms
from django.db.models import Q

from academico.models import CursoInstitucion
from alumnos.models import Encargado, Inscripcion
from core.forms import AulaProFormMixin
from docentes.models import Docente

from .models import (
    CategoriaSeguimiento,
    CompromisoSeguimiento,
    NotaSeguimiento,
    RegistroSeguimiento,
    ReunionSeguimiento,
)


class CategoriaForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = CategoriaSeguimiento
        exclude = ("institucion",)


class RegistroForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = RegistroSeguimiento
        fields = (
            "inscripcion",
            "categoria",
            "tipo",
            "fecha",
            "titulo",
            "descripcion",
            "gravedad",
            "confidencialidad",
            "curso",
            "docente",
        )
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, institucion, alumnos=None, **kwargs):
        super().__init__(*args, **kwargs)
        docente_actual = self.instance.docente_id if self.instance.pk else None
        self.fields["inscripcion"].queryset = Inscripcion.objects.filter(
            institucion=institucion,
            alumno__in=alumnos or [],
        ).select_related("alumno", "grado", "seccion")
        self.fields["categoria"].queryset = CategoriaSeguimiento.objects.filter(
            institucion=institucion,
            activo=True,
        )
        self.fields["curso"].queryset = CursoInstitucion.objects.filter(
            institucion=institucion,
            activo=True,
        )
        self.fields["docente"].queryset = Docente.objects.filter(
            institucion=institucion,
        ).filter(Q(estado=Docente.Estado.ACTIVO) | Q(pk=docente_actual))


class CompromisoForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = CompromisoSeguimiento
        fields = ("descripcion", "responsable", "fecha_compromiso", "fecha_limite")
        widgets = {
            "fecha_compromiso": forms.DateInput(attrs={"type": "date"}),
            "fecha_limite": forms.DateInput(attrs={"type": "date"}),
        }


class NotaForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = NotaSeguimiento
        fields = ("fecha", "comentario", "visible_padre")
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"})}


class ReunionForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = ReunionSeguimiento
        fields = (
            "fecha",
            "encargado",
            "participantes",
            "motivo",
            "acuerdos",
            "observaciones",
        )
        widgets = {"fecha": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def __init__(self, *args, institucion, **kwargs):
        super().__init__(*args, **kwargs)
        encargado_actual = self.instance.encargado_id if self.instance.pk else None
        self.fields["encargado"].queryset = Encargado.objects.filter(
            institucion=institucion,
        ).filter(Q(activo=True) | Q(pk=encargado_actual))
