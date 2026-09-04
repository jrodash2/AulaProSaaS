from collections import defaultdict
from django.db.models import Count
from django.utils import timezone

from .models import HorarioClase

RELACIONES=("bloque","aula","seccion__grado","asignacion_docente__curso","asignacion_docente__docente")

def detectar_conflictos(horario):
    if not horario.dia_semana or not horario.bloque_id or not horario.asignacion_docente_id:return []
    qs=HorarioClase.objects.filter(institucion_id=horario.institucion_id,dia_semana=horario.dia_semana,activo=True)
    qs=qs.filter(bloque__hora_inicio__lt=horario.bloque.hora_fin,bloque__hora_fin__gt=horario.bloque.hora_inicio).exclude(pk=horario.pk).select_related(*RELACIONES)
    conflictos=[]
    for existente in qs:
        tramo=f"{horario.get_dia_semana_display()} de {horario.bloque.hora_inicio:%H:%M} a {horario.bloque.hora_fin:%H:%M}"
        if existente.seccion_id==horario.seccion_id:conflictos.append(f"La sección ya tiene {existente.curso} el {tramo}.")
        if existente.asignacion_docente.docente_id==horario.docente.pk:conflictos.append(f"{horario.docente.nombre_completo} ya tiene {existente.curso} con {existente.seccion} el {tramo}.")
        if horario.aula_id and existente.aula_id==horario.aula_id:conflictos.append(f"El aula {horario.aula} ya está ocupada por {existente.seccion} el {tramo}.")
    return conflictos

def horario_seccion(seccion):return HorarioClase.objects.filter(institucion=seccion.institucion,seccion=seccion,activo=True).select_related(*RELACIONES).order_by("bloque__orden")
def horario_docente(docente):return HorarioClase.objects.filter(institucion=docente.institucion,asignacion_docente__docente=docente,activo=True).select_related(*RELACIONES).order_by("bloque__orden")

def matriz_semanal(items,bloques):
    mapa={(h.bloque_id,h.dia_semana):h for h in items};dias=HorarioClase.Dia.choices[:6]
    return [{"bloque":b,"celdas":[{"codigo":codigo,"nombre":nombre,"clase":mapa.get((b.pk,codigo))} for codigo,nombre in dias]} for b in bloques],dias

def validar_carga_semanal(seccion):
    cursos=seccion.grado.cursos.filter(activo=True);conteos=dict(horario_seccion(seccion).values_list("asignacion_docente__curso_id").annotate(total=Count("id")))
    filas=[]
    for curso in cursos:
        esperado=curso.periodos_semanales or 0;asignados=conteos.get(curso.pk,0);filas.append({"curso":curso,"esperado":esperado,"asignados":asignados,"faltan":max(esperado-asignados,0),"exceso":max(asignados-esperado,0)})
    return filas

def proxima_clase(seccion,ahora=None):
    ahora=timezone.localtime(ahora or timezone.now());dias=("LUNES","MARTES","MIERCOLES","JUEVES","VIERNES","SABADO","DOMINGO");dia=dias[ahora.weekday()]
    return horario_seccion(seccion).filter(dia_semana=dia,bloque__hora_fin__gte=ahora.time()).order_by("bloque__hora_inicio").first()

def clase_actual_docente(docente,ahora=None):
    ahora=timezone.localtime(ahora or timezone.now());dias=("LUNES","MARTES","MIERCOLES","JUEVES","VIERNES","SABADO","DOMINGO");dia=dias[ahora.weekday()]
    return horario_docente(docente).filter(dia_semana=dia,bloque__hora_inicio__lte=ahora.time(),bloque__hora_fin__gte=ahora.time()).first()
