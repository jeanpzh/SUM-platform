# SUM · Administración de documentos

Dashboard responsive basado en [DESIGN.md](../DESIGN.md): React 19, TanStack Start, Tailwind 4, shadcn, Zustand, React Hook Form y Zod.

## Ejecutar

Las dependencias están en `pnpm-lock.yaml`. Desde `UI`:

```sh
pnpm dev
```

El backend debe estar disponible en `http://127.0.0.1:8000`. Para cambiarlo, configura `BACKEND_API_URL` en el entorno del servidor de UI. Esta variable no usa el prefijo `VITE_`.

La conexión es automática. El servidor de UI usa `BACKEND_ADMIN_TOKEN` o `API_ADMIN_TOKEN`; la configuración local carga la credencial desde el `.env` de la raíz. No se envía al navegador. No hay que pulsar un botón de conexión. El historial se recupera de PostgreSQL al recargar.

## Vistas y alcance

| Ruta              | Función                                              | Datos                      |
| ----------------- | ---------------------------------------------------- | -------------------------- |
| `/`               | Selección múltiple de PDF, metadatos de lote y carga | Backend real               |
| `/admin/jobs`     | Etapas, contadores, cancelación y nueva versión      | Backend real               |
| `/admin/library`  | Documentos publicados, fragmentos y reindexación     | Backend real               |
| `/admin/search`   | Exploración léxica de fragmentos                     | Muestra local              |
| `/admin/chat`     | Vista de respuestas y citas de ejemplo               | Muestra local              |
| `/admin/settings` | Preferencias locales y perfil de embeddings          | Perfil guardado en backend |

La recuperación con IA queda fuera de las pruebas de ingesta.

## Ingesta

- Adjunta hasta 50 PDF por lote, acumulando selecciones o arrastrando archivos. El límite del cliente es 32 MB por archivo, alineado con el valor predeterminado `MAX_UPLOAD_BYTES` del backend; el servidor aplica su propio límite configurado.
- Cada PDF tiene título, validación, porcentaje de transferencia y trabajo independientes. Hay hasta tres cargas simultáneas.
- Los metadatos de lote usan los campos del contrato actual: título, tipo, prioridad, URL de fuente y código opcionales. Cada solicitud multipart envía un PDF.
- Una respuesta 202 confirma aceptación, no publicación. La UI consulta cada dos segundos los trabajos activos y muestra seis etapas y los contadores reportados; no inventa un porcentaje global.
- Un reintento después de una respuesta perdida conserva archivo, metadatos y `Idempotency-Key` durante la sesión.
- Un trabajo fallido o cancelado se reintenta mediante `POST /v1/documents/{id}/versions`. Tras recargar, hay que adjuntar el original nuevamente. La versión publicada anterior se conserva.
- «Trabajos» y «Trabajos recientes» consultan `GET /v1/indexing-jobs`, con filtros, contadores y paginación. La biblioteca consulta `GET /v1/documents` y los fragmentos publicados; se actualiza después de publicar y al volver a la pestaña.
- Cada intento de etapa registra inicio/fin UTC, resultado y duración obtenida con un reloj monotónico del indexador. Se conservan reintentos; una ejecución interrumpida no inventa una duración. Los trabajos anteriores a esta implementación pueden no tener mediciones.

## Reindexación y desarrollo

En Configuración puedes guardar proveedor (`tei`, `ollama`, `openai`), modelo, revisión y límite de tokens. El índice actual requiere 768 dimensiones. El perfil se conserva por versión: cambiarlo afecta a nuevos trabajos y no dispara reindexaciones automáticamente.

«Reindexar pendientes» envía hasta 100 documentos con un perfil publicado diferente al actual. La biblioteca también permite reindexar un documento reutilizando su PDF original. Ambas acciones funcionan en producción y conservan la versión publicada hasta completar la nueva.

`ENV_MODE=DEVELOPMENT` en el backend habilita «Eliminar registro de prueba» en Biblioteca y Trabajos, también para registros existentes. Confirma el título exacto; no se permite borrar durante una indexación activa. Se eliminan versiones, historial, fragmentos y vectores en una transacción. El borrado de originales y artefactos se registra para reintentar la limpieza si falla el almacenamiento. En `PRODUCTION` el backend rechaza el borrado y la UI oculta los controles; el modo predeterminado es producción.

Para cambiar únicamente el modo, edita `.env` a `ENV_MODE=PRODUCTION` y ejecuta desde la raíz `docker compose up -d --no-deps --no-build --force-recreate backend`. No reconstruye la imagen ni reinicia PostgreSQL. `docker compose restart` no actualiza las variables del contenedor. El cambio de `ENV_MODE` controla estas funciones de administración; el Compose local conserva su configuración Inngest de desarrollo.

Para Ollama configura `OLLAMA_URL` e instala un modelo de 768 dimensiones; usa su nombre/tag, por ejemplo `nomic-embed-text:latest`, y revisión `auto` para fijar el digest detectado. Para OpenAI configura `OPENAI_API_KEY` en el entorno del indexador y selecciona `text-embedding-3-small` o `text-embedding-3-large`. Reinicia el indexador después de cambiar estas variables del servidor. Las claves nunca se introducen en el formulario. Consulta [la documentación del indexador](../docs/indexer-service.md) para migraciones y tokenización.

## Organización

Los componentes presentan las vistas. Los hooks gestionan selección, formularios, carga, conexión y seguimiento. `src/stores/admin-workspace-store.ts` crea un store Zustand por proveedor, evitando compartir estado entre solicitudes SSR. El reducer puro evita que una consulta antigua sobrescriba una cancelación más reciente.

`src/routes/api.indexing.$.ts` y `src/lib/pdf-ingestion/backend-proxy.server.ts` implementan un proxy de rutas permitidas con streaming multipart. La credencial permanece en el servidor. Credenciales y archivos originales no se serializan en `localStorage`.

## Pruebas

Requieren Node 24 para las pruebas unitarias con TypeScript nativo. Playwright ya está añadido como dependencia de desarrollo. Si falta su navegador:

```sh
pnpm exec playwright install chromium
```

Desde la raíz del repositorio, arranca el backend y sus dependencias con la configuración existente:

```sh
docker compose up -d --build
```

Después, desde `UI`:

```sh
pnpm test:unit
pnpm test:e2e
```

La configuración E2E usa `E2E_ADMIN_TOKEN` del entorno o lee exclusivamente `API_ADMIN_TOKEN` de `../.env`. No incorpora secretos al código ni activa trazas de red. Arranca Vite en el puerto 3017 y ejecuta Chromium en escritorio y Pixel 7 emulado.

Las pruebas usan `sources/originals/Directiva-SUM-006-rectificacion.pdf` y `RR-000046-2026-R-UNMSM.pdf`. Cubren selección múltiple, duplicados, archivos inválidos, eliminación, autenticación, tema, publicación completa de dos trabajos, cancelación, nueva versión e idempotencia tras perder la confirmación. **Crean documentos y versiones reales en el backend configurado**; usa un entorno de desarrollo para ejecutarlas.

El reporte queda en `playwright-report/`. Las capturas de fallos quedan en `test-results/`. [design-qa.md](design-qa.md) registra la revisión con Playwright MCP.

## Limitaciones del starter

Las rutas `/demo` se conservan fuera del alcance de ingesta. El build de producción y el chequeo global de TypeScript tienen incompatibilidades preexistentes en esas demos, entre ellas TanStack Table v9 con APIs v8. La UI de ingesta se valida con el servidor Vite y las pruebas anteriores.
