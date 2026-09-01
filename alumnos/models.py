from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
import os
import uuid

cui_validator = RegexValidator(r"^\d{13}$", "El CUI debe contener exactamente 13 dígitos.")


class Familia(models.Model):
    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="familias")
    codigo = models.CharField(max_length=20, null=True, blank=True)
    nombre_referencia = models.CharField(max_length=180)
    direccion = models.TextField(blank=True)
    telefono_principal = models.CharField(max_length=30, blank=True)
    email_principal = models.EmailField(blank=True)
    observaciones = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre_referencia",)
        constraints = [models.UniqueConstraint(fields=("institucion", "codigo"), condition=Q(codigo__isnull=False), name="familia_codigo_unico_institucion")]
        indexes = [models.Index(fields=("institucion", "activa"), name="familia_inst_activa_idx")]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.full_clean()
            super().save(*args, **kwargs)
            if not self.codigo:
                self.codigo = f"FAM-{self.pk:06d}"
                type(self).objects.filter(pk=self.pk).update(codigo=self.codigo)
        return self

    def __str__(self): return self.nombre_referencia


class Alumno(models.Model):
    class EstadoIdentificacion(models.TextChoices):
        VALIDADO = "VALIDADO", "Validado"
        PENDIENTE = "PENDIENTE", "Pendiente"
    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        INACTIVO = "INACTIVO", "Inactivo"
        RETIRADO = "RETIRADO", "Retirado"
        EGRESADO = "EGRESADO", "Egresado"
    class Sexo(models.TextChoices):
        FEMENINO = "F", "Femenino"
        MASCULINO = "M", "Masculino"
        OTRO = "O", "Otro / no especificado"

    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="alumnos")
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="perfil_alumno")
    familia = models.ForeignKey(Familia, null=True, blank=True, on_delete=models.SET_NULL, related_name="alumnos")
    cui = models.CharField(max_length=13, null=True, blank=True, validators=[cui_validator])
    estado_identificacion = models.CharField(max_length=12, choices=EstadoIdentificacion.choices, default=EstadoIdentificacion.PENDIENTE)
    codigo_interno = models.CharField(max_length=40, blank=True)
    primer_nombre = models.CharField(max_length=60)
    segundo_nombre = models.CharField(max_length=60, blank=True)
    otros_nombres = models.CharField(max_length=100, blank=True)
    primer_apellido = models.CharField(max_length=60)
    segundo_apellido = models.CharField(max_length=60, blank=True)
    apellido_casada = models.CharField(max_length=60, blank=True)
    fecha_nacimiento = models.DateField()
    sexo = models.CharField(max_length=1, choices=Sexo.choices)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    departamento = models.CharField(max_length=80, blank=True)
    municipio = models.CharField(max_length=80, blank=True)
    fotografia = models.ImageField(upload_to="alumnos/fotografias/", blank=True, validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])])
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
    fecha_ingreso = models.DateField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("primer_apellido", "segundo_apellido", "primer_nombre")
        constraints = [models.UniqueConstraint(fields=("institucion", "cui"), condition=Q(cui__isnull=False), name="alumno_cui_unico_institucion")]
        indexes = [models.Index(fields=("institucion", "estado"), name="alumno_inst_estado_idx"), models.Index(fields=("institucion", "primer_apellido", "primer_nombre"), name="alumno_nombre_idx")]

    @property
    def nombre_completo(self):
        return " ".join(filter(None, [self.primer_nombre, self.segundo_nombre, self.otros_nombres, self.primer_apellido, self.segundo_apellido, self.apellido_casada]))

    def clean(self):
        errors = {}
        if self.cui:
            self.estado_identificacion = self.EstadoIdentificacion.VALIDADO
        elif self.estado_identificacion == self.EstadoIdentificacion.VALIDADO:
            errors["cui"] = "Un alumno validado debe tener CUI."
        if self.familia_id and self.familia.institucion_id != self.institucion_id:
            errors["familia"] = "La familia debe pertenecer a la institución."
        if errors: raise ValidationError(errors)

    def save(self, *args, **kwargs): self.full_clean(); return super().save(*args, **kwargs)
    def __str__(self): return self.nombre_completo


class Encargado(models.Model):
    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="encargados")
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="perfil_encargado")
    cui = models.CharField(max_length=13, null=True, blank=True, validators=[cui_validator])
    nombres = models.CharField(max_length=160)
    apellidos = models.CharField(max_length=160)
    telefono = models.CharField(max_length=30)
    telefono_secundario = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    ocupacion = models.CharField(max_length=120, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("apellidos", "nombres")
        constraints = [models.UniqueConstraint(fields=("institucion", "cui"), condition=Q(cui__isnull=False), name="encargado_cui_unico_institucion")]
        indexes = [models.Index(fields=("institucion", "activo"), name="encargado_inst_activo_idx")]
    @property
    def nombre_completo(self): return f"{self.nombres} {self.apellidos}".strip()
    def save(self, *args, **kwargs): self.full_clean(); return super().save(*args, **kwargs)
    def __str__(self): return self.nombre_completo


class AlumnoEncargado(models.Model):
    class Parentesco(models.TextChoices):
        MADRE="MADRE","Madre"; PADRE="PADRE","Padre"; ABUELO="ABUELO","Abuelo"; ABUELA="ABUELA","Abuela"; TUTOR="TUTOR","Tutor"; HERMANO="HERMANO","Hermano"; HERMANA="HERMANA","Hermana"; OTRO="OTRO","Otro"
    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="vinculos_encargados")
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="vinculos_encargados")
    encargado = models.ForeignKey(Encargado, on_delete=models.CASCADE, related_name="vinculos_alumnos")
    parentesco = models.CharField(max_length=12, choices=Parentesco.choices)
    parentesco_otro = models.CharField(max_length=80, blank=True)
    es_principal = models.BooleanField(default=False)
    es_responsable_financiero = models.BooleanField(default=False)
    es_contacto_emergencia = models.BooleanField(default=False)
    autorizado_recoger = models.BooleanField(default=False)
    convive_con_alumno = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=("alumno","encargado"), name="alumno_encargado_unico")]
        indexes=[models.Index(fields=("institucion","activo"), name="vinculo_inst_activo_idx")]
    def clean(self):
        if self.alumno_id and self.encargado_id and (self.alumno.institucion_id != self.institucion_id or self.encargado.institucion_id != self.institucion_id): raise ValidationError("Alumno y encargado deben pertenecer a la institución.")
        if self.parentesco == self.Parentesco.OTRO and not self.parentesco_otro: raise ValidationError({"parentesco_otro":"Especifique el parentesco."})
    def save(self,*args,**kwargs): self.full_clean(); return super().save(*args,**kwargs)


class Inscripcion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR="BORRADOR","Borrador"; ACTIVA="ACTIVA","Activa"; RETIRADA="RETIRADA","Retirada"; TRASLADADA="TRASLADADA","Trasladada"; FINALIZADA="FINALIZADA","Finalizada"; ANULADA="ANULADA","Anulada"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="inscripciones")
    alumno=models.ForeignKey(Alumno,on_delete=models.PROTECT,related_name="inscripciones")
    ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="inscripciones")
    oferta_academica=models.ForeignKey("academico.OfertaAcademica",on_delete=models.PROTECT,related_name="inscripciones")
    grado=models.ForeignKey("academico.GradoInstitucion",on_delete=models.PROTECT,related_name="inscripciones")
    seccion=models.ForeignKey("academico.Seccion",on_delete=models.PROTECT,related_name="inscripciones")
    fecha_inscripcion=models.DateField()
    numero_inscripcion=models.CharField(max_length=40,blank=True)
    estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.ACTIVA)
    es_reingreso=models.BooleanField(default=False)
    observaciones=models.TextField(blank=True)
    fecha_retiro=models.DateField(null=True,blank=True)
    motivo_retiro=models.TextField(blank=True)
    fecha_creacion=models.DateTimeField(auto_now_add=True)
    fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("-ciclo__anio","alumno__primer_apellido")
        constraints=[models.UniqueConstraint(fields=("alumno","ciclo"),condition=Q(estado="ACTIVA"),name="inscripcion_activa_unica_ciclo")]
        indexes=[models.Index(fields=("institucion","ciclo","estado"),name="inscripcion_inst_ciclo_idx")]
    def clean(self):
        errors={}
        if self.alumno_id and self.alumno.institucion_id != self.institucion_id: errors["alumno"]="El alumno no pertenece a la institución."
        if self.ciclo_id and self.ciclo.institucion_id != self.institucion_id: errors["ciclo"]="El ciclo no pertenece a la institución."
        if self.oferta_academica_id and (self.oferta_academica.institucion_id != self.institucion_id or self.oferta_academica.ciclo_id != self.ciclo_id): errors["oferta_academica"]="La oferta no corresponde a la institución y ciclo."
        if self.grado_id and (self.grado.institucion_id != self.institucion_id or self.grado.ciclo_id != self.ciclo_id or self.grado.oferta_id != self.oferta_academica_id): errors["grado"]="El grado no corresponde a la oferta."
        if self.seccion_id and (self.seccion.institucion_id != self.institucion_id or self.seccion.ciclo_id != self.ciclo_id or self.seccion.grado_id != self.grado_id): errors["seccion"]="La sección no corresponde al grado."
        if self.estado == self.Estado.RETIRADA and (not self.fecha_retiro or not self.motivo_retiro): errors["motivo_retiro"]="Indique fecha y motivo del retiro."
        if errors: raise ValidationError(errors)
    def save(self,*args,**kwargs):
        with transaction.atomic():
            from instituciones.models import Institucion
            Institucion.objects.select_for_update().get(pk=self.institucion_id)
            activa_nueva=self.estado==self.Estado.ACTIVA and (not self.pk or not type(self).objects.filter(pk=self.pk,estado=self.Estado.ACTIVA).exists())
            if activa_nueva:
                from suscripciones.services import suscripcion_actual
                suscripcion = suscripcion_actual(self.institucion)
                usados = type(self).objects.filter(institucion=self.institucion, ciclo=self.ciclo, estado=self.Estado.ACTIVA).count()
                if suscripcion and suscripcion.limite_alumnos is not None and usados + 1 > suscripcion.limite_alumnos:
                    raise ValidationError(f"Has alcanzado el límite de {suscripcion.limite_alumnos} estudiantes para este ciclo.")
            if self.ciclo_id and self.ciclo.cerrado and self.estado in (self.Estado.BORRADOR, self.Estado.ACTIVA):
                raise ValidationError("Un ciclo cerrado no admite nuevas inscripciones activas.")
            self.full_clean(); return super().save(*args,**kwargs)


class ImportacionAlumnos(models.Model):
    class Estado(models.TextChoices): VALIDANDO="VALIDANDO","Validando"; LISTA="LISTA","Lista"; PROCESADA="PROCESADA","Procesada"; FALLIDA="FALLIDA","Fallida"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="importaciones_alumnos")
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="importaciones_alumnos")
    ciclo=models.ForeignKey("academico.CicloEscolar",on_delete=models.PROTECT,related_name="importaciones_alumnos")
    archivo_original=models.FileField(upload_to="alumnos/importaciones/",blank=True)
    nombre_archivo=models.CharField(max_length=255)
    estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.VALIDANDO)
    total_filas=models.PositiveIntegerField(default=0); creados=models.PositiveIntegerField(default=0); actualizados=models.PositiveIntegerField(default=0); inscripciones_creadas=models.PositiveIntegerField(default=0); errores=models.PositiveIntegerField(default=0)
    detalle_errores=models.JSONField(default=list,blank=True)
    fecha_inicio=models.DateTimeField(auto_now_add=True); fecha_fin=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=("-fecha_inicio",); indexes=[models.Index(fields=("institucion","estado"),name="import_inst_estado_idx")]
    def clean(self):
        if self.ciclo_id and self.ciclo.institucion_id != self.institucion_id:
            raise ValidationError({"ciclo":"El ciclo de importación no pertenece a la institución."})
    def save(self,*args,**kwargs): self.full_clean(); return super().save(*args,**kwargs)


class TipoDocumentoAlumno(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="tipos_documento_alumno")
    codigo=models.CharField(max_length=40);nombre=models.CharField(max_length=140);descripcion=models.TextField(blank=True)
    obligatorio=models.BooleanField(default=True);requiere_vigencia=models.BooleanField(default=False);permite_multiples=models.BooleanField(default=False);visible_portal=models.BooleanField(default=False);activo=models.BooleanField(default=True);orden=models.PositiveSmallIntegerField(default=0)
    fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=("orden","nombre");constraints=[models.UniqueConstraint(fields=("institucion","codigo"),name="tipo_doc_codigo_unico_inst")]
    def save(self,*a,**kw):self.codigo=self.codigo.upper().strip();self.full_clean();return super().save(*a,**kw)
    def __str__(self):return self.nombre


class RequisitoDocumentoAlumno(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="requisitos_documentales")
    tipo_documento=models.ForeignKey(TipoDocumentoAlumno,on_delete=models.PROTECT,related_name="requisitos")
    obligatorio=models.BooleanField(default=True)
    aplica_a_nivel=models.ForeignKey("catalogos.NivelEducativo",null=True,blank=True,on_delete=models.PROTECT,related_name="requisitos_documentales")
    aplica_a_oferta=models.ForeignKey("academico.OfertaAcademica",null=True,blank=True,on_delete=models.PROTECT,related_name="requisitos_documentales")
    aplica_a_grado=models.ForeignKey("academico.GradoInstitucion",null=True,blank=True,on_delete=models.PROTECT,related_name="requisitos_documentales")
    aplica_a_ciclo=models.ForeignKey("academico.CicloEscolar",null=True,blank=True,on_delete=models.PROTECT,related_name="requisitos_documentales")
    activo=models.BooleanField(default=True);fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:constraints=[models.UniqueConstraint(fields=("institucion","tipo_documento","aplica_a_nivel","aplica_a_oferta","aplica_a_grado","aplica_a_ciclo"),name="requisito_doc_alcance_unico")]
    def clean(self):
        e={}
        if self.tipo_documento_id and self.tipo_documento.institucion_id!=self.institucion_id:e["tipo_documento"]="El tipo no pertenece a la institución."
        for campo in ("aplica_a_oferta","aplica_a_grado","aplica_a_ciclo"):
            obj=getattr(self,campo,None)
            if obj and obj.institucion_id!=self.institucion_id:e[campo]="El alcance no pertenece a la institución."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)


EXTENSIONES_DOCUMENTO=("pdf","jpg","jpeg","png","webp")
def ruta_documento_alumno(instance,filename):
    ext=os.path.splitext(filename)[1].lower()
    return f"alumnos/documentos/{instance.institucion_id}/{instance.alumno_id}/{uuid.uuid4().hex}{ext}"
def validar_documento_alumno(archivo):
    ext=os.path.splitext(archivo.name)[1].lower().lstrip(".")
    if ext not in EXTENSIONES_DOCUMENTO:raise ValidationError("Solo se permiten archivos PDF, JPG, PNG o WEBP.")
    if archivo.size>getattr(settings,"DOCUMENTO_ALUMNO_MAX_SIZE",10*1024*1024):raise ValidationError("El archivo no puede superar 10 MB.")
    cabecera=archivo.read(16);archivo.seek(0)
    firmas={"pdf":(b"%PDF",),"jpg":(b"\xff\xd8\xff",),"jpeg":(b"\xff\xd8\xff",),"png":(b"\x89PNG\r\n\x1a\n",),"webp":(b"RIFF",)}
    if not any(cabecera.startswith(firma) for firma in firmas[ext]):raise ValidationError("El contenido no coincide con el tipo de archivo permitido.")
    if ext=="webp" and cabecera[8:12]!=b"WEBP":raise ValidationError("El contenido no corresponde a una imagen WEBP.")


class DocumentoAlumno(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE="PENDIENTE","Pendiente";ENTREGADO="ENTREGADO","Entregado";APROBADO="APROBADO","Aprobado";RECHAZADO="RECHAZADO","Rechazado";VENCIDO="VENCIDO","Vencido";NO_APLICA="NO_APLICA","No aplica"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="documentos_alumnos")
    alumno=models.ForeignKey(Alumno,on_delete=models.PROTECT,related_name="documentos")
    tipo_documento=models.ForeignKey(TipoDocumentoAlumno,on_delete=models.PROTECT,related_name="documentos")
    inscripcion=models.ForeignKey(Inscripcion,null=True,blank=True,on_delete=models.PROTECT,related_name="documentos")
    ciclo=models.ForeignKey("academico.CicloEscolar",null=True,blank=True,on_delete=models.PROTECT,related_name="documentos_alumnos")
    estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.ENTREGADO)
    archivo=models.FileField(upload_to=ruta_documento_alumno,validators=[FileExtensionValidator(EXTENSIONES_DOCUMENTO),validar_documento_alumno],blank=True)
    nombre_original=models.CharField(max_length=255,blank=True);numero_documento=models.CharField(max_length=100,blank=True)
    fecha_emision=models.DateField(null=True,blank=True);fecha_vencimiento=models.DateField(null=True,blank=True)
    observaciones=models.TextField(blank=True);motivo_rechazo=models.TextField(blank=True)
    cargado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="documentos_alumno_cargados")
    revisado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="documentos_alumno_revisados")
    fecha_carga=models.DateTimeField(auto_now_add=True);fecha_revision=models.DateTimeField(null=True,blank=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    reemplaza_a=models.ForeignKey("self",null=True,blank=True,on_delete=models.PROTECT,related_name="reemplazos")
    class Meta:ordering=("-fecha_carga",);indexes=[models.Index(fields=("institucion","alumno","estado"),name="doc_alumno_estado_idx")]
    @property
    def estado_vigente(self):
        return self.Estado.VENCIDO if self.fecha_vencimiento and self.fecha_vencimiento<timezone.localdate() and self.estado==self.Estado.APROBADO else self.estado
    def clean(self):
        e={}
        if self.alumno_id and self.alumno.institucion_id!=self.institucion_id:e["alumno"]="El alumno no pertenece a la institución."
        if self.tipo_documento_id and self.tipo_documento.institucion_id!=self.institucion_id:e["tipo_documento"]="El tipo no pertenece a la institución."
        if self.inscripcion_id and (self.inscripcion.institucion_id!=self.institucion_id or self.inscripcion.alumno_id!=self.alumno_id):e["inscripcion"]="La inscripción no corresponde al alumno."
        if self.ciclo_id and self.ciclo.institucion_id!=self.institucion_id:e["ciclo"]="El ciclo no pertenece a la institución."
        if self.estado==self.Estado.RECHAZADO and not self.motivo_rechazo.strip():e["motivo_rechazo"]="Indique el motivo del rechazo."
        if self.estado==self.Estado.NO_APLICA and not self.observaciones.strip():e["observaciones"]="Indique por qué no aplica."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):
        if self.archivo and not self.nombre_original:self.nombre_original=os.path.basename(self.archivo.name)[:255]
        self.full_clean();return super().save(*a,**kw)
