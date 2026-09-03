# Recursos Humanos

`Empleado` representa la relación laboral y es independiente de la cuenta `Usuario`. Puede vincularse explícitamente con un usuario institucional y, cuando corresponde, con la ficha `Docente`, sin duplicar esas entidades.

## Organización e historial

Las áreas y puestos son catálogos tenant-safe. Los cambios administrativos se conservan como `MovimientoLaboral`; un egreso marca al empleado como retirado y ofrece desactivar el acceso institucional, sin borrar usuario, docente, contratos o historial.

## Contratos y datos sensibles

Los contratos conservan historial y soportan plazo indefinido o fecha final. `contratos_por_vencer()` genera alertas administrativas. El salario de referencia no implementa nómina y solo se muestra al propietario o a usuarios con el permiso Django `rrhh.ver_datos_salariales`; nunca aparece en dashboard o exportación estándar.

## Expediente y permisos

Los requisitos documentales pueden ser globales, por puesto o área. La completitud cuenta únicamente requisitos obligatorios aplicables y aprobados. Los archivos usan UUID, firma segura, límite de 10 MB y descarga autorizada. Los permisos cubren ausencias administrativas y vacaciones, no asistencia estudiantil ni información clínica.

## Acceso

Propietario, dirección y administración gestionan; secretaría dispone de gestión básica sin salario; contabilidad consulta listados seguros; cada empleado autenticado consulta únicamente su perfil y solicita permisos. Padres y alumnos no acceden. Todo acceso por PK se filtra primero por institución.
