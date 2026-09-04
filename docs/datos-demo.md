# Datos integrales de demostración

## Regeneración

```bash
python manage.py migrate
python manage.py crear_demo_aulapro
```

El comando es transaccional e idempotente. Puede ejecutarse repetidamente; administra únicamente la institución `AULAPRO-DEMO` mediante claves naturales estables.

## Credenciales

Contraseña común: `AulaProDemo2026!`.

| Usuario | Uso recomendado |
|---|---|
| `demo_superadmin` | Plataforma global, instituciones y auditoría |
| `demo_propietario` | Recorrido administrativo completo y reportes |
| `demo_director` | Académico, docentes, seguimiento y RRHH |
| `demo_admin` | Operación institucional general |
| `demo_secretaria` | Alumnos, expedientes, admisiones y RRHH básico |
| `demo_contabilidad` | Finanzas, cargos, pagos y recibos |
| `demo_docente` | Clases, asistencia, notas, tareas, horario y perfil laboral |
| `demo_padre` | Portal con Ana López, Carlos López y Daniela García |
| `demo_alumno` | Portal completo de Ana López |

## Resumen del escenario

El seed crea 3 ciclos, 3 grados por ciclo, 4 secciones actuales, 7 materias por grado, 6 docentes, 30 alumnos, 12 familias, 20 sesiones de asistencia, 33 actividades, más de 200 calificaciones, 12 tareas, 60 cargos, 5 pagos, 100 celdas de horario, expedientes, seguimiento, 14 admisiones y 11 empleados. Las fechas de vencimientos, alertas, pagos y tareas se calculan respecto del día de ejecución.

## Dashboard

**Datos:** alumnos y docentes activos, asistencia reciente, pagos, saldos y módulos SaaS completos.  
**Probar:** entrar como `demo_propietario`, `demo_director`, `demo_docente`, `demo_padre` y `demo_alumno`.  
**Esperado:** métricas no vacías y redirección al dashboard apropiado del rol.

## Académico

**Datos:** ciclos 2025 cerrado, 2026 activo y 2027 en planificación; Nivel Básico Demo, jornadas Matutina/Vespertina, Primero/Segundo/Tercero Básico.  
**Probar:** histórico, ciclo actual, planificación y oferta.  
**Esperado:** Primero A, Primero B, Segundo A y Tercero A disponibles en 2026.

## Alumnos

**Datos:** 30 identidades ficticias, distribuidas 8/8/7/7; ejemplos activos, inactivo y retirado; 12 familias con hermanos.  
**Probar:** buscar `Ana López`, `Carlos López`, `Julia Arévalo` y `Kevin Bonilla`.  
**Esperado:** inscripciones y estados diferentes sin compartir datos con otro tenant.

## Docentes

**Datos:** Carlos Méndez (Matemática), Ana Fuentes (Comunicación), Luis Alvarado (Ciencias), Sofía Herrera (Inglés), Mario Rivas (Tecnología) y Elena Solís inactiva.  
**Probar:** `demo_docente`, filtros activos e histórico inactivo.  
**Esperado:** asignaciones distribuidas por curso y sección; el inactivo no aparece en altas nuevas.

## Asistencia

**Datos:** 20 sesiones cerradas con presentes, tardanzas, ausencias y una ausencia justificada.  
**Probar:** reportes por Ana, segundo alumno de cada sección y tercer alumno.  
**Esperado:** perfiles de asistencia excelente, tardanzas recurrentes y ausencias justificadas.

## Calificaciones

**Datos:** cuatro bimestres, tipos Examen/Tarea/Proyecto/Participación/Laboratorio, 33 actividades y notas 95/88/76/64/58, además de pendientes.  
**Probar:** planillas de Matemática y Comunicación de Primero A.  
**Esperado:** promedios variados, estudiantes destacados y casos bajo nota mínima.

## Tareas

**Datos:** 12 tareas borrador/publicadas/cerradas con fechas vencidas y próximas. Entregas pendientes, entregadas, tardías y no entregadas.  
**Probar:** `demo_docente`, `demo_alumno` y `demo_padre`.  
**Esperado:** cada portal ve únicamente las tareas de su sección/hijos.

## Finanzas

**Datos:** Inscripción, colegiaturas enero-marzo, Laboratorio y Actividad especial; 60 cargos y pagos por efectivo, transferencia y otro.  
**Probar:** primeros cinco alumnos. Ana tiene un cargo pagado; Carlos un pago parcial; otros mantienen saldos y morosidad.  
**Esperado:** cargos pagados, parciales, pendientes, vencidos y uno anulado.

## Portal

**Padre:** `demo_padre` tiene tres hijos para probar el selector; Ana y Carlos concentran notas, asistencia, tareas, finanzas, documentos, horario y seguimiento visible.  
**Alumno:** `demo_alumno` está vinculado a Ana López, con inscripción activa 2026 e historial 2025.  
**Esperado:** no es posible cambiar el identificador para consultar estudiantes ajenos.

## Expediente

**Datos:** Partida, Fotografía, Certificado anterior, Documento del encargado, Formulario y Constancia médica.  
**Probar:** Ana tiene expediente completo; Carlos incompleto y un documento rechazado; otros incluyen pendiente, vencido y no aplica.  
**Esperado:** porcentajes, alertas y motivo de rechazo visibles según permisos.

## Horarios

**Datos:** cinco aulas, seis períodos de clase y recreo; 100 clases de lunes a viernes para cuatro secciones.  
**Probar:** vista por Primero A, docente, sección y aula.  
**Esperado:** cuadrícula poblada sin conflictos reales de sección, docente ni aula.

## Seguimiento

**Datos:** reconocimientos, incidencias baja/media/alta, casos abiertos/en seguimiento/resueltos, tres compromisos, notas cronológicas y dos reuniones.  
**Probar:** puntualidad de Ana, liderazgo de Carlos y plan académico interno.  
**Esperado:** `demo_padre` solo ve PADRES/PUBLICABLE_PORTAL; INTERNO permanece oculto.

## Admisiones

**Datos:** 14 solicitudes 2027 en estados Nueva, Revisión, Documentación, Entrevista, Evaluación, Decisión, Aprobada, Lista de espera, Rechazada e Inscrita. Incluye documentos completos/incompletos/rechazados, cuatro estados de entrevista y evaluaciones variadas.  
**Probar:** las dos solicitudes en lista de espera y `Aspirante 14`.  
**Esperado:** `Aspirante 14` comparte CUI con Ana, conserva solicitud inscrita e inscripción 2027 trazable sin duplicar Alumno.

## RRHH

**Datos:** siete áreas y puestos, 11 empleados, docentes vinculados, contratos vigentes/por vencer/finalizado, expedientes completo/incompleto/por vencer, permisos y movimientos laborales.  
**Probar:** empleado de `demo_docente`, contrato que vence en 20 días y permisos pendientes/aprobados/rechazados.  
**Esperado:** salario y documentos permanecen restringidos por rol.

## Reportes

**Datos:** todos los reportes derivan de los escenarios anteriores.  
**Probar:** alumnos, asistencia, calificaciones, finanzas, horarios, expedientes, seguimiento, admisiones, RRHH y resultados anuales; descargar XLSX.  
**Esperado:** indicadores no vacíos y exports OpenXML válidos.

## Cierre y reinscripción

**Datos:** seis inscripciones finalizadas en 2025 con resultados promovido, no promovido, egresado y pendiente; algunos alumnos ya tienen inscripción 2026.  
**Probar:** filtros de resultados, confirmación pendiente y reinscripción sin duplicados.  
**Esperado:** badges históricos variados, ciclo 2025 de solo lectura y ciclo 2027 disponible para planificación.
