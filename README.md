# AulaPro SaaS

AulaPro es una plataforma SaaS multiinstitución para la administración académica, administrativa y financiera de establecimientos educativos de Guatemala. Incluye operación multiinstitución, académico, alumnos, docentes, asistencia, calificaciones, tareas, finanzas, portal familiar, comunicaciones y reportes integrales.

## Arquitectura inicial

- **Django 5.2 LTS y Python 3.12**, con templates del servidor, Bootstrap 5 y JavaScript sin frameworks.
- **PostgreSQL** en producción; SQLite queda disponible únicamente como alternativa local y para pruebas automatizadas.
- Configuración unificada y controlada por variables de entorno, con validaciones que impiden usar secretos, hosts o SQLite inseguros en producción.
- Usuario personalizado (`cuentas.Usuario`) definido desde la primera migración.
- Apps de dominio separadas y tenant-aware para la operación académica, administrativa, financiera, portal, comunicación y analítica.
- Interfaz independiente del Django Admin, que se conserva para operación técnica.
- Catálogo académico global versionado, separado por completo de la futura oferta académica de cada institución.

## Estrategia multiinstitución

Los datos de cada módulo de negocio deberán incluir una `ForeignKey` obligatoria a `Institucion`. La pertenencia se modela mediante `UsuarioInstitucion`, lo cual permite múltiples instituciones por usuario y prohíbe asignaciones duplicadas.

`InstitucionActivaMiddleware` resuelve la institución activa desde las **asignaciones activas almacenadas en el servidor**. Una clave de sesión puede señalar una asignación, pero siempre se vuelve a consultar filtrando por el usuario autenticado, la asignación activa y la institución activa. Un identificador manipulado o perteneciente a otro usuario se descarta y nunca se usa directamente para consultar datos. Las vistas institucionales consumen `request.institucion`, no un ID recibido por URL o formulario.

Reglas para módulos futuros:

1. nunca aceptar `institucion_id` del cliente como autorización;
2. filtrar querysets con `request.institucion` desde el inicio;
3. usar `institucion_required` en vistas institucionales;
4. probar explícitamente el aislamiento entre dos instituciones;
5. registrar operaciones sensibles con `auditoria.services.registrar_evento`.

## Requisitos

- Python 3.12 o compatible
- PostgreSQL 15 o superior recomendado
- Compilador y librerías del sistema que requiera `psycopg` (el paquete incluye binarios para entornos habituales)

## Instalación local

```bash
git clone https://github.com/jrodash2/AulaProSaaS.git
cd AulaProSaaS
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Genere una clave segura y colóquela como `SECRET_KEY` en `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### PostgreSQL

Ejemplo de creación local (ajuste usuario y contraseña):

```sql
CREATE USER aulapro WITH PASSWORD 'una-clave-segura';
CREATE DATABASE aulapro OWNER aulapro;
```

Configure la conexión en `.env`:

```dotenv
DATABASE_URL=postgresql://aulapro:una-clave-segura@localhost:5432/aulapro
```

Complete la instalación:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visite `http://127.0.0.1:8000/login/`. El superusuario accede al panel SaaS global. Un usuario institucional necesita una asignación activa creada desde Django Admin.

## Pruebas y calidad

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Las pruebas cubren autenticación, separación del panel global, unicidad de asignaciones y aislamiento multiinstitución, incluida la manipulación de la clave de sesión.

## Catálogo académico global

Los superusuarios acceden a `/catalogos/carreras/` para administrar niveles, tipos de carrera, carreras, áreas, cursos y versiones históricas de pensum. Ninguno de estos modelos contiene `institucion_id`: representan referencias globales que las instituciones podrán seleccionar en una etapa posterior.

Una carrera posee múltiples versiones; cada versión contiene grados y `CursoPensum` relaciona un curso reutilizable con un grado concreto, su orden, períodos semanales y obligatoriedad. Las versiones pueden duplicarse de forma atómica sin duplicar `CursoCatalogo`. La estrategia de fuentes oficiales e importación futura está documentada en `catalogos/README.md`.

## Datos demo

Con `DEBUG=True`, `python manage.py crear_demo_aulapro` crea o actualiza un entorno idempotente por roles. Consulte [`docs/demo.md`](docs/demo.md). En producción el comando está bloqueado salvo flag explícito.

## Health checks

- `GET /health/`: estado y versión de la aplicación.
- `GET /health/db/`: disponibilidad mínima de la base mediante `SELECT 1`.

Ambos endpoints omiten configuración y datos institucionales.

## Producción

Use el módulo unificado `DJANGO_SETTINGS_MODULE=config.settings`, una `SECRET_KEY` externa y PostgreSQL. Ejecute `check --deploy`, migraciones y `collectstatic` antes del release. La guía completa está en [`docs/production.md`](docs/production.md) y el procedimiento de respaldo/restauración en [`docs/backup.md`](docs/backup.md).

## Documentación operativa

- [Producción](docs/production.md)
- [Backups](docs/backup.md)
- [Demo](docs/demo.md)
- [Matriz de rutas y permisos](docs/routes-permissions.md)
- [QA Sprint 13](docs/qa-sprint13.md)
- [Planes y suscripciones SaaS](docs/suscripciones.md)
- [Onboarding de instituciones](docs/onboarding.md)

## Alcance siguiente

`catalogos` conserva las referencias globales oficiales y `academico` materializa, con trazabilidad, la oferta, grados, cursos, jornadas y secciones particulares de cada institución. No se modifica el pensum global al personalizar la estructura institucional.
