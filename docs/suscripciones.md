# Planes y suscripciones SaaS

Este dominio representa la relación comercial **AulaPro → institución**. No utiliza cargos, pagos ni recibos de `finanzas`, que pertenecen a la relación colegio → familias.

## Planes y módulos

`Plan` almacena precios `Decimal`, capacidades y visibilidad comercial. `ModuloSaaS` y `PlanModulo` controlan Académico, Alumnos, Docentes, Asistencia, Calificaciones, Tareas, Finanzas, Portal, Comunicaciones y Reportes. Deshabilitar un módulo oculta su acceso y el middleware bloquea la URL; nunca elimina los datos existentes.

Los planes INICIO, CRECE, PRO y EMPRESA se crean de forma idempotente mediante `crear_demo_aulapro` o `asignar_plan_inicial`. Los precios son datos editables, nunca constantes de templates.

La migración `0002_modulos_saas_iniciales` garantiza que el catálogo oficial exista incluso antes de ejecutar comandos demo. `sincronizar_modulos_saas` repara nombres, descripciones, iconos y orden sin borrar módulos personalizados ni reactivar módulos desactivados, salvo que se use explícitamente `--reactivar`.

El formulario de plan muestra cards seleccionables. Al guardar, cada módulo activo obtiene un `PlanModulo` con `habilitado=True` o `False`; al editar se leen las selecciones desde esa relación. INICIO incluye el núcleo académico, CRECE agrega Tareas, Portal y Comunicaciones, y PRO/EMPRESA incluyen todo. Estas selecciones son datos configurables en base de datos, no reglas de las vistas.

## Suscripción y estado efectivo

Los estados persistidos son PRUEBA, ACTIVA, VENCIDA, SUSPENDIDA y CANCELADA. `estado_suscripcion()` combina estado, inicio, fin y vencimiento del trial sin escribir durante un GET. `actualizar_suscripciones` materializa vencimientos y puede ejecutarse por cron.

Solo puede existir una suscripción actual PRUEBA, ACTIVA o SUSPENDIDA por institución; VENCIDA y CANCELADA forman el historial natural. Renovaciones, cambios, suspensiones, reactivaciones y cancelaciones crean `HistorialSuscripcion` y `EventoAuditoria` global.

## Consumo y límites

- **Alumnos:** inscripciones ACTIVA del ciclo actual; fichas sin inscripción e históricos no consumen.
- **Usuarios:** asignaciones activas PROPIETARIO, DIRECTOR, ADMINISTRADOR, SECRETARIA, CONTABILIDAD y DOCENTE.
- **Portal:** PADRE y ALUMNO no consumen el límite administrativo.
- Los overrides de la suscripción prevalecen sobre el plan.

Al alcanzar el 100 %, solo se bloquean nuevas inscripciones o activaciones que aumenten consumo. Consultar, editar datos existentes y retirar alumnos sigue permitido. La importación XLSX valida el lote completo antes de escribir y la transacción evita resultados parciales.

## Vencimiento y suspensión

Una suscripción vencida funciona en modo lectura: los GET conservan acceso y las escrituras reciben 403 con una explicación de renovación. SUSPENDIDA/CANCELADA dirige a propietarios y directores a la pantalla de suscripción; los demás roles no acceden. Superadministradores nunca quedan bloqueados.

## Comandos

```bash
python manage.py asignar_plan_inicial --plan INICIO --trial-dias 30
python manage.py actualizar_suscripciones
python manage.py generar_alertas_suscripciones
python manage.py sincronizar_modulos_saas
```

Las alertas se generan a 30, 15, 7 y 1 días para propietarios. La clave de origen evita duplicados. No se envían correos ni WhatsApp.

## Métricas

MRR incluye únicamente suscripciones ACTIVA vigentes. La modalidad anual se convierte a mensual dividiendo entre 12; suspendidas, vencidas y canceladas no cuentan. ARR es MRR × 12. Estas métricas no consultan la app `finanzas`.

## Operación comercial

Solo superadministradores pueden cambiar plan, precio, vigencia, límites o estado. Un downgrade se rechaza cuando el consumo actual supera el nuevo límite. El propietario puede consultar uso y enviar `SolicitudCambioPlan`, pero no modificar directamente el contrato. No se implementan cobros, facturas SaaS, checkout ni pasarela en este sprint.
