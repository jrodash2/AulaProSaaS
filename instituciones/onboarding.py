from suscripciones.services import modulo_habilitado, obtener_uso_plan, suscripcion_actual

PASOS = (
    (1, "Datos de institución", "INSTITUCION"),
    (2, "Ciclo escolar", "ACADEMICO"),
    (3, "Jornada", "ACADEMICO"),
    (4, "Oferta académica", "ACADEMICO"),
    (5, "Grados y secciones", "ACADEMICO"),
    (6, "Cursos", "ACADEMICO"),
    (7, "Docentes", "DOCENTES"),
    (8, "Alumnos", "ALUMNOS"),
    (9, "Finanzas", "FINANZAS"),
    (10, "Portal y comunicación", "PORTAL"),
    (11, "Finalización", "FINAL"),
)


def estado_onboarding(institucion):
    from academico.models import CicloEscolar, CursoInstitucion, GradoInstitucion, JornadaInstitucion, OfertaAcademica, Seccion
    from alumnos.models import Inscripcion
    from docentes.models import Docente
    from finanzas.models import ConfiguracionFinanciera
    from .models import OnboardingInstitucion

    onboarding, _ = OnboardingInstitucion.objects.get_or_create(institucion=institucion)
    def habilitado(codigo):
        if codigo in ("INSTITUCION", "FINAL"):
            return True
        if codigo == "PORTAL":
            # The combined step is useful when either customer-facing module
            # is part of the plan.
            return modulo_habilitado(institucion, "PORTAL") or modulo_habilitado(institucion, "COMUNICACIONES")
        return modulo_habilitado(institucion, codigo)
    reales = {
        1: bool(institucion.nombre and institucion.codigo),
        2: CicloEscolar.objects.filter(institucion=institucion, activo=True).exists(),
        3: JornadaInstitucion.objects.filter(institucion=institucion, activa=True).exists(),
        4: OfertaAcademica.objects.filter(institucion=institucion, activa=True).exists(),
        5: GradoInstitucion.objects.filter(institucion=institucion, activo=True).exists() and Seccion.objects.filter(institucion=institucion, activa=True).exists(),
        6: CursoInstitucion.objects.filter(institucion=institucion, activo=True).exists(),
        7: Docente.objects.filter(institucion=institucion, estado="ACTIVO").exists(),
        8: Inscripcion.objects.filter(institucion=institucion, estado="ACTIVA").exists(),
        9: ConfiguracionFinanciera.objects.filter(institucion=institucion).exists(),
        10: True,
        11: onboarding.completado,
    }
    pasos = []
    for numero, nombre, modulo in PASOS:
        disponible = habilitado(modulo)
        pasos.append({"numero": numero, "nombre": nombre, "modulo": modulo, "disponible": disponible, "completo": reales[numero] if disponible else True, "omitido_plan": not disponible})
    completos = sum(1 for paso in pasos[:-1] if paso["completo"])
    return {
        "onboarding": onboarding,
        "pasos": pasos,
        "paso": pasos[onboarding.paso_actual - 1],
        "completos": completos,
        "porcentaje": round((onboarding.paso_actual - 1) * 100 / (OnboardingInstitucion.TOTAL_PASOS - 1)),
        "suscripcion": suscripcion_actual(institucion),
        "uso": obtener_uso_plan(institucion),
    }


def resumen_onboarding(institucion):
    from academico.models import CicloEscolar, CursoInstitucion, GradoInstitucion, JornadaInstitucion, OfertaAcademica, Seccion
    from alumnos.models import Inscripcion
    from docentes.models import Docente
    return {
        "ciclo": CicloEscolar.objects.filter(institucion=institucion, es_actual=True).first() or CicloEscolar.objects.filter(institucion=institucion).order_by("-anio").first(),
        "jornadas": JornadaInstitucion.objects.filter(institucion=institucion, activa=True).count(),
        "ofertas": OfertaAcademica.objects.filter(institucion=institucion, activa=True).count(),
        "grados": GradoInstitucion.objects.filter(institucion=institucion, activo=True).count(),
        "secciones": Seccion.objects.filter(institucion=institucion, activa=True).count(),
        "cursos": CursoInstitucion.objects.filter(institucion=institucion, activo=True).count(),
        "docentes": Docente.objects.filter(institucion=institucion, estado="ACTIVO").count(),
        "alumnos": Inscripcion.objects.filter(institucion=institucion, estado="ACTIVA").count(),
    }
