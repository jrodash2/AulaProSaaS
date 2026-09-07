# Expediente digital del alumno

El módulo `EXPEDIENTE` mantiene separados el alumno permanente, los requisitos institucionales y cada archivo presentado. Un `TipoDocumentoAlumno` define el catálogo, `RequisitoDocumentoAlumno` calcula a quién aplica y `DocumentoAlumno` conserva cada entrega o reemplazo como registro independiente.

## Seguridad de archivos

Se aceptan PDF, JPG/JPEG, PNG y WEBP de hasta 10 MB. Se valida extensión y firma básica del contenido. El nombre original se guarda únicamente como metadato; la ruta utiliza institución, alumno y un UUID generado por el servidor. Las descargas pasan por vistas autenticadas que validan tenant, rol, alumno autorizado y visibilidad en portal. En producción el servidor web no debe publicar `MEDIA_ROOT`; debe delegar la entrega a la vista autorizada o a un mecanismo privado equivalente.

## Checklist y completitud

Los requisitos globales se aplican a toda la institución. Los alcances opcionales de nivel, oferta, grado y ciclo restringen su aplicación. El porcentaje es `obligatorios aprobados / obligatorios aplicables`. Los opcionales no reducen el porcentaje y una decisión `NO_APLICA`, acompañada de motivo y revisor, sale del denominador. Un documento permanente aprobado, sin ciclo en su requisito, se reutiliza en ciclos posteriores.

Los documentos vencidos se derivan de la fecha de vencimiento sin destruir el estado de revisión almacenado. `documentos_por_vencer()` permite construir alertas internas futuras.

## Versiones y revisión

Un reemplazo crea otra fila y referencia `reemplaza_a`; el archivo anterior no se modifica ni elimina. Propietario, director, administrador y secretaría pueden cargar, aprobar, rechazar o marcar no aplica. Padres pueden cargar y descargar únicamente tipos visibles en portal para alumnos vinculados. El alumno dispone inicialmente de consulta; docentes y contabilidad no tienen acceso administrativo.

## SaaS

El módulo se incorpora al catálogo oficial como `EXPEDIENTE`. La migración lo habilita para planes `PRO` y `EMPRESA`; continúa configurable desde el catálogo de planes. Al desplegar, ejecute migraciones y configure almacenamiento privado antes de habilitar documentos reales.
