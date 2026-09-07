# Admisiones

## Configuración y formulario público

`ConfiguracionAdmision` controla si la institución recibe solicitudes públicas, el ciclo sugerido, obligatoriedad del CUI, carga documental y la política de documentos completos. El formulario público se abre por código institucional, valida todos los identificadores contra el tenant, usa CSRF, honeypot y límite básico por IP.

Cada solicitud recibe un correlativo institucional `ADM-AÑO-00001` y un UUID no enumerable para consultar un estado público simplificado y cargar documentos. Los nombres físicos de archivos son UUID, las extensiones se restringen a PDF/imágenes y el tamaño máximo es 10 MB.

## Flujo

Los estados cubren recepción, revisión, documentación, entrevista, evaluación, decisión, aprobación, lista de espera, rechazo, inscripción y cancelación. Entrevistas y evaluaciones son evidencia para una decisión humana; sus recomendaciones o puntuaciones nunca aprueban automáticamente.

## Conversión

`convertir_solicitud_a_alumno()` es atómico. Solo acepta solicitudes aprobadas, valida sección y cupo SaaS, reutiliza alumno por CUI y encargado por DPI/correo, crea o reutiliza familia, vincula encargado, crea una inscripción anual y copia documentos aprobados a tipos compatibles del expediente digital. Finalmente marca aspirante y solicitud como inscritos. No genera cargos financieros automáticamente; Finanzas puede hacerlo posteriormente.

## Permisos y seguridad

Propietario, dirección, administración y secretaría operan el panel. Docentes, contabilidad, padres y alumnos no acceden al panel administrativo. Las vistas internas filtran por `request.institucion`; el portal público no presenta observaciones ni motivos internos de rechazo.
