# Entorno demo de AulaPro

AulaPro incluye un comando idempotente para generar datos de prueba y recorrer los módulos desarrollados sin utilizar el Django Admin.

## Crear/actualizar datos demo

```bash
python manage.py migrate
python manage.py crear_demo_aulapro
```

Por seguridad, el comando solo se ejecuta con `DEBUG=True` salvo que se indique explícitamente `--permitir-produccion`. No se recomienda usarlo sobre una base de datos real.

## Institución demo

- **Nombre:** Colegio Demo AulaPro
- **Código:** `AULAPRO-DEMO`
- **Ciclo:** 2026
- **Jornada:** Matutina
- **Oferta:** Ciclo Básico Demo
- **Grado:** Primero Básico
- **Sección:** A
- **Cursos:** Matemática, Comunicación y Lenguaje, Tecnología

## Usuarios

| Usuario | Rol |
|---|---|
| `demo_superadmin` | Superadministrador |
| `demo_propietario` | Propietario |
| `demo_director` | Director |
| `demo_admin` | Administrador |
| `demo_secretaria` | Secretaría |
| `demo_contabilidad` | Contabilidad |
| `demo_docente` | Docente |

Contraseña predeterminada:

```text
AulaProDemo2026!
```

Puede cambiarse al ejecutar:

```bash
python manage.py crear_demo_aulapro --password "OtraClaveSegura"
```

## Datos creados

El comando genera o actualiza:

- una institución;
- usuarios para todos los roles institucionales y un superadministrador;
- ciclo, jornada, oferta, grado, sección y tres cursos;
- 12 alumnos con inscripción activa;
- familia y encargado demo;
- docente con usuario y asignación de Matemática;
- docente guía;
- una sesión de asistencia con presentes, tardanzas y ausencias;
- configuración de calificaciones;
- primer bimestre;
- tipo de evaluación;
- actividad de Matemática;
- notas demo.

El comando usa `get_or_create` / `update_or_create` para poder ejecutarse varias veces sin duplicar intencionalmente el escenario principal.

## Qué revisar por rol

### Superadministrador
- dashboard global;
- instituciones;
- usuarios globales;
- catálogo académico;
- auditoría;
- configuración.

### Propietario / Director / Administrador
- dashboard institucional;
- académico;
- alumnos;
- docentes;
- asistencia;
- calificaciones;
- usuarios y configuración.

### Secretaría
- navegación y permisos de gestión permitidos;
- alumnos e inscripciones;
- consultas de asistencia/calificaciones según permisos actuales.

### Contabilidad
- verificar que módulos académicos restringidos no permitan modificaciones indebidas;
- Finanzas seguirá como módulo futuro hasta su sprint.

### Docente
- Mis clases;
- asistencia de sus clases;
- actividades;
- planillas de calificaciones;
- perfil.

