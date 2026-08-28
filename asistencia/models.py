from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class SesionAsistencia(models.Model):
    class Tipo(models.TextChoices):
        GENERAL = "GENERAL", "General"
        CURSO = "CURSO", "Por curso"
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ABIERTA = "ABIERTA", "Abierta"
        CERRADA = "CERRADA", "Cerrada"
        ANULADA = "ANULADA", "Anulada"

    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="sesiones_asistencia")
    ciclo = models.ForeignKey("academico.CicloEscolar", on_delete=models.PROTECT, related_name="sesiones_asistencia")
    fecha = models.DateField()
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    oferta_academica = models.ForeignKey("academico.OfertaAcademica", on_delete=models.PROTECT, related_name="sesiones_asistencia")
    grado = models.ForeignKey("academico.GradoInstitucion", on_delete=models.PROTECT, related_name="sesiones_asistencia")
    seccion = models.ForeignKey("academico.Seccion", on_delete=models.PROTECT, related_name="sesiones_asistencia")
    curso = models.ForeignKey("academico.CursoInstitucion", null=True, blank=True, on_delete=models.PROTECT, related_name="sesiones_asistencia")
    asignacion_docente = models.ForeignKey("docentes.AsignacionDocente", null=True, blank=True, on_delete=models.PROTECT, related_name="sesiones_asistencia")
    docente = models.ForeignKey("docentes.Docente", null=True, blank=True, on_delete=models.PROTECT, related_name="sesiones_asistencia")
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ABIERTA)
    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="sesiones_asistencia_creadas")
    cerrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="sesiones_asistencia_cerradas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    motivo_reapertura = models.TextField(blank=True)
    reabierta_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="sesiones_asistencia_reabiertas")
    fecha_reapertura = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.TextField(blank=True)
    anulada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="sesiones_asistencia_anuladas")
    fecha_anulacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-fecha", "grado__orden", "seccion__nombre")
        constraints = [
            models.UniqueConstraint(fields=("institucion", "fecha", "seccion"), condition=Q(tipo="GENERAL") & ~Q(estado="ANULADA"), name="asistencia_general_unica_activa"),
            models.UniqueConstraint(fields=("institucion", "fecha", "seccion", "curso"), condition=Q(tipo="CURSO") & ~Q(estado="ANULADA"), name="asistencia_curso_unica_activa"),
        ]
        indexes = [models.Index(fields=("institucion", "fecha"), name="asist_inst_fecha_idx"), models.Index(fields=("institucion", "ciclo"), name="asist_inst_ciclo_idx")]

    def clean(self):
        errors = {}
        if self._state.adding and self.ciclo_id and self.ciclo.cerrado: errors["ciclo"] = "El ciclo está cerrado y no admite nuevas sesiones."
        related = (("ciclo", self.ciclo_id), ("oferta_academica", self.oferta_academica_id), ("grado", self.grado_id), ("seccion", self.seccion_id))
        for field, pk in related:
            if pk and getattr(self, field).institucion_id != self.institucion_id:
                errors[field] = "Debe pertenecer a la institución."
        if self.oferta_academica_id and self.oferta_academica.ciclo_id != self.ciclo_id: errors["oferta_academica"] = "La oferta no corresponde al ciclo."
        if self.grado_id and (self.grado.ciclo_id != self.ciclo_id or self.grado.oferta_id != self.oferta_academica_id): errors["grado"] = "El grado no corresponde a la oferta."
        if self.seccion_id and (self.seccion.ciclo_id != self.ciclo_id or self.seccion.grado_id != self.grado_id): errors["seccion"] = "La sección no corresponde al grado."
        if self.tipo == self.Tipo.GENERAL and (self.curso_id or self.asignacion_docente_id): errors["curso"] = "Una asistencia general no puede tener curso ni asignación."
        if self.tipo == self.Tipo.CURSO and not self.curso_id: errors["curso"] = "Seleccione el curso."
        if self.curso_id and (self.curso.institucion_id != self.institucion_id or self.curso.ciclo_id != self.ciclo_id or self.curso.grado_id != self.grado_id): errors["curso"] = "El curso no corresponde a la estructura seleccionada."
        if self.asignacion_docente_id:
            a = self.asignacion_docente
            if a.institucion_id != self.institucion_id or a.ciclo_id != self.ciclo_id or a.seccion_id != self.seccion_id or a.curso_id != self.curso_id: errors["asignacion_docente"] = "La asignación no corresponde a la sesión."
            if self.docente_id and a.docente_id != self.docente_id: errors["docente"] = "El docente no corresponde a la asignación."
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio: errors["hora_fin"] = "Debe ser posterior a la hora inicial."
        if errors: raise ValidationError(errors)

    def save(self, *args, **kwargs): self.full_clean(); return super().save(*args, **kwargs)
    def __str__(self): return f"{self.get_tipo_display()} · {self.seccion} · {self.fecha:%d/%m/%Y}"


class RegistroAsistencia(models.Model):
    class Estado(models.TextChoices):
        SIN_MARCAR = "SIN_MARCAR", "Sin marcar"
        PRESENTE = "PRESENTE", "Presente"
        AUSENTE = "AUSENTE", "Ausente"
        TARDE = "TARDE", "Tarde"

    institucion = models.ForeignKey("instituciones.Institucion", on_delete=models.CASCADE, related_name="registros_asistencia")
    sesion = models.ForeignKey(SesionAsistencia, on_delete=models.CASCADE, related_name="registros")
    alumno = models.ForeignKey("alumnos.Alumno", on_delete=models.PROTECT, related_name="registros_asistencia")
    inscripcion = models.ForeignKey("alumnos.Inscripcion", on_delete=models.PROTECT, related_name="registros_asistencia")
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.SIN_MARCAR)
    hora_registro = models.TimeField(null=True, blank=True)
    observacion = models.TextField(blank=True)
    justificada = models.BooleanField(default=False)
    motivo_justificacion = models.TextField(blank=True)
    justificada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="ausencias_justificadas")
    fecha_justificacion = models.DateTimeField(null=True, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="registros_asistencia_realizados")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("alumno__primer_apellido", "alumno__primer_nombre")
        constraints = [models.UniqueConstraint(fields=("sesion", "alumno"), name="registro_asistencia_unico_alumno")]
        indexes = [models.Index(fields=("sesion", "estado"), name="registro_sesion_estado_idx"), models.Index(fields=("alumno", "sesion"), name="registro_alumno_sesion_idx")]

    def clean(self):
        errors = {}
        if self.sesion_id and self.sesion.institucion_id != self.institucion_id: errors["sesion"] = "La sesión no pertenece a la institución."
        if self.alumno_id and self.alumno.institucion_id != self.institucion_id: errors["alumno"] = "El alumno no pertenece a la institución."
        if self.inscripcion_id:
            i = self.inscripcion
            if i.institucion_id != self.institucion_id: errors["inscripcion"] = "La inscripción no pertenece a la institución."
            elif self.alumno_id and i.alumno_id != self.alumno_id: errors["inscripcion"] = "La inscripción no corresponde al alumno."
            elif self.sesion_id and (i.ciclo_id != self.sesion.ciclo_id or i.seccion_id != self.sesion.seccion_id): errors["inscripcion"] = "La inscripción no corresponde al ciclo y sección de la sesión."
        if self.justificada and self.estado != self.Estado.AUSENTE: errors["justificada"] = "Solo una ausencia puede justificarse."
        if self.justificada and not self.motivo_justificacion.strip(): errors["motivo_justificacion"] = "Indique el motivo de la justificación."
        if errors: raise ValidationError(errors)

    def save(self, *args, **kwargs): self.full_clean(); return super().save(*args, **kwargs)
