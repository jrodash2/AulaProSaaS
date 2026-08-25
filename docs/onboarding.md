# Onboarding de instituciones

El onboarding es una guía opcional de once pasos para preparar una institución nueva sin bloquear el uso normal de AulaPro. Propietario y Administrador pueden modificarlo; Director puede consultar el estado. Docentes, padres y alumnos no tienen acceso.

## Flujo

1. Datos de institución.
2. Ciclo escolar actual.
3. Jornadas.
4. Oferta académica.
5. Grados y secciones.
6. Cursos.
7. Docentes.
8. Alumnos e importación Excel.
9. Configuración y conceptos financieros.
10. Portal y comunicaciones.
11. Resumen y finalización.

Los primeros pasos reutilizan `InstitucionForm`, `CicloEscolarForm` y `JornadaForm`. Los pasos académicos enlazan a las vistas existentes y la carga de alumnos usa el importador XLSX original, incluida la validación de capacidad del plan. Finanzas crea únicamente configuración y conceptos; nunca genera cargos.

## Estado y reanudación

`OnboardingInstitucion` conserva el paso actual, usuario que actualizó, finalización y omisión. Cada envío guarda el avance, por lo que puede abandonarse y retomarse desde el dashboard. `estado_onboarding(institucion)` combina ese progreso con datos reales: un ciclo activo o una jornada ya existente aparecen completados aunque hayan sido creados fuera del asistente.

El onboarding no redirige obligatoriamente ni impide usar módulos configurados. El propietario puede usar **Configurar después y omitir la guía**; la información permanece y el flujo puede reiniciarse administrativamente.

## Integración con el plan

Cada paso consulta `modulo_habilitado()`. Si Finanzas, Portal u otro módulo no forma parte del plan, se muestra como omitido y no se solicita configuración. En el paso de alumnos se presenta el uso actual frente al límite contratado.

## Alta desde plataforma

La creación de una institución por superadministrador solicita datos, plan, trial y credenciales iniciales del propietario en una transacción. El resultado incluye Institución, Suscripción, `UsuarioInstitucion` PROPIETARIO y `OnboardingInstitucion` en el paso 1. La contraseña se almacena mediante `create_user()` y nunca como texto plano.

## Demo

`crear_demo_aulapro` marca el Colegio Demo como completado para no interrumpir las demostraciones. Una nueva institución real comienza en el paso 1.
