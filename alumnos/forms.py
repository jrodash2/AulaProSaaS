from django import forms
from django.utils import timezone
from academico.models import CicloEscolar, GradoInstitucion, OfertaAcademica, Seccion
from .models import Alumno, AlumnoEncargado, DocumentoAlumno, Encargado, Familia, Inscripcion, RequisitoDocumentoAlumno, TipoDocumentoAlumno

class StyledMixin:
    def style(self):
        for f in self.fields.values(): f.widget.attrs.setdefault("class", "form-check-input" if isinstance(f.widget,forms.CheckboxInput) else "form-select" if isinstance(f.widget,forms.Select) else "form-control")

class AlumnoForm(StyledMixin,forms.ModelForm):
    class Meta:
        model=Alumno; exclude=("institucion","estado_identificacion","fecha_creacion","fecha_actualizacion")
        widgets={"fecha_nacimiento":forms.DateInput(attrs={"type":"date"}),"fecha_ingreso":forms.DateInput(attrs={"type":"date"}),"direccion":forms.Textarea(attrs={"rows":2})}
    def __init__(self,*args,institucion,**kwargs):
        super().__init__(*args,**kwargs); self.fields["familia"].queryset=institucion.familias.filter(activa=True); self.style()
    def clean_fotografia(self):
        foto=self.cleaned_data.get("fotografia")
        if foto and foto.size>3*1024*1024: raise forms.ValidationError("La fotografía no puede superar 3 MB.")
        return foto

class FamiliaForm(StyledMixin,forms.ModelForm):
    class Meta: model=Familia; fields=("nombre_referencia","direccion","telefono_principal","email_principal","observaciones","activa")
    def __init__(self,*a,**kw): super().__init__(*a,**kw); self.style()

class EncargadoForm(StyledMixin,forms.ModelForm):
    class Meta: model=Encargado; exclude=("institucion","fecha_creacion","fecha_actualizacion")
    def __init__(self,*a,**kw): super().__init__(*a,**kw); self.style()

class VinculoForm(StyledMixin,forms.ModelForm):
    class Meta: model=AlumnoEncargado; exclude=("institucion","alumno","encargado")
    def __init__(self,*a,**kw): super().__init__(*a,**kw); self.style()

class InscripcionForm(StyledMixin,forms.ModelForm):
    class Meta:
        model=Inscripcion; exclude=("institucion","alumno","fecha_creacion","fecha_actualizacion","fecha_retiro","motivo_retiro")
        widgets={"fecha_inscripcion":forms.DateInput(attrs={"type":"date"})}
    def __init__(self,*args,institucion,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["ciclo"].queryset=CicloEscolar.objects.filter(institucion=institucion,activo=True)
        self.fields["oferta_academica"].queryset=OfertaAcademica.objects.filter(institucion=institucion,activa=True)
        self.fields["grado"].queryset=GradoInstitucion.objects.filter(institucion=institucion,activo=True)
        self.fields["seccion"].queryset=Seccion.objects.filter(institucion=institucion,activa=True)
        actual=self.fields["ciclo"].queryset.filter(es_actual=True).first()
        if actual and not self.is_bound: self.initial["ciclo"]=actual
        self.style()

class RetiroForm(StyledMixin,forms.Form):
    fecha_retiro=forms.DateField(initial=timezone.localdate,widget=forms.DateInput(attrs={"type":"date"}))
    motivo_retiro=forms.CharField(widget=forms.Textarea(attrs={"rows":3}))
    def __init__(self,*a,**kw): super().__init__(*a,**kw); self.style()

class ImportarForm(StyledMixin,forms.Form):
    ciclo=forms.ModelChoiceField(queryset=CicloEscolar.objects.none())
    archivo=forms.FileField(help_text="Archivo .xlsx de máximo 5 MB")
    def __init__(self,*a,institucion,**kw):
        super().__init__(*a,**kw); self.fields["ciclo"].queryset=CicloEscolar.objects.filter(institucion=institucion,activo=True); self.style()
    def clean_archivo(self):
        f=self.cleaned_data["archivo"]
        if not f.name.lower().endswith(".xlsx"): raise forms.ValidationError("Solo se aceptan archivos .xlsx.")
        if f.size>5*1024*1024: raise forms.ValidationError("El archivo no puede superar 5 MB.")
        if f.read(4)!=b"PK\x03\x04": raise forms.ValidationError("El contenido no corresponde a un archivo XLSX válido.")
        f.seek(0); return f

class TipoDocumentoAlumnoForm(StyledMixin,forms.ModelForm):
    class Meta:model=TipoDocumentoAlumno;exclude=("institucion","fecha_creacion","fecha_actualizacion")
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.style()

class RequisitoDocumentoAlumnoForm(StyledMixin,forms.ModelForm):
    class Meta:model=RequisitoDocumentoAlumno;exclude=("institucion","fecha_creacion","fecha_actualizacion")
    def __init__(self,*a,institucion,**kw):
        super().__init__(*a,**kw);self.fields["tipo_documento"].queryset=TipoDocumentoAlumno.objects.filter(institucion=institucion,activo=True)
        self.fields["aplica_a_oferta"].queryset=OfertaAcademica.objects.filter(institucion=institucion);self.fields["aplica_a_grado"].queryset=GradoInstitucion.objects.filter(institucion=institucion);self.fields["aplica_a_ciclo"].queryset=CicloEscolar.objects.filter(institucion=institucion);self.style()

class DocumentoAlumnoForm(StyledMixin,forms.ModelForm):
    class Meta:
        model=DocumentoAlumno;fields=("tipo_documento","inscripcion","ciclo","archivo","numero_documento","fecha_emision","fecha_vencimiento","observaciones","reemplaza_a")
        widgets={"fecha_emision":forms.DateInput(attrs={"type":"date"}),"fecha_vencimiento":forms.DateInput(attrs={"type":"date"}),"reemplaza_a":forms.HiddenInput()}
    def __init__(self,*a,institucion,alumno,portal=False,**kw):
        super().__init__(*a,**kw)
        self.institucion=institucion;self.alumno=alumno
        self.instance.institucion=institucion;self.instance.alumno=alumno
        tipos=TipoDocumentoAlumno.objects.filter(institucion=institucion,activo=True)
        if portal:tipos=tipos.filter(visible_portal=True)
        self.fields["tipo_documento"].queryset=tipos
        self.fields["inscripcion"].queryset=Inscripcion.objects.filter(institucion=institucion,alumno=alumno).select_related("ciclo","grado","seccion").order_by("-ciclo__anio","-fecha_inscripcion")
        self.fields["ciclo"].queryset=CicloEscolar.objects.filter(institucion=institucion).order_by("-anio")
        self.fields["reemplaza_a"].queryset=DocumentoAlumno.objects.filter(institucion=institucion,alumno=alumno)
        self.style()
    def clean(self):
        data=super().clean();tipo=data.get("tipo_documento");inscripcion=data.get("inscripcion");ciclo=data.get("ciclo");reemplaza=data.get("reemplaza_a")
        if tipo and tipo.institucion_id!=self.institucion.pk:self.add_error("tipo_documento","El tipo no pertenece a la institución.")
        if inscripcion and (inscripcion.institucion_id!=self.institucion.pk or inscripcion.alumno_id!=self.alumno.pk):self.add_error("inscripcion","La inscripción no corresponde al alumno.")
        if ciclo and ciclo.institucion_id!=self.institucion.pk:self.add_error("ciclo","El ciclo no pertenece a la institución.")
        if reemplaza and (reemplaza.institucion_id!=self.institucion.pk or reemplaza.alumno_id!=self.alumno.pk):self.add_error("reemplaza_a","El documento reemplazado no corresponde al alumno.")
        return data
    def clean_archivo(self):
        archivo=self.cleaned_data.get("archivo")
        if not archivo:raise forms.ValidationError("Seleccione un archivo.")
        return archivo

class RevisionDocumentoForm(StyledMixin,forms.Form):
    estado=forms.ChoiceField(choices=(("APROBADO","Aprobar"),("RECHAZADO","Rechazar"),("NO_APLICA","No aplica")))
    motivo=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3}))
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.style()
    def clean(self):
        data=super().clean()
        if data.get("estado") in ("RECHAZADO","NO_APLICA") and not data.get("motivo","").strip():self.add_error("motivo","Indique el motivo.")
        return data
