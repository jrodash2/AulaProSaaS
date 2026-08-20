# Catálogo académico global

Este módulo representa información académica normativa compartida por toda la plataforma. Sus modelos **no pertenecen a una institución**. La futura oferta académica institucional deberá referenciar versiones del catálogo sin copiarlas ni convertirlas en datos del tenant.

## Fuentes y acuerdos

`CarreraCatalogo` y `VersionPensum` conservan el nombre de la fuente oficial, su URL, acuerdo ministerial y fechas conocidas. Una fuente vacía significa “pendiente de verificación”; nunca debe completarse con información inferida. Los documentos binarios oficiales deberán almacenarse fuera de la base de datos si se incorporan en otra etapa.

## Versionado y vigencia

Cada carrera admite múltiples `VersionPensum`. Los estados distinguen borradores, versiones vigentes, material en revisión, histórico y derogado. Las relaciones normativas usan `PROTECT`; el flujo habitual debe cambiar estados o desactivar registros, no eliminar historia.

La duplicación crea una versión `BORRADOR`, copia grados y asociaciones `CursoPensum`, y reutiliza los mismos objetos `CursoCatalogo`.

## Importación futura

La estructura `catalogos/management/commands/` está reservada para `importar_catalogo_mineduc`. El comando futuro deberá:

1. recibir archivos o fuentes explícitas y trazables;
2. validar antes de persistir;
3. ejecutar cada lote de manera atómica e idempotente;
4. generar un reporte de altas, cambios, omisiones y errores;
5. crear nuevas versiones en lugar de sobrescribir historia normativa;
6. no activar automáticamente información que requiera revisión humana.

En esta etapa no existe scraping, carga masiva ni información oficial precargada.
