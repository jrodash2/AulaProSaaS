from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from academico.models import CicloEscolar,CursoInstitucion,GradoInstitucion,OfertaAcademica,Seccion
from .models import AsignacionDocente,AsignacionGuia,Docente

class Styled:
 def style(self):
  for f in self.fields.values(): f.widget.attrs.setdefault("class","form-check-input" if isinstance(f.widget,forms.CheckboxInput) else "form-select" if isinstance(f.widget,forms.Select) else "form-control")

class DocenteForm(Styled,forms.ModelForm):
 class Meta:
  model=Docente; exclude=("institucion","usuario","codigo","fecha_creacion","fecha_actualizacion")
  widgets={"fecha_nacimiento":forms.DateInput(attrs={"type":"date"}),"fecha_ingreso":forms.DateInput(attrs={"type":"date"}),"direccion":forms.Textarea(attrs={"rows":2}),"observaciones":forms.Textarea(attrs={"rows":2})}
 def __init__(self,*a,**kw): super().__init__(*a,**kw); self.style()
 def clean_fotografia(self):
  foto=self.cleaned_data.get("fotografia")
  if foto and foto.size>3*1024*1024: raise forms.ValidationError("La fotografía no puede superar 3 MB.")
  return foto

class AccesoForm(Styled,forms.Form):
 username=forms.CharField(max_length=150); email=forms.EmailField(); password=forms.CharField(widget=forms.PasswordInput,label="Contraseña inicial")
 def __init__(self,*a,**kw): super().__init__(*a,**kw); self.style()
 def clean_username(self):
  value=self.cleaned_data["username"]
  if get_user_model().objects.filter(username=value).exists(): raise forms.ValidationError("Este username ya existe.")
  return value
 def clean_password(self): value=self.cleaned_data["password"]; validate_password(value); return value

class CrearDocenteForm(DocenteForm):
 crear_acceso=forms.BooleanField(required=False,label="Crear acceso al sistema")
 username=forms.CharField(max_length=150,required=False); email_acceso=forms.EmailField(required=False,label="Email de acceso"); password=forms.CharField(required=False,widget=forms.PasswordInput,label="Contraseña inicial")
 def clean(self):
  c=super().clean()
  if c.get("crear_acceso"):
   for field in ("username","email_acceso","password"):
    if not c.get(field): self.add_error(field,"Este campo es requerido para crear acceso.")
   if c.get("username") and get_user_model().objects.filter(username=c["username"]).exists(): self.add_error("username","Este username ya existe.")
   if c.get("password"):
    try: validate_password(c["password"])
    except forms.ValidationError as exc: self.add_error("password",exc)
  return c

class AsignacionForm(Styled,forms.ModelForm):
 class Meta:
  model=AsignacionDocente; exclude=("institucion","fecha_creacion","fecha_actualizacion")
  widgets={"fecha_inicio":forms.DateInput(attrs={"type":"date"}),"fecha_fin":forms.DateInput(attrs={"type":"date"}),"observaciones":forms.Textarea(attrs={"rows":2})}
 def __init__(self,*a,institucion,**kw):
  super().__init__(*a,**kw)
  self.fields["ciclo"].queryset=CicloEscolar.objects.filter(institucion=institucion,activo=True)
  self.fields["docente"].queryset=Docente.objects.filter(institucion=institucion,estado=Docente.Estado.ACTIVO)
  self.fields["oferta_academica"].queryset=OfertaAcademica.objects.filter(institucion=institucion,activa=True)
  self.fields["grado"].queryset=GradoInstitucion.objects.filter(institucion=institucion,activo=True)
  self.fields["seccion"].queryset=Seccion.objects.filter(institucion=institucion,activa=True)
  self.fields["curso"].queryset=CursoInstitucion.objects.filter(institucion=institucion,activo=True)
  actual=self.fields["ciclo"].queryset.filter(es_actual=True).first()
  if actual and not self.is_bound: self.initial["ciclo"]=actual
  self.style()

class GuiaForm(Styled,forms.ModelForm):
 class Meta: model=AsignacionGuia; fields=("docente","fecha_inicio")
 def __init__(self,*a,institucion,**kw): super().__init__(*a,**kw); self.fields["docente"].queryset=Docente.objects.filter(institucion=institucion,estado=Docente.Estado.ACTIVO); self.style()
