from django import forms

from core.forms import AulaProFormMixin
from .models import ModuloSaaS, Plan, SolicitudCambioPlan, Suscripcion


class PlanForm(AulaProFormMixin, forms.ModelForm):
    # This is deliberately not named ``modulos``: that is the model M2M and
    # ModelForm would try to validate/save it in addition to PlanModulo.
    modulos_seleccionados = forms.MultipleChoiceField(
        choices=(), widget=forms.CheckboxSelectMultiple, label="Módulos incluidos"
    )

    class Meta:
        model = Plan
        fields = ("codigo", "nombre", "descripcion", "precio_mensual", "precio_anual", "max_alumnos", "max_usuarios", "max_docentes", "es_personalizado", "activo", "publico", "orden")
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.modulos_disponibles = list(ModuloSaaS.objects.filter(activo=True).order_by("orden", "nombre"))
        self.fields["modulos_seleccionados"].choices = [(str(modulo.pk), modulo.nombre) for modulo in self.modulos_disponibles]
        if self.instance.pk and not self.is_bound:
            self.fields["modulos_seleccionados"].initial = [str(pk) for pk in ModuloSaaS.objects.filter(configuracion_planes__plan=self.instance, configuracion_planes__habilitado=True, activo=True).values_list("pk", flat=True)]

    def save(self, commit=True):
        plan = super().save(commit)
        if commit:
            seleccionados = {int(pk) for pk in self.cleaned_data["modulos_seleccionados"]}
            for modulo in ModuloSaaS.objects.filter(activo=True):
                from .models import PlanModulo
                PlanModulo.objects.update_or_create(plan=plan, modulo=modulo, defaults={"habilitado": modulo.pk in seleccionados})
        return plan


class SuscripcionForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = Suscripcion
        fields = ("institucion", "plan", "estado", "modalidad", "fecha_inicio", "fecha_fin", "periodo_prueba_hasta", "renovacion_automatica", "max_alumnos_override", "max_usuarios_override", "precio_acordado", "notas_internas")
        widgets = {"fecha_inicio": forms.DateInput(attrs={"type": "date"}), "fecha_fin": forms.DateInput(attrs={"type": "date"}), "periodo_prueba_hasta": forms.DateInput(attrs={"type": "date"}), "notas_internas": forms.Textarea(attrs={"rows": 3})}


class RenovacionForm(AulaProFormMixin, forms.Form):
    periodo = forms.ChoiceField(choices=(("1", "1 mes"), ("12", "12 meses"), ("FECHA", "Fecha personalizada")))
    fecha_fin = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        data = super().clean()
        if data.get("periodo") == "FECHA" and not data.get("fecha_fin"):
            self.add_error("fecha_fin", "Indique la fecha final.")
        return data


class CambioPlanForm(AulaProFormMixin, forms.Form):
    plan = forms.ModelChoiceField(queryset=Plan.objects.filter(activo=True))


class SolicitudCambioPlanForm(AulaProFormMixin, forms.ModelForm):
    class Meta:
        model = SolicitudCambioPlan
        fields = ("plan_solicitado", "mensaje")
        widgets = {"mensaje": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, plan_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        if plan_actual:
            self.fields["plan_solicitado"].queryset = Plan.objects.filter(activo=True, publico=True).exclude(pk=plan_actual.pk)
