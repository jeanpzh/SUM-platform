# Decisiones de arquitectura

## Alcance acordado

- El caso de consulta de referencia es la desaprobación reiterada de un curso.
- Los documentos regulatorios compartidos se consultan mediante recuperación institucional.
- Los datos SUM saneados son un resultado del proceso de recopilación; el estudiante no debe prepararlos manualmente.
- Las instantáneas privadas se mantienen fuera del corpus vectorial compartido.

## Separación de servicios definida en el diseño

- Backend API, AI Service, Indexer Service y SUM Gateway pertenecen al sistema backend y se ejecutan como servicios independientes. Pueden compartir repositorio y máquina.
- Backend API es la entrada pública y administra consultas, trabajos, eventos y catálogo de fuentes. AI Service e Indexer Service reportan cambios mediante contratos internos autenticados.
- Indexer Service publica el corpus derivado; AI Service tiene acceso de lectura a versiones publicadas. La recuperación y las reglas viven dentro de AI Service.
- SUM Gateway administra conexiones del adaptador e instantáneas privadas, y entrega contexto autorizado mediante su contrato. Los demás servicios no escriben sus tablas.
- Una instancia PostgreSQL compartida mantiene esquemas y permisos por propietario. Inngest y la cola son infraestructura de ejecución, no servicios de negocio.
- La estructura y los contratos se detallan en [Separación de servicios](separacion-servicios.md). Backend API e Indexer Service tienen una implementación inicial y un Compose de desarrollo; AI Service y SUM Gateway siguen pendientes. Véase la [guía del indexador](indexer-service.md).

## Decisiones de implementación pendientes

- Mapeo real de campos SUM, una vez implementado el adaptador.
- Proveedor del modelo de lenguaje y registro ejecutable de reglas, una vez verificadas las reglas.
- Topología de alojamiento propio y versión de Inngest probada.
- Los límites propuestos de ejecución y los valores predeterminados de retención requieren confirmación antes de implementarse.

## Restricciones verificadas de los frameworks

- Inngest ejecuta los flujos invocando el endpoint SDK de la aplicación; las ejecuciones durables se repiten usando resultados de pasos guardados. Por eso, los eventos y resultados deben contener referencias, no datos estudiantiles, instrucciones ni respuestas personalizadas. [Ciclo de vida de ejecución de Inngest para Python](https://github.com/inngest/inngest-py/blob/main/pkg/inngest/docs/REQUEST_LIFECYCLE.md).
- FastAPI admite SSE y respuestas en transmisión; la transmisión asíncrona debe permitir la cancelación. Antes de elegir su respuesta SSE nativa o una implementación con StreamingResponse, hay que fijar una versión compatible. [Documentación de FastAPI sobre SSE](https://fastapi.tiangolo.com/tutorial/server-sent-events/).
- El almacenamiento de eventos en PostgreSQL, un outbox transaccional y las referencias a artefactos privados son propuestas de arquitectura de la aplicación; no son funciones automáticas del SDK de Inngest.
