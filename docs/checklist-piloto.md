# Checklist previo al piloto AulaPro

## Infraestructura

- [ ] Configurar `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.
- [ ] Configurar PostgreSQL, respaldo automático y prueba de restauración.
- [ ] Configurar HTTPS, proxy, correo y almacenamiento privado de archivos.
- [ ] Ejecutar `migrate`, `check --deploy`, `collectstatic` y la suite completa.
- [ ] Verificar `/health/` y `/health/db/` detrás del balanceador.

## Institución y SaaS

- [ ] Confirmar tenant, ciclo actual, jornadas, oferta y módulos contratados.
- [ ] Probar acceso directo a un módulo deshabilitado: debe bloquearse.
- [ ] Revisar límites de alumnos y usuarios con el plan seleccionado.
- [ ] Confirmar zona horaria `America/Guatemala` y fecha/hora del servidor.

## Roles y navegación

- [ ] Recorrer dashboard y sidebar como propietario, director, administrador y secretaría.
- [ ] Confirmar que contabilidad solo accede a Finanzas y datos permitidos.
- [ ] Confirmar que docente solo ve clases, estudiantes, horario, seguimiento autorizado y perfil laboral propios.
- [ ] Confirmar que padre/alumno solo ven sus relaciones en Portal.
- [ ] Confirmar que superadmin selecciona contexto antes de operar un tenant.

## Flujos críticos

- [ ] Crear y editar alumno, docente y empleado; probar relaciones inactivas históricas.
- [ ] Crear inscripción y reinscripción sin duplicados ni exceder el plan.
- [ ] Registrar asistencia, calificaciones y tarea; comprobar bloqueo de ciclo cerrado.
- [ ] Probar pago total, parcial y saldo pendiente usando montos decimales.
- [ ] Probar horarios con conflicto de sección, docente y aula.
- [ ] Probar reconocimiento/incidencia y confidencialidad del seguimiento.
- [ ] Enviar admisión pública, usar token y convertir una solicitud aprobada.

## Archivos y exportaciones

- [ ] Subir PDF/JPG/PNG/WEBP permitidos y rechazar EXE/BAT/CMD/SH/PHP/HTML/JS.
- [ ] Intentar descargar documentos desde otro tenant y otro padre: debe responder 403/404.
- [ ] Abrir XLSX de alumnos, resultados, expedientes, horarios, seguimiento, admisiones, RRHH y finanzas.
- [ ] Confirmar que exports RRHH no incluyen salario, DPI o NIT sin permiso.

## UX y dispositivos

- [ ] Probar 375, 768, 1366 y 1920 px, especialmente Portal, admisión, documentos y horarios.
- [ ] Probar modo claro/oscuro, contraste, foco, labels, alt y botones de icono.
- [ ] Abrir/cancelar/confirmar repetidamente el modal global y verificar ausencia de backdrops residuales.
- [ ] Probar doble clic en Guardar y una conexión móvil lenta.
- [ ] Revisar consola sin errores JavaScript y páginas vacías sin excepciones.

## Salida

- [ ] Cero P0/P1 abiertos.
- [ ] Suite completa verde y sin migraciones pendientes.
- [ ] Demo ejecutado dos veces sin duplicados.
- [ ] Backups, responsable de soporte y plan de reversión confirmados.
