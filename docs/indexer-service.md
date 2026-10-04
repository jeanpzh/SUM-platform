# Indexer Service

Backend API e Indexer Service se despliegan por separado. Inngest coordina los pasos; PostgreSQL guarda estados y vectores; MinIO conserva originales y artefactos. `UI/` usa el backend para ingesta, seguimiento, biblioteca y administración del perfil de embeddings. AI Service y SUM Gateway quedan pendientes.

## Flujo y límites

```mermaid
flowchart LR
    C[Cliente: archivos en paralelo] --> B[Backend API]
    B --> S[Almacenamiento de originales]
    B --> D[Trabajo y outbox: transacción]
    D --> O[Despachador]
    O --> I[Inngest: IDs y prioridad]
    I --> X[Indexer Service]
    S --> X
    X --> P[Procesos: extracción y OCR]
    P --> T[Texto y fragmentos con páginas]
    T --> E[Servicio de embeddings]
    E --> V[pgvector: generación preparada]
    X --> B
    B --> A[Publicación y estado: transacción]
    V --> R[Vista de fragmentos publicados]
    A --> R
```

Cada solicitud contiene **un documento**. El cliente puede enviar varias solicitudes simultáneas; cada aceptación devuelve `202` y su propio trabajo. El backend verifica credenciales, formato, tamaño y metadatos; guarda el original y registra documento, versión, trabajo y outbox antes de responder. `202` confirma aceptación durable, no procesamiento terminado. Una repetición idempotente de un trabajo terminado devuelve `200`.

**Inngest recibe referencias, no PDFs ni texto.** El indexador obtiene el contexto mediante una ruta interna autenticada y descarga el original con sus credenciales de almacenamiento. Los pasos retornan IDs y estados; los artefactos grandes se guardan fuera del orquestador.

El despachador reintenta entregas del outbox. Los IDs estables, checkpoints y operaciones idempotentes toleran entregas repetidas. Se conservan los embeddings de lotes terminados para evitar recalcularlos tras un fallo. El perfil de modelo y la configuración quedan congelados por trabajo.

## Arranque local

Requiere Docker con Compose y acceso a los registros de imágenes, los módulos de Go y Hugging Face.

```sh
cp .env.example .env
docker compose up --build
```

Compose compila MinIO y `mc` desde versiones de código fuente fijadas mediante `infra/Dockerfile.storage`, porque [MinIO Community se distribuye solo como código fuente](https://github.com/minio/minio#source-only-distribution). `MINIO_VERSION` y `MINIO_CLIENT_VERSION` seleccionan las versiones; las antiguas variables `MINIO_IMAGE` y `MINIO_CLIENT_IMAGE` ya no se utilizan. Si aparece `pull access denied for minio/minio`, comprobar que se está usando el `compose.yaml` actualizado. Los errores de imágenes interrumpidas que siguen a ese fallo requieren reintentar el arranque, no iniciar sesión en MinIO.

El primer arranque compila el almacenamiento y descarga `intfloat/multilingual-e5-base` con una revisión inmutable compartida por TEI y el tokenizador. Puede tardar varios minutos; los módulos y la compilación de Go se almacenan en la caché de BuildKit para los siguientes arranques. El servicio de embeddings también puede tardar varios minutos en estar disponible.

La caché del tokenizador (`/tmp/huggingface`) debe pertenecer al usuario del indexador, UID/GID `10001`. El Dockerfile crea la carpeta con esos permisos antes de montar un volumen nuevo. Si un volumen creado anteriormente pertenece a `root` y la indexación falla en fragmentación, corrige sus permisos sin eliminar la caché:

```sh
docker compose exec --user root indexer chown 10001:10001 /tmp/huggingface
```

- Backend: `http://localhost:8000`; documentación REST: `/docs`.
- Inngest de desarrollo: `http://localhost:8288`.
- El indexador, PostgreSQL, MinIO y TEI quedan en la red interna de Compose.
- Los datos, originales y cachés de modelos usan volúmenes persistentes.

Los scripts SQL inicializan una base nueva. En una base existente, aplicar los cambios con una migración revisada; reiniciar el contenedor no vuelve a ejecutar los scripts de inicialización. Las contraseñas de ejemplo están pensadas para desarrollo y deben reemplazarse; usar valores compatibles con una URI PostgreSQL o codificarlos al configurar `DATABASE_URL`.

## Cargar documentos

Ejemplo de metadatos en `examples/indexing/metadata.json`. Para una prueba pequeña también existe `examples/indexing/documento.txt`, identificado como contenido sintético.

```sh
curl -i http://localhost:8000/v1/documents \
  -H 'Authorization: Bearer development-admin-token-change-before-use' \
  -H 'Idempotency-Key: documento-sintetico-001' \
  -F 'archivo=@examples/indexing/documento.txt;type=text/plain' \
  -F 'metadatos=<examples/indexing/metadata.json'
```

Para un PDF, sustituir `archivo` por `@ruta/documento.pdf;type=application/pdf`. Conservar la misma clave al reintentar exactamente la misma carga; usar una nueva para contenido o metadatos distintos. Reutilizar una clave con contenido diferente devuelve `409`.

La respuesta contiene `documento_id`, `version_id`, `trabajo_id`, `estado`, `mensaje` y `estado_url`. La cabecera `Location` señala el estado. Los mensajes públicos y estados están en español.

| Operación | Ruta |
|---|---|
| Registrar documento | `POST /v1/documents` |
| Cargar nueva versión | `POST /v1/documents/{documento_id}/versions` |
| Consultar trabajo | `GET /v1/indexing-jobs/{trabajo_id}` |
| Cancelar | `POST /v1/indexing-jobs/{trabajo_id}/cancel` |
| Seguir progreso SSE | `GET /v1/indexing-jobs/{trabajo_id}/events` |

Todas estas rutas requieren `Authorization: Bearer <API_ADMIN_TOKEN>`; las cargas requieren `Idempotency-Key`. SSE permite reconectar con `Last-Event-ID` y termina al llegar a un estado final. Al consumir SSE desde el navegador, usar un cliente que permita la cabecera de autorización; `EventSource` nativo no admite cabeceras arbitrarias.

```sh
curl http://localhost:8000/v1/indexing-jobs/TRABAJO_ID \
  -H 'Authorization: Bearer development-admin-token-change-before-use'

curl -N http://localhost:8000/v1/indexing-jobs/TRABAJO_ID/events \
  -H 'Authorization: Bearer development-admin-token-change-before-use'
```

Estados: `en_cola`, `procesando`, `completado`, `fallido`, `cancelado`. Etapas: `validando`, `extrayendo`, `fragmentando`, `generando_vectores`, `guardando`, `publicando`. Los contadores de páginas, fragmentos y vectores acompañan el progreso. El heartbeat informa actividad aunque no haya avanzado el contador.

### Metadatos

Requeridos: `titulo`, `tipo_documento`. Tipos: `plan_estudios`, `reglamento`, `resolucion`, `directiva`, `otro`. Prioridad: `alta`, `normal` o `baja`. La prioridad orienta la planificación de Inngest; no interrumpe un trabajo en ejecución ni garantiza un orden estricto de finalización.

Otros campos: `institucion`, `idioma` (`es` o `es-en`), `unidad_emisora`, `codigo_documento`, `fuente_url`, `facultad`, `carrera`, `version_curricular`, `fecha_emision`, `vigente_desde`, `vigente_hasta`, `periodos_aplicables` y `relaciones`. Las fechas usan `AAAA-MM-DD`. Los metadatos se preservan en la versión, los fragmentos y el manifiesto. La URL se conserva como procedencia; el indexador no la visita. Las relaciones son referencias declaradas, no reglas académicas verificadas.

## Extracción y embeddings

El registro de extractores usa un diccionario MIME → fábrica, detrás de una interfaz. Se admiten PDF, PNG, JPEG y TXT UTF-8. PDF usa PyMuPDF; páginas sin texto suficiente e imágenes utilizan OCR Tesseract español/inglés. La extracción produce texto `.txt` y estructura por página/bloque; los fragmentos conservan sus localizadores y metadatos.

Los planes de estudios tienen extracción de filas y encabezados de tablas. Un plan escaneado se rechaza con `CALIDAD_TABLA` cuando no se puede asegurar la alineación de celdas; requiere revisión o un extractor de tablas especializado. La indexación no certifica vigencia jurídica ni interpreta automáticamente prerrequisitos.

La fragmentación usa un tokenizador Hugging Face configurado con `EMBEDDING_TOKENIZER_MODEL` y `EMBEDDING_TOKENIZER_REVISION`, incluye el título y añade solapamiento. Por defecto usa el tokenizador E5. Si eliges otra familia, configura su tokenizador compatible en el indexador antes de procesar documentos. Los proveedores mantienen `truncate=false` cuando la API lo permite para rechazar entradas excesivas. E5 usa `passage: ` y `query: `; los adaptadores Ollama y OpenAI no añaden esos prefijos. Los vectores se verifican por cantidad, dimensión y valores finitos y se normalizan.

TEI, Ollama (`/api/embed`) y OpenAI (`/v1/embeddings`) tienen adaptadores. Ollama fija la revisión con el digest de `/api/tags`; OpenAI solicita 768 dimensiones a los modelos `text-embedding-3-*`, y su campo de revisión es una etiqueta de despliegue administrada por el operador. `OLLAMA_URL` y `OPENAI_API_KEY` se configuran solo en el servidor. Para otro formato, implementar `Extractor`, registrarlo y añadir su MIME a la entrada del backend. El índice HNSW actual está preparado para 768 dimensiones; otra dimensión exige migrar el índice SQL. La recuperación futura debe generar las consultas con el mismo perfil que los documentos.

## Administración persistente

| Operación | Ruta |
|---|---|
| Historial, contadores y filtros | `GET /v1/indexing-jobs?status=active&limit=25&offset=0` |
| Biblioteca publicada | `GET /v1/documents` |
| Fragmentos publicados | `GET /v1/documents/{id}/chunks` |
| Consultar/cambiar modelo | `GET` / `PATCH /v1/admin/embedding-profile` |
| Reindexar un documento | `POST /v1/documents/{id}/reindex` |
| Reindexar perfiles pendientes (máximo 100) | `POST /v1/admin/reindex-stale` |
| Eliminar registro de desarrollo | `DELETE /v1/documents/{id}` con `{"confirmar_titulo":"título exacto"}` |

El cambio de modelo se guarda en PostgreSQL y cada versión recibe una copia del perfil. Reindexar reutiliza el original, crea versión/trabajo/outbox y conserva la publicación anterior. Un documento con trabajo activo no se vuelve a encolar.

El borrado requiere `ENV_MODE=DEVELOPMENT`, propietario autorizado, título exacto y ausencia de trabajo activo. El modo por defecto es `PRODUCTION`. Las eliminaciones de almacenamiento se guardan transaccionalmente y se reintentan cada 30 segundos si fallan. La función SQL de limpieza de vectores solo es ejecutable por el rol del backend.

Los tiempos siguen el ciclo de un span: inicio, fin, resultado y número de intento. Los timestamps UTC sirven para auditoría; `perf_counter_ns()` mide la duración sin depender de ajustes del reloj del sistema. PostgreSQL conserva los intentos y los devuelve en `tiempos`. Para trabajos anteriores no se reconstruyen mediciones que nunca se registraron.

Para actualizar una base existente sin borrar datos, aplica las migraciones y reconstruye los servicios modificados:

```sh
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U sum -d sum < infra/postgres/003_stage_timings_and_library.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U sum -d sum < infra/postgres/004_admin_operations.sql
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U sum -d sum < infra/postgres/005_development_cleanup.sql
docker compose run --rm storage-init
docker compose up -d --build backend dispatcher indexer
```

## Concurrencia y escalabilidad

| Variable | Predeterminado | Alcance |
|---|---:|---|
| `CPU_PROCESSES` | 2 | Procesos de extracción por réplica del indexador |
| `EXTRACTION_CONCURRENCY` | 2 | Ejecuciones de extracción coordinadas por Inngest |
| `EMBEDDING_CONCURRENCY` | 2 | Ejecuciones de embeddings coordinadas por Inngest |
| `WRITING_CONCURRENCY` | 2 | Ejecuciones de escritura coordinadas por Inngest |
| `PAGE_BATCH_SIZE` | 10 | Páginas por checkpoint |
| `EMBEDDING_BATCH_SIZE` | 32 | Fragmentos por llamada de embeddings |
| `MAX_UPLOAD_BYTES` | 33554432 | Límite de cada archivo |
| `MAX_PENDING_JOBS` | 1000 | Trabajos pendientes por identidad administrativa |
| `MAX_PAGES` | 2000 | Límite de páginas por documento |
| `STAGE_TIMEOUT_SECONDS` | 900 | Tiempo máximo de una ejecución de etapa |

La extracción usa un pool acotado con `spawn`; los documentos y lotes se procesan sin crear un proceso por cada petición. Los threads sirven a operaciones de red/almacenamiento y los procesos ejecutan la extracción. La cancelación o el timeout de una operación CPU reinicia el pool de esa réplica; puede interrumpir otros lotes, que se recuperan mediante reintentos.

Se puede escalar el backend y el indexador independientemente detrás de direcciones estables. Registrar el host de Inngest contra el balanceador del indexador y conservar los mismos IDs de funciones/límites. Los límites de CPU son por réplica; ajustar concurrencia, memoria, conexiones PostgreSQL y capacidad de TEI conjuntamente. Compose ilustra una réplica local; el despliegue con balanceo queda a cargo de la infraestructura.

## Propiedad de datos y publicación

- Backend escribe `application`: documentos, versiones, trabajos, eventos, outbox y puntero del catálogo publicado.
- Indexer escribe `institutional`: generaciones, fragmentos, vectores y resultados pendientes de confirmación.
- La recuperación tiene lectura de `institutional.published_chunks`, que expone únicamente generaciones preparadas y autorizadas por el catálogo del backend.
- Las credenciales S3 del backend permiten guardar originales. Las del indexador permiten leer originales y administrar derivados.

El indexador valida que la generación esté completa antes de preparar el manifiesto. Backend verifica versión y cancelación y publica el puntero con el estado final en una transacción. Si un callback se pierde, un reconciliador vuelve a informar el resultado durable. La versión anterior sigue disponible durante una actualización y ante fallos; cancelar impide publicar el nuevo resultado.

Los dos servicios se comunican por contratos HTTP/eventos versionados y comparten únicamente contratos, almacenamiento de objetos y el adaptador SQLAlchemy Core. Cada servicio conserva sus propias consultas y credenciales; ninguno importa los repositorios o las rutas del otro. El adaptador administra `Engine`, pool, transacciones y parámetros JSONB. PostgreSQL y pgvector siguen siendo requisitos porque el esquema usa bloqueo advisory, `SKIP LOCKED`, JSONB y el tipo `vector`.

## Validación y pendientes de despliegue

```sh
uv sync --group dev
uv run python -m unittest discover -s tests -t . -v
uv run ruff check packages services tests
```

Las pruebas cubren contratos, metadatos, API con cargas simultáneas, errores en español, idempotencia, límites, SSE, credenciales separadas, adaptador HTTP de embeddings, multiprocessing real de TXT y recuperación/cancelación mediante dobles de almacenamiento vectorial y backend. No equivalen a una prueba de integración de PostgreSQL, OCR, modelos o Inngest reales.

La integración de ingesta se verifica además desde `UI` con Playwright y los PDF de `sources/originals`, usando el backend, PostgreSQL, almacenamiento, Inngest y TEI reales. Estas pruebas cubren publicación, cancelación y reintento como nueva versión; no cubren preguntas de recuperación con IA. Consulta [UI/README.md](../UI/README.md) para ejecutarlas. El arranque y la configuración de producción requieren su propia validación.

Antes de producción, configurar Inngest durable con firma (`INNGEST_SIGNING_KEY`, desactivar `INNGEST_DEV`), autenticación de usuarios, secretos y límites medidos. El Compose usa el servidor Inngest de desarrollo y sus ejecuciones no tienen persistencia configurada. La autenticación inicial usa una identidad administrativa con token estático, no un sistema multiusuario. Los artefactos huérfanos o cancelados necesitan una política de retención y limpieza; ante un resultado de commit incierto se conserva el original para evitar borrar una fuente aceptada.
