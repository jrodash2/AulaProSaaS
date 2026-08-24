from django import forms
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from alumnos.models import AlumnoEncargado,Encargado
from core.forms import AulaProFormMixin
from instituciones.models import UsuarioInstitucion
from tareas.models import EntregaTarea
from tareas.services import sincronizar_entregas_tarea
from tareas.tests import Base

class SampleForm(AulaProFormMixin,forms.Form):
    text=forms.CharField(widget=forms.TextInput(attrs={"class":"custom form-control"}))
    select=forms.ChoiceField(choices=(("a","A"),))
    check=forms.BooleanField(required=False)
    file=forms.FileField(required=False)
    date=forms.DateField(widget=forms.DateInput(attrs={"type":"date"}))
class FormMixinTests(TestCase):
    def test_clases_por_widget_y_sin_duplicados(self):
        f=SampleForm();self.assertEqual(f.fields["text"].widget.attrs["class"].split().count("form-control"),1);self.assertIn("form-select",f.fields["select"].widget.attrs["class"]);self.assertIn("form-check-input",f.fields["check"].widget.attrs["class"]);self.assertIn("form-control",f.fields["file"].widget.attrs["class"]);self.assertIn("form-control",f.fields["date"].widget.attrs["class"])

class PortalTests(Base):
    def setUp(self):
        super().setUp();self.padre=get_user_model().objects.create_user("padre",password="x");self.alumno_user=get_user_model().objects.create_user("alumno",password="x");UsuarioInstitucion.objects.create(usuario=self.padre,institucion=self.a,rol="PADRE");UsuarioInstitucion.objects.create(usuario=self.alumno_user,institucion=self.a,rol="ALUMNO");self.enc=Encargado.objects.create(institucion=self.a,usuario=self.padre,nombres="Madre",apellidos="Demo",telefono="1");AlumnoEncargado.objects.create(institucion=self.a,alumno=self.al,encargado=self.enc,parentesco="MADRE",activo=True);self.al.usuario=self.alumno_user;self.al.save()
    def test_padre_inicia_y_solo_ve_hijo(self):
        self.client.force_login(self.padre);r=self.client.get(reverse("portal:dashboard"));self.assertContains(r,self.al.nombre_completo)
    def test_padre_no_ve_alumno_externo(self):
        otro=self.al.__class__.objects.create(institucion=self.a,primer_nombre="Otro",primer_apellido="X",fecha_nacimiento=self.al.fecha_nacimiento,sexo="M",fecha_ingreso=self.al.fecha_ingreso);self.client.force_login(self.padre);self.assertEqual(self.client.get(reverse("portal:estudiante",args=[otro.pk])).status_code,404)
    def test_alumno_solo_se_ve_a_si_mismo_y_no_finanzas(self):
        self.client.force_login(self.alumno_user);self.assertEqual(self.client.get(reverse("portal:estudiante",args=[self.al.pk])).status_code,200);self.assertEqual(self.client.get(reverse("portal:finanzas",args=[self.al.pk])).status_code,403)
    def test_padre_ve_secciones(self):
        self.client.force_login(self.padre)
        for name in ("asistencia","calificaciones","tareas","finanzas","recibos"):self.assertEqual(self.client.get(reverse("portal:"+name,args=[self.al.pk])).status_code,200)
    def test_alumno_entrega_archivo(self):
        t=self.tarea("PUBLICADA");t.permite_entrega_archivo=True;t.save();sincronizar_entregas_tarea(t);self.client.force_login(self.alumno_user);r=self.client.post(reverse("portal:tarea",args=[self.al.pk,t.pk]),{"archivo":SimpleUploadedFile("tarea.pdf",b"%PDF",content_type="application/pdf")});self.assertEqual(r.status_code,302);self.assertEqual(EntregaTarea.objects.get(tarea=t,alumno=self.al).estado,"ENTREGADA")
