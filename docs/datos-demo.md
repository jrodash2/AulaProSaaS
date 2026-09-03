# Datos demo de AulaPro

## Objetivo

Este documento sirve como guía funcional para recorrer AulaPro con datos de demostración coherentes y probar cada módulo de principio a fin.

El dataset demo debe permitir validar tanto escenarios normales como estados alternativos: pendientes, aprobados, rechazados, vencidos, históricos, activos, inactivos y procesos ya completados.

El comando oficial es:

```bash
python manage.py crear_demo_aulapro
```

Debe ser idempotente: puede ejecutarse varias veces sin duplicar registros.

---

## Institución demo

- **Nombre:** Colegio Demo AulaPro
- **Código:** AULAPRO-DEMO
- **País:** Guatemala
- **Zona horaria:** America/Guatemala
- **Estado:** Activa

La institución demo debe tener habilitados todos los módulos disponibles para poder recorrer todas las vistas.

---

## Credenciales demo

Contraseña común:

```text
AulaProDemo2026!
```

Usuarios:

| Usuario | Rol | Uso principal |
|---|---|---|
| demo_superadmin | Superadministrador | Administración SaaS y selección de institución |
| demo_propietario | Propietario | Recorrido completo de la institución |
| demo_director | Director | Gestión académica y administrativa |
| demo_admin | Administrador | Operación general |
| demo_secretaria | Secretaría | Alumnos, admisiones, expedientes e inscripciones |
| demo_contabilidad | Contabilidad | Finanzas y consultas autorizadas |
| demo_docente | Docente | Cursos, asistencia, calificaciones, tareas y horario |
| demo_padre | Padre/encargado | Portal familiar |
| demo_alumno | Alumno | Portal del estudiante |

---

# 1. Dashboard

## Usuario recomendado

`demo_propietario`

## Datos esperados

El dashboard debe mostrar valores distintos de cero en los principales indicadores, por ejemplo:

- alumnos activos;
- docentes;
- secciones;
- cargos pendientes;
- asistencia reciente;
- solicitudes de admisión;
- expedientes;
- empleados;
- notificaciones.

## Qué probar

1. Iniciar sesión como propietario.
2. Abrir el dashboard.
3. Confirmar que todas las tarjetas tengan datos coherentes.
4. Verificar que los enlaces de cada tarjeta abran el módulo correspondiente.
5. Cambiar entre modo claro y oscuro.

---

# 2. Estructura académica

## Dataset esperado

Ciclos:

- 2025 — histórico/cerrado;
- 2026 — ciclo actual;
- 2027 — planificación.

Oferta:

- Ciclo Básico Demo.

Grados:

- Primero Básico;
- Segundo Básico;
- Tercero Básico.

Secciones:

- Primero Básico A;
- Primero Básico B;
- Segundo Básico A;
- Tercero Básico A.

Jornada principal:

- Matutina.

Cursos sugeridos:

- Matemática;
- Comunicación y Lenguaje;
- Ciencias Naturales;
- Estudios Sociales;
- Inglés;
- Tecnología;
- Educación Física.

## Qué probar

- ciclos;
- oferta académica;
- grados;
- cursos;
- secciones;
- jornadas;
- activación/desactivación;
- cierre de ciclo;
- histórico.

---

# 3. Alumnos

## Dataset esperado

Aproximadamente 30 alumnos distribuidos entre varias secciones.

Debe haber:

- alumnos activos;
- al menos un alumno inactivo o retirado, según estados reales del modelo;
- familias con un hijo;
- familias con dos hermanos;
- diferentes encargados;
- responsables financieros;
- contactos de emergencia.

## Casos recomendados

### Alumno completo

Utilizar el alumno vinculado a `demo_alumno`.

Debe contar con:

- inscripción activa;
- familia;
- encargado;
- calificaciones;
- asistencia;
- tareas;
- horario;
- expediente;
- cargos/pagos;
- seguimiento visible.

### Familia con varios hijos

`demo_padre` debe tener al menos dos hijos vinculados para validar el cambio de estudiante en el portal.

## Qué probar

- crear alumno;
- editar alumno;
- detalle;
- familia;
- encargados;
- inscripción;
- filtros;
- búsqueda;
- estados;
- expediente.

---

# 4. Docentes

## Dataset esperado

Al menos cinco docentes:

1. Matemática;
2. Comunicación y Lenguaje;
3. Ciencias Naturales;
4. Inglés;
5. Tecnología.

Debe existir también al menos un docente inactivo para comprobar filtros y relaciones históricas.

## Usuario recomendado

`demo_docente`

## Qué probar como administración

- crear docente;
- editar;
- asignar cursos;
- asignar sección guía;
- vincular usuario;
- revisar horario.

## Qué probar como docente

- Mis cursos;
- Mis secciones;
- Mi horario;
- Asistencia;
- Calificaciones;
- Tareas;
- Seguimiento autorizado;
- Mi información laboral.

---

# 5. Horarios

## Dataset esperado

Bloques de lunes a viernes, por ejemplo:

| Bloque | Horario |
|---|---|
| 1 | 07:00–07:45 |
| 2 | 07:45–08:30 |
| Recreo | 08:30–08:50 |
| 3 | 08:50–09:35 |
| 4 | 09:35–10:20 |
| 5 | 10:20–11:05 |
| 6 | 11:05–11:50 |

Aulas:

- Aula 1;
- Aula 2;
- Aula 3;
- Laboratorio de Computación;
- Laboratorio de Ciencias.

Debe existir horario semanal para varias secciones sin conflictos.

## Qué probar

- horario por sección;
- horario por docente;
- horario por aula;
- creación de clase;
- edición;
- conflictos de docente;
- conflictos de sección;
- conflictos de aula;
- vista móvil;
- impresión.

---

# 6. Asistencia

## Dataset esperado

Al menos 20 sesiones de asistencia distribuidas en fechas distintas.

Deben existir alumnos con:

- asistencia excelente;
- varias tardanzas;
- ausencias;
- una o más ausencias justificadas.

## Usuario recomendado

`demo_docente`

## Qué probar

- crear sesión;
- marcar presentes;
- marcar ausentes;
- marcar tardanzas;
- justificar;
- editar sesión;
- consulta histórica;
- reportes.

---

# 7. Calificaciones

## Dataset esperado

Períodos académicos configurados para el ciclo actual.

Tipos de evaluación:

- Examen;
- Tarea;
- Proyecto;
- Participación;
- Laboratorio.

Actividades distribuidas entre varios cursos y períodos.

Las notas deben ser variadas, por ejemplo:

- 95;
- 88;
- 76;
- 64;
- 58.

No todos los estudiantes deben tener las mismas calificaciones.

## Qué probar

- crear actividad;
- registro masivo;
- editar notas;
- promedios;
- alumnos con rendimiento alto;
- rendimiento medio;
- notas bajas;
- ciclo cerrado.

---

# 8. Tareas

## Dataset esperado

Entre 10 y 15 tareas distribuidas en diferentes cursos.

Debe haber tareas:

- vigentes;
- publicadas;
- vencidas;
- borrador, si el modelo lo soporta.

Entregas con estados variados según los choices reales.

## Usuario recomendado

`demo_docente`

## Portal

Probar también con:

- `demo_alumno`;
- `demo_padre`.

## Qué probar

- creación;
- publicación;
- entregas;
- revisión;
- estado vencido;
- portal alumno;
- portal padre.

---

# 9. Finanzas

## Dataset esperado

Conceptos sugeridos:

- Inscripción;
- Colegiatura enero;
- Colegiatura febrero;
- Colegiatura marzo;
- Laboratorio;
- Actividad especial.

Crear diferentes escenarios:

### Caso A — solvente

Todos los cargos pagados.

### Caso B — pago parcial

Un cargo con abono y saldo pendiente.

### Caso C — pendiente

Uno o más cargos sin pago.

### Caso D — morosidad

Varios cargos pendientes.

### Caso E — pago reciente

Pago registrado recientemente para alimentar dashboard y reportes.

## Usuario recomendado

`demo_contabilidad`

## Qué probar

- crear cargo;
- registrar pago;
- pago total;
- pago parcial;
- saldo pendiente;
- estados;
- reportes;
- exportación.

Todos los montos deben utilizar `Decimal`.

---

# 10. Expediente digital del alumno

## Tipos de documento sugeridos

- Partida de nacimiento;
- Fotografía;
- Certificado del grado anterior;
- Documento del encargado;
- Formulario de inscripción;
- Constancia médica.

## Casos esperados

### Expediente completo

Un alumno con 100 %.

### Expediente incompleto

Un alumno entre 50 % y 80 %.

### Documento rechazado

Debe contener motivo de rechazo.

### Documento vencido

Cuando el modelo permita vigencia.

## Qué probar

- carga;
- revisión;
- aprobación;
- rechazo;
- reemplazo;
- descarga privada;
- filtros;
- porcentaje de cumplimiento;
- portal padre.

---

# 11. Seguimiento estudiantil

## Categorías demo

- Puntualidad;
- Responsabilidad;
- Convivencia;
- Rendimiento académico;
- Participación;
- Liderazgo.

## Casos esperados

- reconocimiento positivo;
- incidencia baja;
- incidencia media;
- caso abierto;
- caso en seguimiento;
- caso resuelto.

Debe haber niveles de confidencialidad distintos según los choices reales.

## Compromisos

Crear ejemplos:

- pendiente;
- cumplido;
- vencido.

## Reuniones

Al menos dos reuniones con encargados:

- una por puntualidad;
- una por rendimiento académico.

## Qué probar

- nuevo registro;
- reconocimiento;
- incidencia;
- compromiso;
- nota;
- reunión;
- cierre de caso;
- confidencialidad;
- portal padre.

---

# 12. Admisiones

## Dataset esperado

Entre 12 y 15 solicitudes para el ciclo 2027.

Distribuir entre estados disponibles, por ejemplo:

- Nueva;
- En revisión;
- Documentación pendiente;
- Entrevista pendiente;
- Evaluación pendiente;
- Aprobada;
- Lista de espera;
- Rechazada;
- Inscrita.

## Orígenes

Usar distintos canales disponibles:

- referido;
- redes sociales;
- página web;
- visita;
- publicidad.

## Casos recomendados

### Solicitud nueva

Para probar inicio de revisión.

### Documentación pendiente

Para probar carga y revisión de archivos.

### Entrevista programada

Para probar reprogramación/realización.

### Evaluación pendiente

Para registrar resultados.

### Aprobada

Para probar conversión a alumno.

### Lista de espera

Al menos dos solicitudes.

### Rechazada

Para probar motivo interno.

### Inscrita

Debe conservar la relación con el alumno generado.

## Qué probar

- formulario público;
- solicitud;
- detalle;
- documentos;
- entrevista;
- evaluación;
- aprobación;
- rechazo;
- lista de espera;
- conversión a alumno;
- inscripción.

---

# 13. RRHH

## Áreas demo

- Dirección;
- Administración;
- Secretaría;
- Contabilidad;
- Docencia;
- Servicios Generales;
- Tecnología.

## Puestos demo

- Director;
- Secretaria;
- Contador;
- Profesor;
- Auxiliar administrativo;
- Conserje;
- Soporte TI.

## Empleados

Al menos ocho empleados, incluyendo docentes vinculados correctamente.

## Contratos

Debe haber:

- contratos vigentes;
- uno próximo a vencer;
- uno finalizado;
- uno histórico.

## Documentos

Tipos sugeridos:

- DPI;
- NIT;
- Currículum;
- Título;
- Antecedentes;
- Contrato.

## Permisos laborales

Casos:

- pendiente;
- aprobado;
- rechazado.

## Historial laboral

Crear movimientos como:

- ingreso;
- cambio de puesto;
- renovación;
- licencia;
- reintegro.

## Qué probar

- nuevo empleado;
- edición;
- vínculo con usuario;
- vínculo con docente;
- contratos;
- expediente laboral;
- permisos;
- datos sensibles;
- historial;
- egreso.

---

# 14. Comunicaciones

## Dataset esperado

Crear notificaciones internas con estados leídas y no leídas.

Ejemplos:

- nueva tarea publicada;
- pago registrado;
- documento aprobado;
- entrevista programada;
- permiso aprobado;
- reconocimiento del alumno.

## Qué probar

- badge de no leídas;
- listado;
- marcar como leída;
- enlace al contexto relacionado cuando aplique.

---

# 15. Portal padre

## Usuario

```text
demo_padre
```

## Dataset esperado

Debe tener al menos dos hijos asociados.

Los hijos deben tener información suficiente para probar:

- notas;
- asistencia;
- tareas;
- horario;
- documentos;
- finanzas;
- seguimiento visible.

## Qué probar

1. Iniciar sesión.
2. Cambiar entre hijos.
3. Revisar notas.
4. Revisar tareas.
5. Revisar asistencia.
6. Revisar horario.
7. Revisar documentos.
8. Revisar estados financieros permitidos.
9. Revisar seguimiento visible.
10. Intentar manipular el ID de otro alumno y comprobar que no haya acceso.

---

# 16. Portal alumno

## Usuario

```text
demo_alumno
```

## Qué probar

- dashboard;
- notas;
- tareas;
- asistencia;
- horario;
- documentos autorizados;
- seguimiento visible;
- resultados anuales si aplica.

---

# 17. Cierre de ciclo y promoción

## Dataset esperado

Ciclo 2025 con resultados históricos.

Debe haber ejemplos reales según los choices del modelo:

- promovido;
- no promovido;
- egresado.

También deben existir resultados sugeridos y confirmados.

## Qué probar

- resultados anuales;
- confirmación;
- cierre;
- creación del siguiente ciclo;
- reinscripción;
- no duplicación de inscripción.

---

# 18. Reportes

Los datos generados por el comando deben alimentar reportes de:

- alumnos;
- asistencia;
- calificaciones;
- resultados anuales;
- finanzas;
- expedientes;
- horarios;
- seguimiento;
- admisiones;
- RRHH.

## Qué probar

- filtros;
- tenant;
- fechas;
- exportaciones XLSX;
- estados vacíos;
- datos suficientes para gráficos.

---

# 19. Escenarios rápidos de demostración

## Escenario 1 — Secretaría

Usuario:

```text
demo_secretaria
```

Recorrido:

```text
Admisiones
→ solicitud aprobada
→ convertir a alumno
→ seleccionar grado/sección
→ inscripción
→ expediente
```

## Escenario 2 — Docente

Usuario:

```text
demo_docente
```

Recorrido:

```text
Mi horario
→ seleccionar clase
→ asistencia
→ calificaciones
→ tarea
→ seguimiento de alumno
```

## Escenario 3 — Contabilidad

Usuario:

```text
demo_contabilidad
```

Recorrido:

```text
Finanzas
→ alumno con saldo
→ registrar pago parcial
→ revisar saldo
→ reporte
```

## Escenario 4 — Padre

Usuario:

```text
demo_padre
```

Recorrido:

```text
Portal
→ seleccionar hijo
→ notas
→ asistencia
→ horario
→ finanzas
→ documentos
→ seguimiento visible
```

## Escenario 5 — RRHH

Usuario:

```text
demo_director
```

Recorrido:

```text
RRHH
→ empleados
→ ficha de docente
→ contrato
→ documento
→ permiso
→ historial laboral
```

## Escenario 6 — Cierre de ciclo

Usuario:

```text
demo_director
```

Recorrido:

```text
Académico
→ ciclo histórico
→ resultados anuales
→ promoción
→ reinscripción
```

---

# 20. Resumen esperado del comando

Al finalizar, el comando debería mostrar un resumen similar a:

```text
AulaPro Demo creado/actualizado

Institución: Colegio Demo AulaPro
Usuarios demo: 9
Alumnos: ~30
Familias: ~12
Docentes: >=5
Cursos: >=7
Secciones: >=4
Sesiones asistencia: >=20
Tareas: >=10
Admisiones: >=12
Empleados: >=8

Credenciales:
Contraseña: AulaProDemo2026!
```

Los números exactos pueden variar si el modelo requiere ajustes, pero cada módulo debe contar con suficientes datos para probar sus vistas y procesos.

---

# 21. Validación final del dataset

Después de generar el demo ejecutar:

```bash
python manage.py crear_demo_aulapro
python manage.py crear_demo_aulapro
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Verificar:

- segunda ejecución sin duplicados;
- suite completa verde;
- dashboards con información;
- sin errores 500;
- tenant isolation intacto;
- roles funcionando;
- datos demo identificables;
- ningún dato de otra institución modificado.

---

## Nota

Este documento describe el dataset funcional de demostración que `crear_demo_aulapro` debe producir. Si un modelo cambia, los seeds y esta guía deben actualizarse juntos para que la documentación siga reflejando el comportamiento real de AulaPro.
