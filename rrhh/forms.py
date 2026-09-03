from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from core.forms import AulaProFormMixin
from docentes.models import Docente

from .models import (
    AreaLaboral,
    ContratoLaboral,
    DocumentoEmpleado,
    Empleado,
    PermisoLaboral,
    PuestoLaboral,
    TipoDocumentoEmpleado,
)


class EmpleadoForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = Empleado
        exclude = (
            "institucion",
            "codigo_empleado",
            "secuencia",
            "creado_por",
            "fecha_creacion",
            "fecha_actualizacion",
        )
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
            "fecha_ingreso": forms.DateInput(attrs={"type": "date"}),
            "fecha_egreso": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, institucion, **kwargs):
        super().__init__(*args, **kwargs)
        area_actual = self.instance.area_id if self.instance.pk else None
        puesto_actual = self.instance.puesto_id if self.instance.pk else None
        usuario_actual = self.instance.usuario_id if self.instance.pk else None
        docente_actual = self.instance.docente_id if self.instance.pk else None

        self.fields["area"].queryset = AreaLaboral.objects.filter(
            institucion=institucion
        ).filter(Q(activa=True) | Q(pk=area_actual))
        self.fields["puesto"].queryset = PuestoLaboral.objects.filter(
            institucion=institucion
        ).filter(Q(activo=True) | Q(pk=puesto_actual))
        self.fields["usuario"].queryset = get_user_model().objects.filter(
            Q(
                asignaciones_institucion__institucion=institucion,
                asignaciones_institucion__activo=True,
            )
            | Q(pk=usuario_actual)
        ).distinct()
        self.fields["docente"].queryset = Docente.objects.filter(
            institucion=institucion
        ).filter(Q(estado=Docente.Estado.ACTIVO) | Q(pk=docente_actual))


class AreaForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = AreaLaboral
        exclude = ("institucion",)


class PuestoForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = PuestoLaboral
        exclude = ("institucion",)

    def __init__(self, *args, institucion, **kwargs):
        super().__init__(*args, **kwargs)
        area_actual = self.instance.area_id if self.instance.pk else None
        self.fields["area"].queryset = AreaLaboral.objects.filter(
            institucion=institucion
        ).filter(Q(activa=True) | Q(pk=area_actual))


class ContratoForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = ContratoLaboral
        exclude = (
            "institucion",
            "empleado",
            "creado_por",
            "fecha_creacion",
            "motivo_finalizacion",
        )
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, institucion, ver_salario=False, **kwargs):
        super().__init__(*args, **kwargs)
        puesto_actual = self.instance.puesto_id if self.instance.pk else None
        self.fields["puesto"].queryset = PuestoLaboral.objects.filter(
            institucion=institucion
        ).filter(Q(activo=True) | Q(pk=puesto_actual))
        if not ver_salario:
            self.fields.pop("salario_referencia")


class PermisoForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = PermisoLaboral
        fields = (
            "tipo",
            "fecha_inicio",
            "fecha_fin",
            "hora_inicio",
            "hora_fin",
            "motivo",
            "observaciones",
        )
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}),
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}),
            "hora_fin": forms.TimeInput(attrs={"type": "time"}),
        }


class DocumentoForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = DocumentoEmpleado
        fields = (
            "tipo_documento",
            "archivo",
            "fecha_emision",
            "fecha_vencimiento",
            "observaciones",
        )
        widgets = {
            "fecha_emision": forms.DateInput(attrs={"type": "date"}),
            "fecha_vencimiento": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, institucion, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_documento"].queryset = TipoDocumentoEmpleado.objects.filter(
            institucion=institucion,
            activo=True,
        )
