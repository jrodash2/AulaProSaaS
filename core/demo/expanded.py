"""Datos integrales, coherentes e idempotentes para la institución demo."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from academico.models import CicloEscolar, CursoInstitucion, GradoInstitucion, JornadaInstitucion, OfertaAcademica, ResultadoAnualAlumno, Seccion
from admisiones.models import Aspirante, DocumentoAdmision, EncargadoAspirante, EntrevistaAdmision, EvaluacionAdmision, SolicitudAdmision, TipoDocumentoAdmision, TipoEvaluacionAdmision
from alumnos.models import Alumno, AlumnoEncargado, DocumentoAlumno, Encargado, Familia, Inscripcion, RequisitoDocumentoAlumno, TipoDocumentoAlumno
from asistencia.models import RegistroAsistencia, SesionAsistencia
from calificaciones.models import ActividadEvaluacion, Calificacion, ConfiguracionCalificaciones, PeriodoAcademico, TipoEvaluacion
from comunicaciones.models import Notificacion
from docentes.models import AsignacionDocente, Docente
from finanzas.models import AplicacionPago, Cargo, ConceptoCobro, ConfiguracionFinanciera, MetodoPago, Pago
from horarios.models import Aula, BloqueHorario, HorarioClase
from instituciones.models import UsuarioInstitucion
from rrhh.models import AreaLaboral, ContratoLaboral, DocumentoEmpleado, Empleado, MovimientoLaboral, PermisoLaboral, PuestoLaboral, TipoDocumentoEmpleado
from seguimiento.models import CategoriaSeguimiento, CompromisoSeguimiento, NotaSeguimiento, RegistroSeguimiento, ReunionSeguimiento
from suscripciones.catalogo import MODULOS_OFICIALES
from suscripciones.models import ModuloSaaS, Plan, PlanModulo, Suscripcion
from tareas.models import EntregaTarea, Tarea

DEMO_NOTE = "Generado por crear_demo_aulapro."


def _aware(day, hour=8):
    return timezone.make_aware(datetime.combine(day, time(hour, 0)))


def _saas(institucion, admin):
    for codigo, nombre, orden, descripcion, icono in MODULOS_OFICIALES:
        modulo, _ = ModuloSaaS.objects.update_or_create(codigo=codigo, defaults={"nombre": nombre, "orden": orden, "descripcion": descripcion, "icono": icono, "activo": True})
    plan, _ = Plan.objects.update_or_create(codigo="PRO", defaults={"nombre": "Pro", "descripcion": "Plan completo para la institución demo", "precio_mensual": Decimal("699.00"), "precio_anual": Decimal("6990.00"), "max_alumnos": 500, "max_usuarios": 100, "max_docentes": 50, "activo": True, "publico": True, "orden": 3})
    for modulo in ModuloSaaS.objects.filter(activo=True):
        PlanModulo.objects.update_or_create(plan=plan, modulo=modulo, defaults={"habilitado": True})
    actual = Suscripcion.objects.filter(institucion=institucion, estado__in=(Suscripcion.Estado.PRUEBA, Suscripcion.Estado.ACTIVA, Suscripcion.Estado.SUSPENDIDA)).first()
    defaults = {"plan": plan, "estado": Suscripcion.Estado.ACTIVA, "modalidad": Suscripcion.Modalidad.ANUAL, "fecha_inicio": date(2026, 1, 1), "fecha_fin": date(2027, 12, 31), "renovacion_automatica": True, "creada_por": admin}
    if actual:
        for key, value in defaults.items(): setattr(actual, key, value)
        actual.save()
    else:
        Suscripcion.objects.create(institucion=institucion, **defaults)


def _academico(institucion, nivel):
    ciclos = {}
    for anio, estado, actual, cerrado in ((2025, CicloEscolar.Estado.CERRADO, False, True), (2026, CicloEscolar.Estado.ACTIVO, True, False), (2027, CicloEscolar.Estado.PLANIFICACION, False, False)):
        ciclos[anio], _ = CicloEscolar.objects.update_or_create(institucion=institucion, anio=anio, defaults={"nombre": f"Ciclo Escolar {anio}", "fecha_inicio": date(anio, 1, 15), "fecha_fin": date(anio, 10, 31), "activo": anio != 2025, "es_actual": actual, "cerrado": cerrado, "estado": estado})
    jornada, _ = JornadaInstitucion.objects.update_or_create(institucion=institucion, codigo="MAT", defaults={"nombre": "Matutina", "hora_inicio": time(7), "hora_fin": time(13), "activa": True, "orden": 1})
    JornadaInstitucion.objects.update_or_create(institucion=institucion, codigo="VES", defaults={"nombre": "Vespertina", "hora_inicio": time(13), "hora_fin": time(18), "activa": True, "orden": 2})
    ofertas, grados = {}, {}
    for anio, ciclo in ciclos.items():
        oferta, _ = OfertaAcademica.objects.update_or_create(institucion=institucion, ciclo=ciclo, codigo_interno="BASICO-DEMO", defaults={"nivel": nivel, "nombre_mostrado": "Ciclo Básico Demo", "origen": OfertaAcademica.Origen.PERSONALIZADA, "activa": True})
        ofertas[anio] = oferta
        for orden, codigo, nombre in ((1, "1B", "Primero Básico"), (2, "2B", "Segundo Básico"), (3, "3B", "Tercero Básico")):
            grados[(anio, codigo)], _ = GradoInstitucion.objects.update_or_create(oferta=oferta, codigo=codigo, defaults={"institucion": institucion, "ciclo": ciclo, "nombre": nombre, "orden": orden, "activo": True})
    secciones = {}
    for codigo, grado_codigo, nombre in (("1B-A", "1B", "A"), ("1B-B", "1B", "B"), ("2B-A", "2B", "A"), ("3B-A", "3B", "A")):
        grado = grados[(2026, grado_codigo)]
        secciones[codigo], _ = Seccion.objects.update_or_create(grado=grado, jornada=jornada, nombre=nombre, defaults={"institucion": institucion, "ciclo": ciclos[2026], "codigo": codigo, "capacidad": 35, "activa": True})
    for anio in (2025, 2027):
        for grado_codigo in ("1B", "2B", "3B"):
            grado = grados[(anio, grado_codigo)]
            Seccion.objects.update_or_create(grado=grado, jornada=jornada, nombre="A", defaults={"institucion": institucion, "ciclo": ciclos[anio], "codigo": f"{grado_codigo}-A-{anio}", "capacidad": 35, "activa": True})
    materias = (("MAT", "Matemática", 5), ("COM", "Comunicación y Lenguaje", 5), ("CIE", "Ciencias Naturales", 4), ("SOC", "Estudios Sociales", 3), ("ING", "Inglés", 3), ("TEC", "Tecnología", 3), ("EFI", "Educación Física", 2))
    cursos = {}
    for (_, grado_codigo), grado in grados.items():
        for orden, (codigo, nombre, periodos) in enumerate(materias, 1):
            curso, _ = CursoInstitucion.objects.update_or_create(grado=grado, nombre_personalizado=nombre, defaults={"institucion": institucion, "ciclo": grado.ciclo, "oferta": grado.oferta, "nombre_mostrado": nombre, "periodos_semanales": periodos, "obligatorio": True, "origen": CursoInstitucion.Origen.INSTITUCIONAL, "orden": orden, "activo": True})
            cursos[(grado.ciclo.anio, grado_codigo, codigo)] = curso
    return {"ciclos": ciclos, "ofertas": ofertas, "grados": grados, "secciones": secciones, "jornada": jornada, "cursos": cursos, "materias": materias}


def _docentes(institucion, ctx, demo_docente):
    datos = (
        ("2888888888888", "Carlos", "Méndez", "Matemática", Docente.Estado.ACTIVO, demo_docente),
        ("2888888888889", "Ana", "Fuentes", "Comunicación y Lenguaje", Docente.Estado.ACTIVO, None),
        ("2888888888890", "Luis", "Alvarado", "Ciencias Naturales", Docente.Estado.ACTIVO, None),
        ("2888888888891", "Sofía", "Herrera", "Inglés", Docente.Estado.ACTIVO, None),
        ("2888888888892", "Mario", "Rivas", "Tecnología", Docente.Estado.ACTIVO, None),
        ("2888888888893", "Elena", "Solís", "Estudios Sociales", Docente.Estado.INACTIVO, None),
    )
    docentes = []
    for idx, (cui, nombre, apellido, especialidad, estado, usuario) in enumerate(datos, 1):
        docente, _ = Docente.objects.update_or_create(institucion=institucion, cui=cui, defaults={"usuario": usuario, "primer_nombre": nombre, "primer_apellido": apellido, "telefono": f"5556-{idx:04d}", "email": f"docente{idx}@aulapro.local", "titulo_profesional": "Profesorado de Enseñanza Media", "especialidad": especialidad, "fecha_ingreso": date(2022 + idx % 3, 1, 10), "estado": estado})
        docentes.append(docente)
    activos = docentes[:5]
    asignaciones = {}
    mapa = {"MAT": 0, "COM": 1, "CIE": 2, "SOC": 1, "ING": 3, "TEC": 4, "EFI": 2}
    for seccion in ctx["secciones"].values():
        grado_codigo = seccion.grado.codigo
        for codigo, _, _ in ctx["materias"]:
            curso = ctx["cursos"][(2026, grado_codigo, codigo)]
            docente = activos[mapa[codigo]]
            asignacion, _ = AsignacionDocente.objects.update_or_create(institucion=institucion, ciclo=ctx["ciclos"][2026], seccion=seccion, curso=curso, docente=docente, defaults={"oferta_academica": ctx["ofertas"][2026], "grado": seccion.grado, "fecha_inicio": date(2026, 1, 15), "activa": True, "es_titular": True, "observaciones": DEMO_NOTE})
            asignaciones[(seccion.codigo, codigo)] = asignacion
    return docentes, asignaciones


def _familias_alumnos(institucion, ctx, usuarios):
    familias, encargados = [], []
    portal_padre = get_user_model().objects.get(username="demo_padre")
    for idx in range(1, 13):
        nombre = "Familias Demo AulaPro" if idx == 1 else f"Familia Demo {idx:02d}"
        familia, _ = Familia.objects.update_or_create(institucion=institucion, nombre_referencia=nombre, defaults={"direccion": f"Zona {(idx % 12) + 1}, Ciudad de Guatemala", "telefono_principal": f"5557-{idx:04d}", "email_principal": f"familia{idx:02d}@aulapro.local", "activa": True})
        familias.append(familia)
        cui_encargado = "2999999999999" if idx == 1 else f"29999999{idx:05d}"
        encargado, _ = Encargado.objects.update_or_create(institucion=institucion, cui=cui_encargado, defaults={"usuario": portal_padre if idx == 1 else None, "nombres": ("María Elena" if idx == 1 else f"Encargado {idx:02d}"), "apellidos": "Familia Demo", "telefono": f"5557-{idx:04d}", "email": f"familia{idx:02d}@aulapro.local", "direccion": familia.direccion, "ocupacion": "Responsable familiar", "activo": True})
        encargados.append(encargado)
    nombres = (("Ana", "López"), ("Carlos", "López"), ("Daniela", "García"), ("Diego", "Ramírez"), ("Elena", "Morales"), ("Fernando", "Castillo"), ("Gabriela", "Hernández"), ("Hugo", "Méndez"), ("Isabel", "Reyes"), ("José", "Cabrera"), ("Karla", "Ortiz"), ("Luis", "Gómez"), ("Mariana", "Paz"), ("Nicolás", "León"), ("Olivia", "Campos"), ("Pablo", "Vega"), ("Renata", "Díaz"), ("Samuel", "Ibarra"), ("Valeria", "Navas"), ("Tomás", "Pineda"), ("Amanda", "Rosales"), ("Bruno", "Santos"), ("Camila", "Mejía"), ("Damián", "Cruz"), ("Eva", "Lemus"), ("Felipe", "Monzón"), ("Gina", "Barrios"), ("Ian", "Godínez"), ("Julia", "Arévalo"), ("Kevin", "Bonilla"))
    section_codes = ["1B-A"] * 8 + ["1B-B"] * 8 + ["2B-A"] * 7 + ["3B-A"] * 7
    alumnos, inscripciones = [], {}
    for idx, ((nombre, apellido), section_code) in enumerate(zip(nombres, section_codes), 1):
        familia = familias[min((idx - 1) // 3, 11)]
        estado = Alumno.Estado.INACTIVO if idx == 29 else Alumno.Estado.RETIRADO if idx == 30 else Alumno.Estado.ACTIVO
        alumno, _ = Alumno.objects.update_or_create(institucion=institucion, cui=f"100000000{idx:04d}", defaults={"usuario": get_user_model().objects.get(username="demo_alumno") if idx == 1 else None, "familia": familia, "estado_identificacion": Alumno.EstadoIdentificacion.VALIDADO, "codigo_interno": f"ALU-{idx:04d}", "primer_nombre": nombre, "primer_apellido": apellido, "fecha_nacimiento": date(2011 + (idx % 3), ((idx - 1) % 12) + 1, min(idx + 1, 28)), "sexo": Alumno.Sexo.FEMENINO if idx % 2 else Alumno.Sexo.MASCULINO, "direccion": familia.direccion, "departamento": "Guatemala", "municipio": "Guatemala", "estado": estado, "fecha_ingreso": date(2025 if idx <= 6 else 2026, 1, 15)})
        alumnos.append(alumno)
        encargado = encargados[min((idx - 1) // 3, 11)]
        AlumnoEncargado.objects.update_or_create(alumno=alumno, encargado=encargado, defaults={"institucion": institucion, "parentesco": AlumnoEncargado.Parentesco.MADRE if idx % 3 == 1 else AlumnoEncargado.Parentesco.PADRE if idx % 3 == 2 else AlumnoEncargado.Parentesco.TUTOR, "es_principal": True, "es_responsable_financiero": idx % 3 != 0, "es_contacto_emergencia": True, "autorizado_recoger": True, "activo": True})
        seccion = ctx["secciones"][section_code]
        estado_ins = Inscripcion.Estado.RETIRADA if idx == 29 else Inscripcion.Estado.ANULADA if idx == 30 else Inscripcion.Estado.ACTIVA
        ins = Inscripcion.objects.filter(institucion=institucion, alumno=alumno, ciclo=ctx["ciclos"][2026]).first() or Inscripcion(institucion=institucion, alumno=alumno, ciclo=ctx["ciclos"][2026])
        ins.oferta_academica=ctx["ofertas"][2026];ins.grado=seccion.grado;ins.seccion=seccion;ins.fecha_inscripcion=date(2026,1,15);ins.numero_inscripcion=f"INS-2026-{idx:04d}";ins.estado=estado_ins;ins.observaciones=DEMO_NOTE
        if estado_ins == Inscripcion.Estado.RETIRADA: ins.fecha_retiro=date(2026,5,20);ins.motivo_retiro="Traslado familiar demo"
        ins.save();inscripciones[alumno.pk]=ins
    AlumnoEncargado.objects.filter(institucion=institucion, encargado=encargados[0]).exclude(alumno__in=alumnos[:3]).update(activo=False)
    return alumnos, inscripciones, familias, encargados

def _horarios(institucion, ctx, asignaciones):
    aulas = []
    for idx, (codigo, nombre) in enumerate((("A1", "Aula 1"), ("A2", "Aula 2"), ("A3", "Aula 3"), ("LAB-COMP", "Laboratorio de Computación"), ("LAB-CIEN", "Laboratorio de Ciencias"))):
        aula, _ = Aula.objects.update_or_create(institucion=institucion, codigo=codigo, defaults={"nombre": nombre, "capacidad": 36, "ubicacion": "Edificio principal", "descripcion": DEMO_NOTE, "activa": True})
        aulas.append(aula)
    slots = ((10,"Período 1",time(7),time(7,45),"CLASE"),(20,"Período 2",time(7,45),time(8,30),"CLASE"),(25,"Recreo",time(8,30),time(8,50),"RECREO"),(30,"Período 3",time(8,50),time(9,35),"CLASE"),(40,"Período 4",time(9,35),time(10,20),"CLASE"),(50,"Período 5",time(10,20),time(11,5),"CLASE"),(60,"Período 6",time(11,5),time(11,50),"CLASE"))
    bloques = []
    for orden,nombre,inicio,fin,tipo in slots:
        bloque, _ = BloqueHorario.objects.update_or_create(institucion=institucion,jornada=ctx["jornada"],orden=orden,defaults={"nombre":nombre,"hora_inicio":inicio,"hora_fin":fin,"tipo":tipo,"activo":True})
        if tipo == BloqueHorario.Tipo.CLASE: bloques.append(bloque)
    dias = (HorarioClase.Dia.LUNES,HorarioClase.Dia.MARTES,HorarioClase.Dia.MIERCOLES,HorarioClase.Dia.JUEVES,HorarioClase.Dia.VIERNES)
    codigos = ("MAT","COM","CIE","ING","TEC")
    secciones = list(ctx["secciones"].values())
    for dia_idx,dia in enumerate(dias):
        for bloque_idx,bloque in enumerate(bloques[:5]):
            for seccion_idx,seccion in enumerate(secciones):
                codigo = codigos[(dia_idx+bloque_idx+seccion_idx)%len(codigos)]
                asignacion=asignaciones[(seccion.codigo,codigo)]
                aula=aulas[seccion_idx]
                HorarioClase.objects.update_or_create(institucion=institucion,seccion=seccion,dia_semana=dia,bloque=bloque,defaults={"ciclo":ctx["ciclos"][2026],"jornada":ctx["jornada"],"asignacion_docente":asignacion,"aula":aula,"activo":True,"observaciones":DEMO_NOTE})
    return aulas, bloques


def _asistencia(institucion, ctx, inscripciones, admin):
    activas=[i for i in inscripciones.values() if i.estado==Inscripcion.Estado.ACTIVA]
    hoy=timezone.localdate()
    for seccion_idx,seccion in enumerate(ctx["secciones"].values()):
        alumnos_seccion=[i for i in activas if i.seccion_id==seccion.pk]
        for n in range(5):
            fecha=hoy-timedelta(days=7+n*3+seccion_idx)
            sesion, _=SesionAsistencia.objects.update_or_create(institucion=institucion,fecha=fecha,seccion=seccion,tipo=SesionAsistencia.Tipo.GENERAL,defaults={"ciclo":ctx["ciclos"][2026],"oferta_academica":ctx["ofertas"][2026],"grado":seccion.grado,"hora_inicio":time(7),"hora_fin":time(7,15),"estado":SesionAsistencia.Estado.CERRADA,"creada_por":admin,"cerrada_por":admin,"fecha_cierre":_aware(fecha,12)})
            for pos,ins in enumerate(alumnos_seccion):
                estado=RegistroAsistencia.Estado.PRESENTE
                if pos==1 and n in (1,3): estado=RegistroAsistencia.Estado.TARDE
                if pos==2 and n in (2,4): estado=RegistroAsistencia.Estado.AUSENTE
                justificada=estado==RegistroAsistencia.Estado.AUSENTE and n==2
                RegistroAsistencia.objects.update_or_create(institucion=institucion,sesion=sesion,alumno=ins.alumno,defaults={"inscripcion":ins,"estado":estado,"hora_registro":time(7,5) if estado==RegistroAsistencia.Estado.TARDE else time(7),"observacion":DEMO_NOTE,"justificada":justificada,"motivo_justificacion":"Cita familiar informada" if justificada else "","justificada_por":admin if justificada else None,"fecha_justificacion":timezone.now() if justificada else None,"registrado_por":admin})


def _calificaciones_tareas(institucion, ctx, asignaciones, inscripciones, admin):
    ConfiguracionCalificaciones.objects.update_or_create(institucion=institucion,defaults={"nota_minima_aprobacion":Decimal("60.00"),"decimales":2,"mostrar_promedio_acumulado":True})
    rangos=((1,"Primer Bimestre",date(2026,1,15),date(2026,3,20)),(2,"Segundo Bimestre",date(2026,3,23),date(2026,5,29)),(3,"Tercer Bimestre",date(2026,6,1),date(2026,8,7)),(4,"Cuarto Bimestre",date(2026,8,10),date(2026,10,31)))
    periodos=[]
    for orden,nombre,inicio,fin in rangos:
        p,_=PeriodoAcademico.objects.update_or_create(institucion=institucion,ciclo=ctx["ciclos"][2026],codigo=f"B{orden}",defaults={"nombre":nombre,"numero_orden":orden,"fecha_inicio":inicio,"fecha_fin":fin,"activo":True,"cerrado":False})
        periodos.append(p)
    tipos={}
    for orden,(codigo,nombre) in enumerate((("EXA","Examen"),("TAR","Tarea"),("PRO","Proyecto"),("PAR","Participación"),("LAB","Laboratorio")),1):
        tipos[codigo],_=TipoEvaluacion.objects.update_or_create(institucion=institucion,codigo=codigo,defaults={"nombre":nombre,"descripcion":DEMO_NOTE,"activo":True,"orden":orden})
    actividades=[]
    for seccion in ctx["secciones"].values():
        inscritos=[i for i in inscripciones.values() if i.seccion_id==seccion.pk and i.estado==Inscripcion.Estado.ACTIVA]
        for p_idx,periodo in enumerate(periodos):
            for codigo in ("MAT","COM"):
                asignacion=asignaciones[(seccion.codigo,codigo)]
                tipo=tipos["EXA" if codigo=="MAT" else "PRO"]
                actividad,_=ActividadEvaluacion.objects.update_or_create(institucion=institucion,periodo=periodo,asignacion_docente=asignacion,nombre=f"{tipo.nombre} {periodo.codigo}",defaults={"ciclo":ctx["ciclos"][2026],"curso":asignacion.curso,"grado":seccion.grado,"seccion":seccion,"tipo_evaluacion":tipo,"descripcion":DEMO_NOTE,"fecha":periodo.fecha_inicio+timedelta(days=20),"punteo_maximo":Decimal("100.00"),"ponderacion":Decimal("25.00"),"activa":True,"creada_por":admin})
                actividades.append(actividad)
                notas=(95,88,76,64,58,91,83,70)
                for idx,ins in enumerate(inscritos):
                    pendiente=(p_idx==3 and idx==len(inscritos)-1)
                    Calificacion.objects.update_or_create(institucion=institucion,actividad=actividad,alumno=ins.alumno,defaults={"inscripcion":ins,"estado":Calificacion.Estado.PENDIENTE if pendiente else Calificacion.Estado.CALIFICADO,"punteo_obtenido":None if pendiente else Decimal(str(notas[(idx+p_idx)%len(notas)])),"observacion":DEMO_NOTE,"registrado_por":admin})
    PeriodoAcademico.objects.filter(pk__in=[p.pk for p in periodos[:2]]).update(cerrado=True, cerrado_por=admin, fecha_cierre=timezone.now())
    hoy=timezone.now()
    tareas=[]
    asignaciones_lista=list(asignaciones.values())[:12]
    for idx,asignacion in enumerate(asignaciones_lista,1):
        estado=(Tarea.Estado.BORRADOR,Tarea.Estado.PUBLICADA,Tarea.Estado.CERRADA)[idx%3]
        publicacion=hoy-timedelta(days=20-idx)
        limite=hoy+timedelta(days=idx-6)
        tarea,_=Tarea.objects.update_or_create(institucion=institucion,asignacion_docente=asignacion,titulo=f"Actividad práctica demo {idx:02d}",defaults={"ciclo":ctx["ciclos"][2026],"curso":asignacion.curso,"grado":asignacion.grado,"seccion":asignacion.seccion,"descripcion":DEMO_NOTE,"instrucciones":"Resolver y entregar según indicaciones.","fecha_publicacion":publicacion,"fecha_limite":limite,"estado":estado,"permite_entrega_archivo":True,"activa":True,"creada_por":admin})
        tareas.append(tarea)
        inscritos=[i for i in inscripciones.values() if i.seccion_id==asignacion.seccion_id and i.estado==Inscripcion.Estado.ACTIVA]
        for pos,ins in enumerate(inscritos):
            entrega_estado=(EntregaTarea.Estado.ENTREGADA,EntregaTarea.Estado.PENDIENTE,EntregaTarea.Estado.ENTREGADA_TARDE,EntregaTarea.Estado.NO_ENTREGADA)[pos%4]
            EntregaTarea.objects.update_or_create(institucion=institucion,tarea=tarea,alumno=ins.alumno,defaults={"inscripcion":ins,"estado":entrega_estado,"comentario":DEMO_NOTE,"fecha_entrega":hoy-timedelta(days=1) if entrega_estado in (EntregaTarea.Estado.ENTREGADA,EntregaTarea.Estado.ENTREGADA_TARDE) else None,"entregada_por":ins.alumno.usuario if entrega_estado in (EntregaTarea.Estado.ENTREGADA,EntregaTarea.Estado.ENTREGADA_TARDE) else None,"calificada":entrega_estado==EntregaTarea.Estado.ENTREGADA,"observacion_docente":"Buen trabajo" if entrega_estado==EntregaTarea.Estado.ENTREGADA else ""})
    return actividades,tareas

def _finanzas(institucion, ctx, alumnos, inscripciones, familias, admin):
    ConfiguracionFinanciera.objects.update_or_create(institucion=institucion,defaults={"moneda":"GTQ","simbolo_moneda":"Q","dia_vencimiento_mensualidad":10,"aplicar_mora":True,"monto_mora_predeterminado":Decimal("25.00"),"permitir_pago_mayor_saldo":False,"prefijo_recibo":"DEMO"})
    conceptos={}
    datos=(("INS","Inscripción","INSCRIPCION","350.00",False),("ENE","Colegiatura enero","MENSUALIDAD","450.00",True),("FEB","Colegiatura febrero","MENSUALIDAD","450.00",True),("MAR","Colegiatura marzo","MENSUALIDAD","450.00",True),("LAB","Laboratorio","EXTRAORDINARIO","125.50",False),("ACT","Actividad especial","EXTRAORDINARIO","200.00",False))
    for orden,(codigo,nombre,tipo,monto,recurrente) in enumerate(datos,1):
        conceptos[codigo],_=ConceptoCobro.objects.update_or_create(institucion=institucion,codigo=codigo,defaults={"nombre":nombre,"descripcion":DEMO_NOTE,"tipo_general":tipo,"monto_predeterminado":Decimal(monto),"activo":True,"recurrente":recurrente,"orden":orden})
    metodos={}
    for orden,(codigo,nombre) in enumerate((("EFE","Efectivo"),("TRA","Transferencia"),("OTR","Otro")),1):
        metodos[codigo],_=MetodoPago.objects.update_or_create(institucion=institucion,codigo=codigo,defaults={"nombre":nombre,"activo":True,"orden":orden})
    hoy=timezone.localdate();cargos=[]
    for idx,alumno in enumerate(alumnos[:10],1):
        ins=inscripciones[alumno.pk]
        for c_idx,codigo in enumerate(("INS","ENE","FEB","MAR","LAB","ACT"),1):
            periodo=f"2026-{c_idx:02d}"
            cargo,_=Cargo.objects.update_or_create(institucion=institucion,alumno=alumno,concepto=conceptos[codigo],periodo_referencia=periodo,defaults={"familia":alumno.familia,"ciclo":ctx["ciclos"][2026],"inscripcion":ins,"descripcion":conceptos[codigo].nombre,"fecha_emision":hoy-timedelta(days=90-c_idx*5),"fecha_vencimiento":hoy+timedelta(days=c_idx*7-35),"monto_original":conceptos[codigo].monto_predeterminado,"descuento":Decimal("0"),"recargo":Decimal("25.00") if idx==4 and c_idx<3 else Decimal("0"),"estado":Cargo.Estado.ANULADO if idx==10 and c_idx==6 else Cargo.Estado.PENDIENTE,"referencia":f"DEMO-{idx:02d}-{codigo}","creado_por":admin})
            cargos.append(cargo)
    for idx,alumno in enumerate(alumnos[:5],1):
        monto=(Decimal("350.00"),Decimal("225.00"),Decimal("450.00"),Decimal("125.50"),Decimal("450.00"))[idx-1]
        pago,_=Pago.objects.update_or_create(institucion=institucion,recibo_numero=f"DEMO-{idx:05d}",defaults={"alumno":alumno,"familia":alumno.familia,"fecha_pago":timezone.now()-timedelta(days=5-idx),"monto":monto,"metodo_pago":metodos[("EFE","TRA","OTR","EFE","TRA")[idx-1]],"referencia":f"PAGO-DEMO-{idx}","observaciones":DEMO_NOTE,"estado":Pago.Estado.CONFIRMADO,"registrado_por":admin})
        cargo=next(c for c in cargos if c.alumno_id==alumno.pk and c.concepto_id==conceptos["INS"].pk)
        aplicado=min(monto,cargo.monto_total)
        AplicacionPago.objects.update_or_create(institucion=institucion,pago=pago,cargo=cargo,defaults={"monto_aplicado":aplicado})
        cargo.estado=Cargo.Estado.PAGADO if aplicado>=cargo.monto_total else Cargo.Estado.PARCIAL;cargo.save()


def _expediente(institucion, alumnos, inscripciones, admin):
    tipos=[]
    for orden,(codigo,nombre,vigencia) in enumerate((("PARTIDA","Partida de nacimiento",False),("FOTO","Fotografía",False),("CERT","Certificado grado anterior",False),("ENC","Documento encargado",False),("FORM","Formulario inscripción",False),("MED","Constancia médica",True)),1):
        tipo,_=TipoDocumentoAlumno.objects.update_or_create(institucion=institucion,codigo=codigo,defaults={"nombre":nombre,"obligatorio":True,"visible_portal":True,"requiere_vigencia":vigencia,"orden":orden,"activo":True})
        RequisitoDocumentoAlumno.objects.update_or_create(institucion=institucion,tipo_documento=tipo,aplica_a_oferta=None,aplica_a_grado=None,defaults={"obligatorio":True,"activo":True})
        tipos.append(tipo)
    hoy=timezone.localdate()
    for a_idx,alumno in enumerate(alumnos[:8]):
        cantidad=6 if a_idx==0 else 4 if a_idx==1 else 2
        for t_idx,tipo in enumerate(tipos[:cantidad]):
            estado=DocumentoAlumno.Estado.APROBADO
            if a_idx==1 and t_idx==3: estado=DocumentoAlumno.Estado.RECHAZADO
            elif a_idx==2 and t_idx==1: estado=DocumentoAlumno.Estado.PENDIENTE
            elif a_idx==3 and t_idx==1: estado=DocumentoAlumno.Estado.VENCIDO
            elif a_idx==4 and t_idx==1: estado=DocumentoAlumno.Estado.NO_APLICA
            documento = DocumentoAlumno.objects.filter(institucion=institucion,alumno=alumno,tipo_documento=tipo).order_by("pk").first()
            documento = documento or DocumentoAlumno(institucion=institucion,alumno=alumno,tipo_documento=tipo)
            documento.inscripcion=inscripciones[alumno.pk];documento.ciclo=inscripciones[alumno.pk].ciclo;documento.estado=estado;documento.nombre_original="metadato-demo.pdf";documento.numero_documento=f"DOC-{a_idx+1:02d}-{t_idx+1:02d}";documento.fecha_emision=hoy-timedelta(days=365);documento.fecha_vencimiento=hoy-timedelta(days=2) if estado==DocumentoAlumno.Estado.VENCIDO else hoy+timedelta(days=60) if tipo.requiere_vigencia else None;documento.observaciones=DEMO_NOTE;documento.motivo_rechazo="Documento ilegible; cargar una nueva copia." if estado==DocumentoAlumno.Estado.RECHAZADO else "";documento.cargado_por=admin;documento.revisado_por=admin if estado in (DocumentoAlumno.Estado.APROBADO,DocumentoAlumno.Estado.RECHAZADO) else None;documento.fecha_revision=timezone.now() if estado in (DocumentoAlumno.Estado.APROBADO,DocumentoAlumno.Estado.RECHAZADO) else None;documento.save()


def _seguimiento(institucion, ctx, alumnos, inscripciones, encargados, docentes, admin):
    cats={}
    datos=(("PUNTUALIDAD","Puntualidad","INCIDENCIA"),("RESPONSABILIDAD","Responsabilidad","POSITIVO"),("CONVIVENCIA","Convivencia","CONVIVENCIA"),("RENDIMIENTO","Rendimiento académico","ACADEMICO"),("PARTICIPACION","Participación","POSITIVO"),("LIDERAZGO","Liderazgo","POSITIVO"))
    for orden,(codigo,nombre,tipo) in enumerate(datos,1):
        cats[codigo],_=CategoriaSeguimiento.objects.update_or_create(institucion=institucion,codigo=codigo,defaults={"nombre":nombre,"tipo":tipo,"descripcion":DEMO_NOTE,"color":"#2563EB","activo":True,"orden":orden})
    registros=[]
    casos=((0,"PARTICIPACION","POSITIVO","Excelente participación en Ciencias","PUBLICABLE_PORTAL","ABIERTO","NO_APLICA"),(1,"LIDERAZGO","POSITIVO","Liderazgo solidario","PADRES","RESUELTO","NO_APLICA"),(0,"PUNTUALIDAD","INCIDENCIA","Llegadas tarde recurrentes","PADRES","EN_SEGUIMIENTO","MEDIA"),(2,"CONVIVENCIA","CONVIVENCIA","Acuerdo de convivencia","DOCENTES","ABIERTO","BAJA"),(3,"RENDIMIENTO","ACADEMICO","Plan de apoyo académico","INTERNO","EN_SEGUIMIENTO","ALTA"),(4,"RESPONSABILIDAD","POSITIVO","Responsabilidad destacada","PADRES","RESUELTO","NO_APLICA"))
    for idx,codigo,tipo,titulo,privacidad,estado,gravedad in casos:
        alumno=alumnos[idx];ins=inscripciones[alumno.pk]
        reg,_=RegistroSeguimiento.objects.update_or_create(institucion=institucion,alumno=alumno,ciclo=ctx["ciclos"][2026],titulo=titulo,defaults={"inscripcion":ins,"categoria":cats[codigo],"tipo":tipo,"fecha":timezone.localdate()-timedelta(days=idx+2),"descripcion":DEMO_NOTE,"gravedad":gravedad,"confidencialidad":privacidad,"docente":docentes[0],"registrado_por":admin,"estado":estado})
        registros.append(reg)
    compromisos=((registros[2],"Mejorar puntualidad durante el mes","ALUMNO","PENDIENTE",10),(registros[4],"Completar plan de refuerzo","DOCENTE","CUMPLIDO",-2),(registros[3],"Cumplir acuerdos de convivencia","PADRE","PENDIENTE",-5))
    for reg,desc,responsable,estado,dias in compromisos:
        CompromisoSeguimiento.objects.update_or_create(institucion=institucion,registro=reg,descripcion=desc,defaults={"responsable":responsable,"fecha_compromiso":timezone.localdate()-timedelta(days=10),"fecha_limite":timezone.localdate()+timedelta(days=dias),"estado":estado,"cumplido_fecha":timezone.localdate()-timedelta(days=2) if estado=="CUMPLIDO" else None,"creado_por":admin})
    for idx,reg in enumerate(registros[2:5],1):
        NotaSeguimiento.objects.update_or_create(institucion=institucion,registro=reg,fecha=timezone.localdate()-timedelta(days=idx),comentario=f"Seguimiento cronológico demo {idx}",defaults={"autor":admin,"visible_padre":reg.confidencialidad in ("PADRES","PUBLICABLE_PORTAL")})
    for reg,motivo,acuerdo in ((registros[2],"Seguimiento de puntualidad","Revisar avances en dos semanas"),(registros[4],"Rendimiento académico","Aplicar plan de apoyo y revisión mensual")):
        ReunionSeguimiento.objects.update_or_create(institucion=institucion,alumno=reg.alumno,registro=reg,motivo=motivo,defaults={"fecha":timezone.now()-timedelta(days=1),"encargado":encargados[min(alumnos.index(reg.alumno)//3,11)],"participantes":"Dirección, encargado y estudiante","acuerdos":acuerdo,"observaciones":DEMO_NOTE,"creado_por":admin})

def _admisiones(institucion, ctx, alumnos, admin, secretaria, docentes):
    tipos=[]
    for codigo,nombre in (("PARTIDA","Partida de nacimiento"),("CERTIFICADO","Certificado del grado anterior"),("FOTOGRAFIA","Fotografía"),("ENCARGADO","Documento del encargado")):
        tipo,_=TipoDocumentoAdmision.objects.update_or_create(institucion=institucion,codigo=codigo,defaults={"nombre":nombre,"obligatorio":True,"activo":True});tipos.append(tipo)
    evaluaciones=[]
    for nombre in ("Matemática","Lectura","Entrevista familiar"):
        tipo,_=TipoEvaluacionAdmision.objects.update_or_create(institucion=institucion,nombre=nombre,defaults={"descripcion":DEMO_NOTE,"punteo_maximo":Decimal("100"),"punteo_minimo_referencia":Decimal("60"),"activo":True});evaluaciones.append(tipo)
    estados=("NUEVA","NUEVA","EN_REVISION","DOCUMENTACION_PENDIENTE","DOCUMENTACION_PENDIENTE","ENTREVISTA_PENDIENTE","EVALUACION_PENDIENTE","APROBADA","APROBADA","LISTA_ESPERA","LISTA_ESPERA","RECHAZADA","EN_DECISION","INSCRITA")
    origenes=("REDES_SOCIALES","REFERIDO","PAGINA_WEB","VISITA","PUBLICIDAD")
    solicitudes=[]
    grado_2027=ctx["grados"][(2027,"1B")]
    for idx,estado in enumerate(estados,1):
        cui=alumnos[0].cui if estado=="INSCRITA" else f"400000000{idx:04d}"
        aspirante = Aspirante.objects.filter(institucion=institucion,nombres=f"Aspirante {idx}").order_by("pk").first()
        aspirante = aspirante or Aspirante(institucion=institucion,nombres=f"Aspirante {idx}",fecha_nacimiento=date(2017,((idx-1)%12)+1,min(idx+2,28)))
        aspirante.apellidos="Familia Demo";aspirante.fecha_nacimiento=date(2017,((idx-1)%12)+1,min(idx+2,28));aspirante.cui=cui;aspirante.sexo="F" if idx%2 else "M";aspirante.telefono=f"5560-{idx:04d}";aspirante.correo=f"aspirante{idx:02d}@demo.test";aspirante.direccion="Ciudad de Guatemala";aspirante.colegio_anterior="Centro Educativo Anterior Demo";aspirante.ultimo_grado_cursado="Sexto Primaria";aspirante.estado="INSCRITO" if estado=="INSCRITA" else "APROBADO" if estado=="APROBADA" else "LISTA_ESPERA" if estado=="LISTA_ESPERA" else "RECHAZADO" if estado=="RECHAZADA" else "EN_PROCESO";aspirante.creado_por=secretaria;aspirante.save()
        EncargadoAspirante.objects.update_or_create(institucion=institucion,aspirante=aspirante,es_principal=True,defaults={"nombres":f"Encargado {idx:02d}","apellidos":"Admisión Demo","parentesco":"MADRE" if idx%2 else "PADRE","telefono":f"5570-{idx:04d}","correo":f"admision{idx:02d}@demo.test","direccion":"Ciudad de Guatemala"})
        solicitud=SolicitudAdmision.objects.filter(institucion=institucion,aspirante=aspirante).first() or SolicitudAdmision(institucion=institucion,aspirante=aspirante,ciclo_solicitado=ctx["ciclos"][2027])
        solicitud.ciclo_solicitado=ctx["ciclos"][2027];solicitud.jornada_solicitada=ctx["jornada"];solicitud.oferta_solicitada=ctx["ofertas"][2027];solicitud.grado_solicitado=grado_2027;solicitud.fecha_solicitud=timezone.localdate()-timedelta(days=idx);solicitud.estado=estado;solicitud.origen=origenes[(idx-1)%len(origenes)];solicitud.observaciones=DEMO_NOTE;solicitud.motivo_rechazo="Cupo y criterios institucionales revisados." if estado=="RECHAZADA" else "";solicitud.posicion_espera=(idx-9) if estado=="LISTA_ESPERA" else None;solicitud.fecha_lista_espera=timezone.localdate()-timedelta(days=2) if estado=="LISTA_ESPERA" else None;solicitud.creada_por=secretaria
        if solicitud.secuencia:
            solicitud.numero_solicitud=f"ADM-2027-{solicitud.secuencia:05d}"
        solicitud.save();solicitudes.append(solicitud)
    from django.core.files.base import ContentFile
    pdf=ContentFile(b"%PDF-1.4\n% AulaPro demo\n%%EOF",name="documento-demo.pdf")
    for s_idx,solicitud in enumerate(solicitudes[:3]):
        cantidad=(4,2,3)[s_idx]
        for t_idx,tipo in enumerate(tipos[:cantidad]):
            estado=DocumentoAdmision.Estado.RECHAZADO if s_idx==2 and t_idx==2 else DocumentoAdmision.Estado.APROBADO
            if not DocumentoAdmision.objects.filter(institucion=institucion,solicitud=solicitud,tipo=tipo).exists():
                pdf.seek(0);DocumentoAdmision.objects.create(institucion=institucion,solicitud=solicitud,tipo=tipo,archivo=ContentFile(pdf.read(),name="documento-demo.pdf"),nombre_original="documento-demo.pdf",estado=estado)
    entrevistas_estados=("PROGRAMADA","REALIZADA","REPROGRAMADA","NO_ASISTIO")
    for idx,estado in enumerate(entrevistas_estados):
        EntrevistaAdmision.objects.update_or_create(institucion=institucion,solicitud=solicitudes[5+idx],defaults={"fecha_programada":timezone.now()+timedelta(days=idx+2),"fecha_realizada":timezone.now()-timedelta(days=1) if estado=="REALIZADA" else None,"entrevistador":admin,"modalidad":("PRESENCIAL","VIRTUAL","TELEFONICA","PRESENCIAL")[idx],"estado":estado,"observaciones":DEMO_NOTE,"recomendacion":"FAVORABLE" if estado=="REALIZADA" else "PENDIENTE"})
    for s_idx,solicitud in enumerate(solicitudes[6:10]):
        for e_idx,tipo in enumerate(evaluaciones):
            realizado=(s_idx+e_idx)%3!=0
            evaluador = docentes[e_idx % len(docentes)].usuario or admin
            EvaluacionAdmision.objects.update_or_create(institucion=institucion,solicitud=solicitud,tipo_evaluacion=tipo,defaults={"fecha":timezone.localdate()-timedelta(days=e_idx),"punteo":Decimal(str(58+7*((s_idx+e_idx)%6))) if realizado else None,"observaciones":DEMO_NOTE,"evaluado_por":admin,"evaluador":evaluador,"estado":"REALIZADA" if realizado else "PENDIENTE"})
    convertido=solicitudes[-1]
    seccion_2027=Seccion.objects.get(grado=grado_2027,nombre="A")
    Inscripcion.objects.update_or_create(institucion=institucion,alumno=alumnos[0],ciclo=ctx["ciclos"][2027],defaults={"oferta_academica":ctx["ofertas"][2027],"grado":grado_2027,"seccion":seccion_2027,"fecha_inscripcion":timezone.localdate(),"numero_inscripcion":"INS-2027-DEMO-0001","estado":Inscripcion.Estado.BORRADOR,"es_reingreso":True,"observaciones":"Conversión trazable por CUI desde admisión demo."})


def _rrhh(institucion, docentes, usuarios, admin):
    areas={}
    for orden,codigo,nombre in ((1,"DIRECCION","Dirección"),(2,"ADMIN","Administración"),(3,"SECRETARIA","Secretaría"),(4,"CONTABILIDAD","Contabilidad"),(5,"DOCENCIA","Docencia"),(6,"SERVICIOS","Servicios Generales"),(7,"TECNOLOGIA","Tecnología")):
        areas[codigo],_=AreaLaboral.objects.update_or_create(institucion=institucion,codigo=codigo,defaults={"nombre":nombre,"descripcion":DEMO_NOTE,"activa":True,"orden":orden})
    puestos={}
    for codigo,nombre,area,tipo in (("DIRECTOR","Director","DIRECCION","DIRECTIVO"),("SECRETARIA","Secretaria","SECRETARIA","ADMINISTRATIVO"),("CONTADOR","Contador","CONTABILIDAD","ADMINISTRATIVO"),("PROFESOR","Profesor","DOCENCIA","DOCENTE"),("AUXILIAR","Auxiliar administrativo","ADMIN","ADMINISTRATIVO"),("CONSERJE","Conserje","SERVICIOS","OPERATIVO"),("SOPORTE","Soporte TI","TECNOLOGIA","ADMINISTRATIVO")):
        puestos[codigo],_=PuestoLaboral.objects.update_or_create(institucion=institucion,codigo=codigo,defaults={"nombre":nombre,"area":areas[area],"descripcion":DEMO_NOTE,"tipo":tipo,"activo":True})
    base=(("Director","Demo","DIRECTOR",usuarios.get("DIRECTOR"),None),("Secretaria","Demo","SECRETARIA",usuarios.get("SECRETARIA"),None),("Contabilidad","Demo","CONTADOR",usuarios.get("CONTABILIDAD"),None),("Andrea","Administrativa","AUXILIAR",None,None),("Raúl","Servicios","CONSERJE",None,None),("Teresa","Sistemas","SOPORTE",None,None))
    perfiles=list(base)+[(d.primer_nombre,d.primer_apellido,"PROFESOR",d.usuario,d) for d in docentes[:5]]
    empleados=[]
    for idx,(nombre,apellido,puesto_codigo,usuario,docente) in enumerate(perfiles,1):
        puesto=puestos[puesto_codigo]
        empleado = Empleado.objects.filter(institucion=institucion, docente=docente).first() if docente else None
        empleado = empleado or Empleado.objects.filter(institucion=institucion,nombres=nombre,apellidos=apellido).first()
        empleado = empleado or Empleado(institucion=institucion,nombres=nombre,apellidos=apellido)
        empleado.nombres=nombre;empleado.apellidos=apellido;empleado.puesto=puesto;empleado.area=puesto.area;empleado.fecha_ingreso=date(2022+idx%4,1,15);empleado.estado=Empleado.Estado.ACTIVO;empleado.usuario=usuario;empleado.docente=docente;empleado.telefono=f"5580-{idx:04d}";empleado.correo=f"empleado{idx:02d}@demo.test";empleado.direccion="Ciudad de Guatemala";empleado.observaciones=DEMO_NOTE;empleado.creado_por=admin;empleado.save()
        empleados.append(empleado)
    hoy=timezone.localdate()
    for idx,empleado in enumerate(empleados):
        estado=ContratoLaboral.Estado.FINALIZADO if idx==len(empleados)-1 else ContratoLaboral.Estado.VIGENTE
        fin=hoy-timedelta(days=120) if estado==ContratoLaboral.Estado.FINALIZADO else hoy+timedelta(days=20 if idx==3 else 180)
        ContratoLaboral.objects.update_or_create(institucion=institucion,numero_contrato=f"DEMO-RRHH-{idx+1:03d}",defaults={"empleado":empleado,"tipo_contrato":"PLAZO_FIJO","fecha_inicio":date(2025,1,1),"fecha_fin":fin,"puesto":empleado.puesto,"jornada_laboral":"Tiempo completo","salario_referencia":Decimal("5000.00")+idx*Decimal("250.00"),"estado":estado,"observaciones":DEMO_NOTE,"motivo_finalizacion":"Contrato histórico demo" if estado==ContratoLaboral.Estado.FINALIZADO else "","creado_por":admin})
    tipos=[]
    for orden,(codigo,nombre,vigencia) in enumerate((("DPI","DPI",False),("NIT","NIT",False),("CV","Currículum",False),("TITULO","Título",False),("ANTECEDENTES","Antecedentes",True),("CONTRATO","Contrato",True)),1):
        tipo,_=TipoDocumentoEmpleado.objects.update_or_create(institucion=institucion,codigo=codigo,defaults={"nombre":nombre,"descripcion":DEMO_NOTE,"obligatorio":True,"requiere_vigencia":vigencia,"activo":True,"orden":orden});tipos.append(tipo)
    for e_idx,empleado in enumerate(empleados[:3]):
        cantidad=(6,3,5)[e_idx]
        for t_idx,tipo in enumerate(tipos[:cantidad]):
            DocumentoEmpleado.objects.update_or_create(institucion=institucion,empleado=empleado,tipo_documento=tipo,defaults={"nombre_original":"metadato-demo.pdf","fecha_emision":hoy-timedelta(days=300),"fecha_vencimiento":hoy+timedelta(days=15) if e_idx==2 and tipo.requiere_vigencia else None,"estado":DocumentoEmpleado.Estado.APROBADO,"observaciones":DEMO_NOTE,"cargado_por":admin,"revisado_por":admin})
    for idx,estado in enumerate((PermisoLaboral.Estado.PENDIENTE,PermisoLaboral.Estado.APROBADO,PermisoLaboral.Estado.RECHAZADO)):
        PermisoLaboral.objects.update_or_create(institucion=institucion,empleado=empleados[idx],tipo=("PERSONAL","VACACIONES","ESTUDIO")[idx],fecha_inicio=hoy+timedelta(days=idx+2),defaults={"fecha_fin":hoy+timedelta(days=idx+2),"motivo":"Solicitud administrativa demo","observaciones":DEMO_NOTE,"estado":estado,"solicitado_por":empleados[idx].usuario or admin,"autorizado_por":admin if estado!=PermisoLaboral.Estado.PENDIENTE else None,"fecha_resolucion":timezone.now() if estado!=PermisoLaboral.Estado.PENDIENTE else None})
    movimientos=("INGRESO","CAMBIO_PUESTO","RENOVACION","LICENCIA","REINTEGRO")
    for idx,tipo in enumerate(movimientos):
        empleado=empleados[idx]
        MovimientoLaboral.objects.update_or_create(institucion=institucion,empleado=empleado,fecha=date(2025,idx+1,15),tipo=tipo,descripcion=f"{tipo.replace('_',' ').title()} demo",defaults={"puesto_anterior":empleado.puesto,"puesto_nuevo":empleado.puesto,"area_anterior":empleado.area,"area_nueva":empleado.area,"registrado_por":admin})


def _historico(institucion, ctx, alumnos, admin):
    resultados=(ResultadoAnualAlumno.Resultado.PROMOVIDO,ResultadoAnualAlumno.Resultado.PROMOVIDO,ResultadoAnualAlumno.Resultado.NO_PROMOVIDO,ResultadoAnualAlumno.Resultado.EGRESADO,ResultadoAnualAlumno.Resultado.PROMOVIDO,ResultadoAnualAlumno.Resultado.PENDIENTE)
    for idx,(alumno,resultado) in enumerate(zip(alumnos[:6],resultados),1):
        grado_codigo="3B" if resultado==ResultadoAnualAlumno.Resultado.EGRESADO else "1B"
        grado=ctx["grados"][(2025,grado_codigo)];seccion=Seccion.objects.get(grado=grado,nombre="A")
        ins,_=Inscripcion.objects.update_or_create(institucion=institucion,alumno=alumno,ciclo=ctx["ciclos"][2025],defaults={"oferta_academica":ctx["ofertas"][2025],"grado":grado,"seccion":seccion,"fecha_inscripcion":date(2025,1,15),"numero_inscripcion":f"INS-2025-{idx:04d}","estado":Inscripcion.Estado.FINALIZADA,"es_reingreso":False,"observaciones":DEMO_NOTE})
        confirmado=resultado!=ResultadoAnualAlumno.Resultado.PENDIENTE
        ResultadoAnualAlumno.objects.update_or_create(institucion=institucion,ciclo=ctx["ciclos"][2025],alumno=alumno,defaults={"inscripcion":ins,"promedio_final":Decimal(str((88,76,55,92,64,59)[idx-1])),"resultado_sugerido":resultado,"resultado_final":resultado if confirmado else None,"observaciones":DEMO_NOTE,"generado_automaticamente":True,"confirmado_por":admin if confirmado else None,"fecha_confirmacion":timezone.now()-timedelta(days=200) if confirmado else None})


def _notificaciones(institucion):
    usuarios=list(get_user_model().objects.filter(asignaciones_institucion__institucion=institucion,asignaciones_institucion__activo=True).distinct())
    titulos=(("TAREA","Nueva tarea publicada","Revisa la actividad disponible"),("PAGO","Pago registrado","Tu pago fue aplicado correctamente"),("DOCUMENTO","Documento aprobado","El documento fue revisado"),("ENTREVISTA","Entrevista programada","Consulta la fecha de entrevista"),("PERMISO","Permiso aprobado","La solicitud fue resuelta"),("RECONOCIMIENTO","Reconocimiento académico","Felicitaciones por tu participación"))
    for u_idx,usuario in enumerate(usuarios):
        for idx,(tipo,titulo,mensaje) in enumerate(titulos):
            Notificacion.objects.update_or_create(institucion=institucion,usuario=usuario,tipo_origen=f"DEMO_{tipo}",origen_id=f"DEMO-{idx+1}",defaults={"titulo":titulo,"mensaje":mensaje,"url_destino":"/inicio/","leida":idx%2==u_idx%2,"fecha_lectura":timezone.now()-timedelta(days=1) if idx%2==u_idx%2 else None})


def _resumen(institucion):
    modelos=(
        ("Alumnos",Alumno),("Familias",Familia),("Docentes",Docente),("Cursos",CursoInstitucion),("Secciones",Seccion),("Sesiones asistencia",SesionAsistencia),("Actividades",ActividadEvaluacion),("Calificaciones",Calificacion),("Tareas",Tarea),("Cargos",Cargo),("Pagos",Pago),("Documentos alumnos",DocumentoAlumno),("Horarios",HorarioClase),("Seguimientos",RegistroSeguimiento),("Admisiones",SolicitudAdmision),("Empleados",Empleado),("Contratos",ContratoLaboral),
    )
    resumen = {nombre:modelo.objects.filter(institucion=institucion).count() for nombre,modelo in modelos}
    return {"Usuarios": get_user_model().objects.filter(username__startswith="demo_").count(), **resumen}


@transaction.atomic
def ampliar_demo(institucion, nivel, usuarios, admin):
    _saas(institucion,admin)
    ctx=_academico(institucion,nivel)
    docentes,asignaciones=_docentes(institucion,ctx,usuarios[UsuarioInstitucion.Rol.DOCENTE])
    alumnos,inscripciones,familias,encargados=_familias_alumnos(institucion,ctx,usuarios)
    _horarios(institucion,ctx,asignaciones)
    _asistencia(institucion,ctx,inscripciones,admin)
    _calificaciones_tareas(institucion,ctx,asignaciones,inscripciones,admin)
    _finanzas(institucion,ctx,alumnos,inscripciones,familias,admin)
    _expediente(institucion,alumnos,inscripciones,admin)
    _seguimiento(institucion,ctx,alumnos,inscripciones,encargados,docentes,admin)
    _admisiones(institucion,ctx,alumnos,admin,usuarios[UsuarioInstitucion.Rol.SECRETARIA],docentes)
    _rrhh(institucion,docentes,usuarios,admin)
    _historico(institucion,ctx,alumnos,admin)
    _notificaciones(institucion)
    return _resumen(institucion)
