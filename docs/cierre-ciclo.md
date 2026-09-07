# Cierre de ciclo, promoción y reinscripción

## Preparación y validaciones

El alumno es una entidad permanente y cada `Inscripcion` representa únicamente un ciclo. El cierre nunca cambia una inscripción para apuntarla al año siguiente ni mueve calificaciones, asistencia, tareas o cargos financieros.

Antes del cierre se comprueba que todos los períodos activos estén cerrados y que cada inscripción activa tenga un resultado final confirmado. Las tareas abiertas se presentan como advertencias; los períodos abiertos y resultados sin confirmar son bloqueantes. Las notas ausentes permanecen **pendientes** y nunca se convierten en cero.

## Resultados y promoción

`generar_resultado_anual` reutiliza el cálculo de calificaciones existente para cada curso obligatorio y período. Guarda el promedio como `Decimal`, separado de la decisión administrativa:

- `resultado_sugerido` es automático;
- `resultado_final` requiere confirmación;
- retirados y trasladados no se promueven;
- una aprobación en el último grado de la oferta produce `EGRESADO`;
- el grado siguiente se determina por `orden` dentro de la oferta, nunca por su nombre.

La nota mínima institucional genera una sugerencia, no una decisión irreversible. Los borradores (sin fecha de confirmación) no deben exponerse en portales.

## Cierre

El cierre finaliza las inscripciones activas confirmadas, marca el ciclo `CERRADO`, lo desactiva y conserva íntegro su historial. Un ciclo cerrado no acepta inscripciones activas nuevas. La reapertura automática no forma parte de este sprint: debe tratarse como proceso excepcional, autorizado y auditado cuando no haya reinscripciones derivadas.

## Nuevo ciclo y reinscripción

`crear_ciclo_siguiente` copia las entidades que dependen del ciclo: ofertas, grados, cursos y secciones. Reutiliza jornadas institucionales y catálogos globales. No copia asignaciones docentes o de guía ni genera cargos financieros.

La reinscripción crea una nueva inscripción y conserva la anterior. Para promovidos exige el orden siguiente; para no promovidos, el mismo orden. El operador elige explícitamente la sección destino. El servicio valida tenant, capacidad, límite SaaS del ciclo destino e idempotencia. El proceso masivo usa una sola transacción: un error crítico revierte el lote completo.

## Historial, reportes y portales

Los listados históricos pueden relacionar las inscripciones por alumno y mostrar únicamente resultados confirmados. La tasa de promoción se define como `PROMOVIDOS / (PROMOVIDOS + NO_PROMOVIDOS + EGRESADOS)`; retirados y trasladados se excluyen. Los reportes deben filtrar por ciclo, oferta, grado, sección y resultado, y pueden exportar exactamente ese conjunto a Excel o a una vista imprimible no oficial.

Los saldos del ciclo anterior continúan visibles como deuda histórica. La reinscripción no crea colegiaturas ni cargo de inscripción de forma predeterminada.

## Restricciones posteriores

Después del cierre se permite consulta. Se deben rechazar nuevas inscripciones, calificaciones, asistencia, tareas y cambios estructurales ordinarios asociados al ciclo cerrado. Toda futura interfaz de cierre debe exigir confirmación fuerte (`CERRAR <año>`) y registrar inicio, generación, confirmación, cierre, creación de ciclo y reinscripciones en auditoría.
