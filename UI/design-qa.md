# QA de ingesta · 2026-10-03

## Evidencia de navegador

Se utilizó el servidor Playwright MCP configurado en Codex CLI para abrir Vite, adjuntar los dos PDF de `sources/originals`, inspeccionar la interfaz y capturarla. Las imágenes corresponden a la implementación:

- [Escritorio, 1440 × 1024](pdf-ingestion/qa/desktop.png): dos archivos seleccionados, títulos independientes y metadatos de lote.
- [Móvil, 390 × 844](pdf-ingestion/qa/mobile.png): selección y metadatos apilados; controles completos y sin desbordamiento horizontal.
- [Móvil oscuro](pdf-ingestion/qa/mobile-dark.png): selector de tema verificado con MCP, sin desbordamiento horizontal.
- Publicación real capturada por la suite E2E en [escritorio](pdf-ingestion/qa/jobs-desktop.png) y [móvil](pdf-ingestion/qa/jobs-mobile.png): dos páginas por documento, 18 y 33 fragmentos, y la misma cantidad de vectores.

Las capturas siguen la dirección de `DESIGN.md`: tipografía serif en títulos, sans-serif en controles, superficies cálidas y acciones terracota. El flujo de lote cambia la distribución respecto del concepto original `pdf-ingestion/mesa-de-ingesta.png`; no se afirma una coincidencia píxel a píxel.

## Hallazgos resueltos

- El selector de archivos y la conexión podían recibir acciones antes de hidratar React. Ahora los controles esperan la carga del estado.
- El selector de tema también espera la hidratación para que su primer clic abra el menú.
- El texto de cargas simultáneas quedaba demasiado estrecho junto al botón. El botón y su explicación ocupan filas completas.
- Cada PDF aceptado muestra su estado confirmado y un enlace a su proceso; la aceptación de la carga se distingue de publicación.
- La fragmentación real fallaba porque la caché del tokenizador pertenecía a `root`. Se corrigió el volumen existente y el Dockerfile; una prueba con volumen nuevo confirmó UID 10001 y escritura permitida.

## Verificación funcional

Las 10 pruebas E2E pasaron (2,6 minutos): Chromium en escritorio y Pixel 7 emulado contra el backend real. Usan los PDF originales y cubren selección múltiple, duplicados, contenido inválido, eliminación, credenciales, sesión en memoria, tema, dos publicaciones independientes, cancelación y nueva versión, y reintento idempotente tras perder la confirmación de carga. Comprueban también los contadores directamente en la API. La recuperación con IA queda fuera del alcance.

Pasaron las ocho pruebas unitarias de validación, tamaño, identidad de archivos, concurrencia, metadatos del contrato, mapeo de estados/contadores y la carrera entre consultas antiguas y cancelación. Las 27 pruebas Python del backend e indexador pasaron sin omisiones. El lint de los archivos del dashboard y de las pruebas no reportó errores; Prettier también pasó.

## Límites

La consola de la sesión MCP registró un 404 de `favicon.ico`; no se observaron excepciones de JavaScript en el flujo de publicación probado. No se realizó una auditoría WCAG completa ni pruebas con dispositivos físicos.

El build global y el chequeo TypeScript siguen bloqueados por incompatibilidades preexistentes en las demos del starter, especialmente `src/routes/demo/table.tsx` usando APIs v8 con TanStack Table v9. Los errores de TypeScript no señalan archivos nuevos de ingesta. El entorno de validación de UI es Vite en desarrollo.
