import os
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models import Max, Q
from django.utils import timezone
from alumnos.models import cui_validator, validar_documento_alumno, EXTENSIONES_DOCUMENTO


def ruta_documento(instance, filename):
    return f"rrhh/documentos/{instance.institucion_id}/{instance.empleado_id}/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()}"


def ruta_contrato(instance, filename):
    return f"rrhh/contratos/{instance.institucion_id}/{instance.empleado_id}/{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()}"


class AreaLaboral(models.Model):
    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="areas_laborales")
    codigo = models.CharField(max_length=40)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    responsable = models.ForeignKey("Empleado", null=True, blank=True, on_delete=models.SET_NULL, related_name="areas_responsable")
    activa = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("orden", "nombre")
        constraints = [models.UniqueConstraint(fields=("institucion", "codigo"), name="rrhh_area_codigo_inst")]

    def clean(self):
        if self.responsable_id and self.responsable.institucion_id != self.institucion_id:
            raise ValidationError({"responsable": "No pertenece a la institución."})

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.upper().strip()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class PuestoLaboral(models.Model):
    class Tipo(models.TextChoices):
        DIRECTIVO = "DIRECTIVO", "Directivo"
        ADMINISTRATIVO = "ADMINISTRATIVO", "Administrativo"
        DOCENTE = "DOCENTE", "Docente"
        OPERATIVO = "OPERATIVO", "Operativo"
        OTRO = "OTRO", "Otro"

    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="puestos_laborales")
    area = models.ForeignKey(AreaLaboral, on_delete=models.PROTECT, related_name="puestos")
    codigo = models.CharField(max_length=40)
    nombre = models.CharField(max_length=140)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=16, choices=Tipo.choices, default=Tipo.ADMINISTRATIVO)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("area__orden", "nombre")
        constraints = [models.UniqueConstraint(fields=("institucion", "codigo"), name="rrhh_puesto_codigo_inst")]

    def clean(self):
        if self.area_id and self.area.institucion_id != self.institucion_id:
            raise ValidationError({"area": "No pertenece a la institución."})

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.upper().strip()
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Empleado(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        SUSPENDIDO = "SUSPENDIDO", "Suspendido"
        LICENCIA = "LICENCIA", "Licencia"
        INACTIVO = "INACTIVO", "Inactivo"
        RETIRADO = "RETIRADO", "Retirado"

    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="empleados")
    nombres = models.CharField(max_length=160)
    apellidos = models.CharField(max_length=160)
    cui = models.CharField(max_length=13, null=True, blank=True, validators=[cui_validator])
    dpi = models.CharField(max_length=13, null=True, blank=True, validators=[cui_validator])
    nit = models.CharField(max_length=20, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, blank=True, choices=(("F", "Femenino"), ("M", "Masculino"), ("O", "Otro")))
    telefono = models.CharField(max_length=30, blank=True)
    correo = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    codigo_empleado = models.CharField(max_length=20, blank=True)
    secuencia = models.PositiveIntegerField(null=True, editable=False)
    puesto = models.ForeignKey(PuestoLaboral, on_delete=models.PROTECT, related_name="empleados")
    area = models.ForeignKey(AreaLaboral, on_delete=models.PROTECT, related_name="empleados")
    fecha_ingreso = models.DateField()
    fecha_egreso = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.ACTIVO)
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="empleado")
    docente = models.OneToOneField("docentes.Docente", null=True, blank=True, on_delete=models.SET_NULL, related_name="empleado")
    foto = models.ImageField(upload_to="rrhh/fotos/", blank=True, validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])])
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="empleados_creados")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("apellidos", "nombres")
        permissions = [("ver_datos_salariales", "Puede ver datos salariales")]
        constraints = [
            models.UniqueConstraint(fields=("institucion", "codigo_empleado"), name="rrhh_empleado_codigo_inst"),
            models.UniqueConstraint(fields=("institucion", "cui"), condition=Q(cui__isnull=False), name="rrhh_empleado_cui_inst"),
            models.UniqueConstraint(fields=("institucion", "dpi"), condition=Q(dpi__isnull=False), name="rrhh_empleado_dpi_inst"),
        ]
        indexes = [models.Index(fields=("institucion", "estado"), name="rrhh_emp_inst_estado")]

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    def clean(self):
        errors = {}
        if self.area_id and self.area.institucion_id != self.institucion_id:
            errors["area"] = "No pertenece a la institución."
        if self.puesto_id and (self.puesto.institucion_id != self.institucion_id or self.puesto.area_id != self.area_id):
            errors["puesto"] = "No corresponde al área e institución."
        if self.usuario_id and not self.usuario.asignaciones_institucion.filter(institucion_id=self.institucion_id, activo=True).exists():
            errors["usuario"] = "El usuario no pertenece a la institución."
        if self.docente_id and self.docente.institucion_id != self.institucion_id:
            errors["docente"] = "No pertenece a la institución."
        if self.fecha_egreso and self.fecha_egreso < self.fecha_ingreso:
            errors["fecha_egreso"] = "Debe ser posterior al ingreso."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.secuencia:
                self.institucion.__class__.objects.select_for_update().get(pk=self.institucion_id)
                self.secuencia = (type(self).objects.filter(institucion=self.institucion).aggregate(m=Max("secuencia"))["m"] or 0) + 1
                self.codigo_empleado = f"EMP-{self.secuencia:05d}"
            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_empleado} · {self.nombre_completo}"


class ContratoLaboral(models.Model):
    class Tipo(models.TextChoices):
        INDEFINIDO = "INDEFINIDO", "Indefinido"
        PLAZO_FIJO = "PLAZO_FIJO", "Plazo fijo"
        SERVICIOS = "SERVICIOS", "Servicios"
        TEMPORAL = "TEMPORAL", "Temporal"
        OTRO = "OTRO", "Otro"
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        VIGENTE = "VIGENTE", "Vigente"
        VENCIDO = "VENCIDO", "Vencido"
        FINALIZADO = "FINALIZADO", "Finalizado"
        ANULADO = "ANULADO", "Anulado"

    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="contratos_laborales")
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name="contratos")
    numero_contrato = models.CharField(max_length=50)
    tipo_contrato = models.CharField(max_length=15, choices=Tipo.choices)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    puesto = models.ForeignKey(PuestoLaboral, on_delete=models.PROTECT)
    jornada_laboral = models.CharField(max_length=100, blank=True)
    salario_referencia = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.BORRADOR)
    observaciones = models.TextField(blank=True)
    motivo_finalizacion = models.TextField(blank=True)
    archivo = models.FileField(upload_to=ruta_contrato, blank=True, validators=[FileExtensionValidator(EXTENSIONES_DOCUMENTO), validar_documento_alumno])
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-fecha_inicio",)
        constraints = [models.UniqueConstraint(fields=("institucion", "numero_contrato"), name="rrhh_contrato_numero_inst")]
        indexes = [models.Index(fields=("institucion", "estado", "fecha_fin"), name="rrhh_contrato_vence")]

    @property
    def estado_vigente(self):
        if self.estado == self.Estado.VIGENTE and self.fecha_fin and self.fecha_fin < timezone.localdate():
            return self.Estado.VENCIDO
        return self.estado

    def clean(self):
        errors = {}
        if self.empleado_id and self.empleado.institucion_id != self.institucion_id:
            errors["empleado"] = "No pertenece a la institución."
        if self.puesto_id and self.puesto.institucion_id != self.institucion_id:
            errors["puesto"] = "No pertenece a la institución."
        if self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            errors["fecha_fin"] = "Debe ser posterior al inicio."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class MovimientoLaboral(models.Model):
    class Tipo(models.TextChoices):
        INGRESO="INGRESO","Ingreso"; CAMBIO_PUESTO="CAMBIO_PUESTO","Cambio de puesto"; CAMBIO_AREA="CAMBIO_AREA","Cambio de área"; RENOVACION="RENOVACION","Renovación"; LICENCIA="LICENCIA","Licencia"; REINTEGRO="REINTEGRO","Reintegro"; EGRESO="EGRESO","Egreso"; OTRO="OTRO","Otro"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name="movimientos");fecha=models.DateField(default=timezone.localdate);tipo=models.CharField(max_length=20,choices=Tipo.choices);puesto_anterior=models.ForeignKey(PuestoLaboral,null=True,blank=True,on_delete=models.PROTECT,related_name="movimientos_origen");puesto_nuevo=models.ForeignKey(PuestoLaboral,null=True,blank=True,on_delete=models.PROTECT,related_name="movimientos_destino");area_anterior=models.ForeignKey(AreaLaboral,null=True,blank=True,on_delete=models.PROTECT,related_name="movimientos_origen");area_nueva=models.ForeignKey(AreaLaboral,null=True,blank=True,on_delete=models.PROTECT,related_name="movimientos_destino");descripcion=models.TextField();registrado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL);fecha_creacion=models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.empleado_id and self.empleado.institucion_id!=self.institucion_id:raise ValidationError("Tenant inválido.")
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)

class TipoDocumentoEmpleado(models.Model):
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);codigo=models.CharField(max_length=40);nombre=models.CharField(max_length=140);descripcion=models.TextField(blank=True);obligatorio=models.BooleanField(default=True);requiere_vigencia=models.BooleanField(default=False);puesto=models.ForeignKey(PuestoLaboral,null=True,blank=True,on_delete=models.PROTECT);area=models.ForeignKey(AreaLaboral,null=True,blank=True,on_delete=models.PROTECT);activo=models.BooleanField(default=True);orden=models.PositiveSmallIntegerField(default=0)
    class Meta:constraints=[models.UniqueConstraint(fields=("institucion","codigo"),name="rrhh_tipo_doc_codigo")]
    def clean(self):
        for f in ("puesto","area"):
            o=getattr(self,f,None)
            if o and o.institucion_id!=self.institucion_id:raise ValidationError({f:"No pertenece a la institución."})
    def save(self,*a,**kw):self.codigo=self.codigo.upper().strip();self.full_clean();return super().save(*a,**kw)

class DocumentoEmpleado(models.Model):
    class Estado(models.TextChoices):ENTREGADO="ENTREGADO","Entregado";APROBADO="APROBADO","Aprobado";RECHAZADO="RECHAZADO","Rechazado";NO_APLICA="NO_APLICA","No aplica"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE);empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name="documentos");tipo_documento=models.ForeignKey(TipoDocumentoEmpleado,on_delete=models.PROTECT);archivo=models.FileField(upload_to=ruta_documento,blank=True,validators=[FileExtensionValidator(EXTENSIONES_DOCUMENTO),validar_documento_alumno]);nombre_original=models.CharField(max_length=255,blank=True);fecha_emision=models.DateField(null=True,blank=True);fecha_vencimiento=models.DateField(null=True,blank=True);estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.ENTREGADO);observaciones=models.TextField(blank=True);cargado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="documentos_empleado_cargados");revisado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="documentos_empleado_revisados");fecha_carga=models.DateTimeField(auto_now_add=True)
    @property
    def estado_vigente(self):return "VENCIDO" if self.fecha_vencimiento and self.fecha_vencimiento<timezone.localdate() and self.estado=="APROBADO" else self.estado
    def clean(self):
        if self.empleado_id and (self.empleado.institucion_id!=self.institucion_id or self.tipo_documento.institucion_id!=self.institucion_id):raise ValidationError("Tenant inválido.")
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)

class PermisoLaboral(models.Model):
    class Tipo(models.TextChoices):PERSONAL="PERSONAL","Personal";MEDICO="MEDICO","Médico";VACACIONES="VACACIONES","Vacaciones";LICENCIA="LICENCIA","Licencia";CITA="CITA","Cita";ESTUDIO="ESTUDIO","Estudio";OTRO="OTRO","Otro"
    class Estado(models.TextChoices):PENDIENTE="PENDIENTE","Pendiente";APROBADO="APROBADO","Aprobado";RECHAZADO="RECHAZADO","Rechazado";CANCELADO="CANCELADO","Cancelado"
    institucion=models.ForeignKey("instituciones.Institucion",on_delete=models.CASCADE,related_name="permisos_laborales");empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name="permisos");tipo=models.CharField(max_length=12,choices=Tipo.choices);fecha_inicio=models.DateField();fecha_fin=models.DateField();hora_inicio=models.TimeField(null=True,blank=True);hora_fin=models.TimeField(null=True,blank=True);motivo=models.TextField();observaciones=models.TextField(blank=True);estado=models.CharField(max_length=12,choices=Estado.choices,default=Estado.PENDIENTE);solicitado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL,related_name="permisos_solicitados");autorizado_por=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name="permisos_autorizados");fecha_solicitud=models.DateTimeField(auto_now_add=True);fecha_resolucion=models.DateTimeField(null=True,blank=True)
    class Meta:indexes=[models.Index(fields=("institucion","estado","fecha_inicio"),name="rrhh_permiso_estado")]
    def clean(self):
        e={}
        if self.empleado_id and self.empleado.institucion_id!=self.institucion_id:e["empleado"]="No pertenece a la institución."
        if self.fecha_fin and self.fecha_inicio and self.fecha_fin<self.fecha_inicio:e["fecha_fin"]="Debe ser posterior al inicio."
        if self.hora_fin and self.hora_inicio and self.fecha_inicio==self.fecha_fin and self.hora_fin<=self.hora_inicio:e["hora_fin"]="Debe ser posterior."
        if e:raise ValidationError(e)
    def save(self,*a,**kw):self.full_clean();return super().save(*a,**kw)
