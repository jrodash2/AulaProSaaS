from datetime import date, time
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from academico.models import (
    CicloEscolar,
    CursoInstitucion,
    GradoInstitucion,
    JornadaInstitucion,
    OfertaAcademica,
    Seccion,
)
from alumnos.models import Alumno, AlumnoEncargado, Encargado, Familia, Inscripcion
from asistencia.models import RegistroAsistencia, SesionAsistencia
from calificaciones.models import (
    ActividadEvaluacion,
    Calificacion,
    ConfiguracionCalificaciones,
    PeriodoAcademico,
    TipoEvaluacion,
)
from catalogos.models import NivelEducativo
from docentes.models import AsignacionDocente, AsignacionGuia, Docente
from instituciones.models import Institucion, UsuarioInstitucion


DEMO_CODE = "AULAPRO-DEMO"
DEFAULT_PASSWORD = "AulaProDemo2026!"


class Command(BaseCommand):
    help = (
        "Crea una institución demo, usuarios por rol y datos académicos de prueba. "
        "Es idempotente y está pensada para desarrollo/QA."
    )

    def add_arguments(self, parser):
        parser.add_argument("--password", default=DEFAULT_PASSWORD)
        parser.add_argument("--allow-production-demo", action="store_true", help="Alias compatible para permitir datos demo en producción.")
        parser.add_argument(
            "--permitir-produccion",
            action="store_true",
            help="Permite ejecutar el comando con DEBUG=False. Úselo solo en un entorno demo controlado.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not (options["permitir_produccion"] or options["allow_production_demo"]):
            raise CommandError(
                "Por seguridad, este comando solo se ejecuta con DEBUG=True. "
                "Use --permitir-produccion únicamente en un entorno demo controlado."
            )

        password = options["password"]
        # Mantiene compatibilidad con el comando demo histórico del módulo tareas.
        # Django resuelve nombres de comandos duplicados según INSTALLED_APPS.
        if options["allow_production_demo"]:
            from tareas.management.commands.crear_demo_aulapro import Command as TareasDemoCommand
            comando = TareasDemoCommand(); comando.stdout = self.stdout; comando.stderr = self.stderr
            comando.handle(allow_production_demo=True)
            return
        User = get_user_model()

        institucion, _ = Institucion.objects.update_or_create(
            codigo=DEMO_CODE,
            defaults={
                "nombre": "Colegio Demo AulaPro",
                "nombre_corto": "AulaPro Demo",
                "razon_social": "Colegio Demo AulaPro",
                "direccion": "Zona 1, Ciudad de Guatemala",
                "departamento": "Guatemala",
                "municipio": "Guatemala",
                "telefono": "2300-0000",
                "email": "demo@aulapro.local",
                "color_primario": "#2563EB",
                "color_secundario": "#4F46E5",
                "activa": True,
            },
        )

        cuentas = [
            ("demo_propietario", "Propietario", "Demo", UsuarioInstitucion.Rol.PROPIETARIO),
            ("demo_director", "Director", "Demo", UsuarioInstitucion.Rol.DIRECTOR),
            ("demo_admin", "Administrador", "Demo", UsuarioInstitucion.Rol.ADMINISTRADOR),
            ("demo_secretaria", "Secretaria", "Demo", UsuarioInstitucion.Rol.SECRETARIA),
            ("demo_contabilidad", "Contabilidad", "Demo", UsuarioInstitucion.Rol.CONTABILIDAD),
            ("demo_docente", "Docente", "Demo", UsuarioInstitucion.Rol.DOCENTE),
        ]
        usuarios = {}
        for username, first_name, last_name, rol in cuentas:
            usuario, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"{username}@aulapro.local",
                    "activo": True,
                },
            )
            usuario.first_name = first_name
            usuario.last_name = last_name
            usuario.email = f"{username}@aulapro.local"
            usuario.activo = True
            usuario.set_password(password)
            usuario.save()
            UsuarioInstitucion.objects.update_or_create(
                usuario=usuario,
                institucion=institucion,
                defaults={"rol": rol, "activo": True},
            )
            usuarios[rol] = usuario

        superadmin, _ = User.objects.get_or_create(
            username="demo_superadmin",
            defaults={
                "first_name": "Superadmin",
                "last_name": "Demo",
                "email": "demo_superadmin@aulapro.local",
                "activo": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        superadmin.first_name = "Superadmin"
        superadmin.last_name = "Demo"
        superadmin.email = "demo_superadmin@aulapro.local"
        superadmin.activo = True
        superadmin.is_staff = True
        superadmin.is_superuser = True
        superadmin.set_password(password)
        superadmin.save()

        nivel, _ = NivelEducativo.objects.update_or_create(
            codigo="DEMO-BASICO",
            defaults={"nombre": "Nivel Básico Demo", "orden": 30, "activo": True},
        )

        ciclo, _ = CicloEscolar.objects.update_or_create(
            institucion=institucion,
            anio=2026,
            defaults={
                "nombre": "Ciclo Escolar 2026",
                "fecha_inicio": date(2026, 1, 15),
                "fecha_fin": date(2026, 10, 31),
                "activo": True,
                "es_actual": True,
                "cerrado": False,
            },
        )

        jornada, _ = JornadaInstitucion.objects.update_or_create(
            institucion=institucion,
            codigo="MAT",
            defaults={
                "nombre": "Matutina",
                "hora_inicio": time(7, 0),
                "hora_fin": time(13, 0),
                "activa": True,
                "orden": 1,
            },
        )

        oferta, _ = OfertaAcademica.objects.update_or_create(
            institucion=institucion,
            ciclo=ciclo,
            codigo_interno="BASICO-DEMO",
            defaults={
                "nivel": nivel,
                "carrera_catalogo": None,
                "version_pensum": None,
                "nombre_mostrado": "Ciclo Básico Demo",
                "origen": OfertaAcademica.Origen.PERSONALIZADA,
                "activa": True,
            },
        )

        grado, _ = GradoInstitucion.objects.update_or_create(
            oferta=oferta,
            codigo="1B",
            defaults={
                "institucion": institucion,
                "ciclo": ciclo,
                "nombre": "Primero Básico",
                "orden": 1,
                "activo": True,
            },
        )

        seccion, _ = Seccion.objects.update_or_create(
            grado=grado,
            jornada=jornada,
            nombre="A",
            defaults={
                "institucion": institucion,
                "ciclo": ciclo,
                "codigo": "1B-A",
                "capacidad": 35,
                "activa": True,
            },
        )

        cursos = {}
        for orden, (codigo, nombre, periodos) in enumerate(
            [
                ("MAT", "Matemática", 5),
                ("COM", "Comunicación y Lenguaje", 5),
                ("TEC", "Tecnología", 3),
            ],
            start=1,
        ):
            curso, _ = CursoInstitucion.objects.update_or_create(
                grado=grado,
                nombre_personalizado=nombre,
                defaults={
                    "institucion": institucion,
                    "ciclo": ciclo,
                    "oferta": oferta,
                    "curso_catalogo": None,
                    "curso_pensum_origen": None,
                    "nombre_mostrado": nombre,
                    "periodos_semanales": periodos,
                    "obligatorio": True,
                    "origen": CursoInstitucion.Origen.INSTITUCIONAL,
                    "orden": orden,
                    "activo": True,
                },
            )
            cursos[codigo] = curso

        familia, _ = Familia.objects.get_or_create(
            institucion=institucion,
            nombre_referencia="Familias Demo AulaPro",
            defaults={
                "direccion": "Ciudad de Guatemala",
                "telefono_principal": "5555-0101",
                "email_principal": "familias.demo@aulapro.local",
                "activa": True,
            },
        )
        encargado, _ = Encargado.objects.update_or_create(
            institucion=institucion,
            cui="2999999999999",
            defaults={
                "nombres": "María Elena",
                "apellidos": "López Demo",
                "telefono": "5555-0101",
                "email": "encargado.demo@aulapro.local",
                "direccion": "Ciudad de Guatemala",
                "ocupacion": "Comerciante",
                "activo": True,
            },
        )

        alumnos = []
        inscripciones = []
        nombres = [
            ("Ana", "López"),
            ("Carlos", "Pérez"),
            ("Daniela", "García"),
            ("Diego", "Ramírez"),
            ("Elena", "Morales"),
            ("Fernando", "Castillo"),
            ("Gabriela", "Hernández"),
            ("Hugo", "Méndez"),
            ("Isabel", "Reyes"),
            ("José", "Cabrera"),
            ("Karla", "Ortiz"),
            ("Luis", "Gómez"),
        ]
        for index, (nombre, apellido) in enumerate(nombres, start=1):
            cui = f"100000000{index:04d}"
            alumno, _ = Alumno.objects.update_or_create(
                institucion=institucion,
                cui=cui,
                defaults={
                    "familia": familia,
                    "estado_identificacion": Alumno.EstadoIdentificacion.VALIDADO,
                    "codigo_interno": f"ALU-{index:04d}",
                    "primer_nombre": nombre,
                    "primer_apellido": apellido,
                    "fecha_nacimiento": date(2012, ((index - 1) % 12) + 1, min(index + 2, 28)),
                    "sexo": Alumno.Sexo.FEMENINO if index % 2 else Alumno.Sexo.MASCULINO,
                    "telefono": "",
                    "email": "",
                    "direccion": "Ciudad de Guatemala",
                    "departamento": "Guatemala",
                    "municipio": "Guatemala",
                    "estado": Alumno.Estado.ACTIVO,
                    "fecha_ingreso": date(2026, 1, 15),
                },
            )
            AlumnoEncargado.objects.update_or_create(
                alumno=alumno,
                encargado=encargado,
                defaults={
                    "institucion": institucion,
                    "parentesco": AlumnoEncargado.Parentesco.TUTOR,
                    "es_principal": True,
                    "es_responsable_financiero": True,
                    "es_contacto_emergencia": True,
                    "autorizado_recoger": True,
                    "convive_con_alumno": False,
                    "activo": True,
                },
            )
            inscripcion, _ = Inscripcion.objects.update_or_create(
                alumno=alumno,
                ciclo=ciclo,
                estado=Inscripcion.Estado.ACTIVA,
                defaults={
                    "institucion": institucion,
                    "oferta_academica": oferta,
                    "grado": grado,
                    "seccion": seccion,
                    "fecha_inscripcion": date(2026, 1, 15),
                    "numero_inscripcion": f"INS-2026-{index:04d}",
                    "es_reingreso": False,
                    "observaciones": "Registro generado por crear_demo_aulapro.",
                },
            )
            alumnos.append(alumno)
            inscripciones.append(inscripcion)

        docente_usuario = usuarios[UsuarioInstitucion.Rol.DOCENTE]
        docente, _ = Docente.objects.update_or_create(
            institucion=institucion,
            cui="2888888888888",
            defaults={
                "usuario": docente_usuario,
                "primer_nombre": "Docente",
                "segundo_nombre": "de",
                "primer_apellido": "Prueba",
                "telefono": "5555-0202",
                "email": docente_usuario.email,
                "titulo_profesional": "Profesorado de Enseñanza Media",
                "especialidad": "Matemática",
                "fecha_ingreso": date(2026, 1, 10),
                "estado": Docente.Estado.ACTIVO,
            },
        )

        asignacion, _ = AsignacionDocente.objects.update_or_create(
            docente=docente,
            ciclo=ciclo,
            seccion=seccion,
            curso=cursos["MAT"],
            activa=True,
            defaults={
                "institucion": institucion,
                "oferta_academica": oferta,
                "grado": grado,
                "fecha_inicio": date(2026, 1, 15),
                "es_titular": True,
                "observaciones": "Asignación demo.",
            },
        )
        AsignacionGuia.objects.update_or_create(
            ciclo=ciclo,
            seccion=seccion,
            activa=True,
            defaults={
                "institucion": institucion,
                "docente": docente,
                "fecha_inicio": date(2026, 1, 15),
            },
        )

        admin = usuarios[UsuarioInstitucion.Rol.ADMINISTRADOR]
        sesion, _ = SesionAsistencia.objects.update_or_create(
            institucion=institucion,
            fecha=date(2026, 8, 24),
            seccion=seccion,
            tipo=SesionAsistencia.Tipo.GENERAL,
            defaults={
                "ciclo": ciclo,
                "oferta_academica": oferta,
                "grado": grado,
                "curso": None,
                "asignacion_docente": None,
                "docente": docente,
                "estado": SesionAsistencia.Estado.CERRADA,
                "creada_por": admin,
                "cerrada_por": admin,
                "fecha_cierre": timezone.now(),
            },
        )
        estados = [
            RegistroAsistencia.Estado.PRESENTE,
            RegistroAsistencia.Estado.PRESENTE,
            RegistroAsistencia.Estado.TARDE,
            RegistroAsistencia.Estado.AUSENTE,
        ]
        for index, (alumno, inscripcion) in enumerate(zip(alumnos, inscripciones)):
            estado = estados[index % len(estados)]
            RegistroAsistencia.objects.update_or_create(
                sesion=sesion,
                alumno=alumno,
                defaults={
                    "institucion": institucion,
                    "inscripcion": inscripcion,
                    "estado": estado,
                    "registrado_por": admin,
                    "justificada": estado == RegistroAsistencia.Estado.AUSENTE and index % 2 == 1,
                    "motivo_justificacion": (
                        "Cita médica (dato demo)."
                        if estado == RegistroAsistencia.Estado.AUSENTE and index % 2 == 1
                        else ""
                    ),
                    "justificada_por": (
                        admin
                        if estado == RegistroAsistencia.Estado.AUSENTE and index % 2 == 1
                        else None
                    ),
                    "fecha_justificacion": (
                        timezone.now()
                        if estado == RegistroAsistencia.Estado.AUSENTE and index % 2 == 1
                        else None
                    ),
                },
            )

        ConfiguracionCalificaciones.objects.get_or_create(institucion=institucion)
        periodo, _ = PeriodoAcademico.objects.update_or_create(
            institucion=institucion,
            ciclo=ciclo,
            codigo="B1",
            defaults={
                "nombre": "Primer Bimestre",
                "numero_orden": 1,
                "fecha_inicio": date(2026, 1, 15),
                "fecha_fin": date(2026, 3, 31),
                "activo": True,
                "cerrado": False,
            },
        )
        tipo_eval, _ = TipoEvaluacion.objects.update_or_create(
            institucion=institucion,
            codigo="EXAMEN",
            defaults={
                "nombre": "Examen",
                "descripcion": "Tipo de evaluación demo.",
                "activo": True,
                "orden": 1,
            },
        )
        actividad, _ = ActividadEvaluacion.objects.update_or_create(
            institucion=institucion,
            periodo=periodo,
            asignacion_docente=asignacion,
            nombre="Evaluación diagnóstica demo",
            defaults={
                "ciclo": ciclo,
                "curso": cursos["MAT"],
                "grado": grado,
                "seccion": seccion,
                "tipo_evaluacion": tipo_eval,
                "descripcion": "Actividad creada para visualizar la planilla de calificaciones.",
                "fecha": date(2026, 2, 10),
                "punteo_maximo": Decimal("100.00"),
                "ponderacion": Decimal("40.00"),
                "es_recuperacion": False,
                "activa": True,
                "creada_por": docente_usuario,
            },
        )
        for index, (alumno, inscripcion) in enumerate(zip(alumnos, inscripciones), start=1):
            nota = Decimal(str(60 + ((index * 3) % 38)))
            Calificacion.objects.update_or_create(
                actividad=actividad,
                alumno=alumno,
                defaults={
                    "institucion": institucion,
                    "inscripcion": inscripcion,
                    "estado": Calificacion.Estado.CALIFICADO,
                    "punteo_obtenido": nota,
                    "observacion": "Nota demo.",
                    "registrado_por": docente_usuario,
                },
            )

        from alumnos.models import DocumentoAlumno, RequisitoDocumentoAlumno, TipoDocumentoAlumno
        for orden, (codigo, nombre) in enumerate((("PARTIDA", "Partida de nacimiento"), ("FOTOGRAFIA", "Fotografía"), ("CERTIFICADO_ANTERIOR", "Certificado del grado anterior"), ("DOC_ENCARGADO", "Documento del encargado")), 1):
            tipo, _ = TipoDocumentoAlumno.objects.update_or_create(institucion=institucion, codigo=codigo, defaults={"nombre": nombre, "obligatorio": True, "visible_portal": True, "orden": orden})
            RequisitoDocumentoAlumno.objects.get_or_create(institucion=institucion, tipo_documento=tipo, defaults={"obligatorio": True})
        partida = TipoDocumentoAlumno.objects.get(institucion=institucion, codigo="PARTIDA")
        for index, alumno in enumerate(alumnos[:3]):
            DocumentoAlumno.objects.get_or_create(institucion=institucion, alumno=alumno, tipo_documento=partida, defaults={"estado": "RECHAZADO" if index == 2 else "APROBADO", "motivo_rechazo": "Archivo ilegible." if index == 2 else "", "cargado_por": admin, "revisado_por": admin, "fecha_revision": timezone.now()})

        self.stdout.write(self.style.SUCCESS("Datos demo de AulaPro creados/actualizados correctamente."))
        self.stdout.write("")
        self.stdout.write("Institución: Colegio Demo AulaPro")
        self.stdout.write("Código: AULAPRO-DEMO")
        self.stdout.write("")
        self.stdout.write("Usuarios de prueba:")
        self.stdout.write("  demo_superadmin   - Superadministrador")
        self.stdout.write("  demo_propietario  - Propietario")
        self.stdout.write("  demo_director     - Director")
        self.stdout.write("  demo_admin        - Administrador")
        self.stdout.write("  demo_secretaria   - Secretaría")
        self.stdout.write("  demo_contabilidad - Contabilidad")
        self.stdout.write("  demo_docente      - Docente")
        self.stdout.write(f"Contraseña común: {password}")
        self.stdout.write("")
        self.stdout.write("Incluye ciclo, jornada, oferta, grado, sección, cursos, 12 alumnos,")
        self.stdout.write("encargado/familia, docente, asignación, asistencia y calificaciones demo.")
