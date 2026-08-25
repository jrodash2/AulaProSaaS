from django import forms
from core.forms import AulaProFormMixin
class FiltroGlobalForm(AulaProFormMixin,forms.Form):
 ciclo=forms.ChoiceField(required=False);oferta=forms.ChoiceField(required=False);grado=forms.ChoiceField(required=False);seccion=forms.ChoiceField(required=False);desde=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}));hasta=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}))
