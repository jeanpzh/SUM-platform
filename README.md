# Investigación para un asistente académico de SUM

El [AI Service y la arquitectura integral administrativa](docs/ai-service.md) incluyen RAG agente con LangChain, proveedores intercambiables, auditoría durable y métricas en el dashboard. Consulta esa guía para migraciones, autenticación, arranque y verificación.

Este repositorio reúne documentos fuente e investigación de evidencia para un asistente académico propuesto para FISI / UNMSM. Incluye una interfaz en `UI/`, Backend API e Indexer Service como servicios independientes. La interfaz ingesta PDF, consulta el historial persistente y muestra la biblioteca publicada directamente desde el backend.

## Ejecutar la indexación

```sh
cp .env.example .env
docker compose up --build
```

El primer arranque compila MinIO y su cliente desde versiones de código fuente fijadas y descarga el modelo de embeddings; puede tardar varios minutos. API: `http://localhost:8000`; Inngest de desarrollo: `http://localhost:8288`. La configuración Compose es local y utiliza credenciales de ejemplo.

Consulta [Indexador: arranque, API y arquitectura](docs/indexer-service.md) para cargar archivos, consultar estados y configurar concurrencia. Los archivos permanecen en almacenamiento de objetos; Inngest recibe referencias a trabajos.

## Estructura

- `services/backend-api/`: API de documentos, estados, SSE y despacho transaccional.
- `services/indexer-service/`: extracción/OCR, fragmentación, embeddings y publicación.
- `services/ai-service/`: recuperación publicada, agentes, herramientas y cuotas distribuidas.
- `packages/`: contratos, almacenamiento de objetos y adaptador SQLAlchemy compartidos.
- `infra/` y `compose.yaml`: contenedores, PostgreSQL/pgvector y permisos de almacenamiento.
- `tests/`: pruebas de contratos, API y procesamiento.
- `data/`: inventarios de fuentes, registros auditados, relaciones y estado de investigación.
- `docs/`: informes de investigación y documentación de arquitectura.
- `docs/evidence/screenshots/`: capturas de navegador conservadas como evidencia visual.
- `scripts/`: utilidades de Python para adquirir y extraer fuentes, y regenerar resultados de auditoría.
- `sources/originals/`: documentos fuente descargados.
- `sources/extracted/`: texto extraído de los documentos, con referencias a páginas.
- `logs/`: registro de las sesiones de investigación.

## Scripts de mantenimiento

Ejecutar desde la raíz del repositorio:

```sh
python scripts/build_source_manifest.py
python scripts/preserve_pre_collection_values.py
python scripts/sync_audited_dictionary.py
```

`python scripts/build_repository_audit.py` genera la auditoría inicial a partir del inventario original. Los scripts de adquisición dependen de `data/` y `sources/` y pueden actualizar archivos CSV o Markdown generados; revisa sus cambios antes de confirmarlos.

## Estado del proyecto

Los resultados de investigación y las brechas de fuentes pendientes se resumen en el [informe de recopilación](docs/source_collection_report.md) y el [informe de auditoría](docs/repository_audit_report.md). La propuesta de arquitectura está en [ARQUITECTURA.md](ARQUITECTURA.md); la [separación de servicios](docs/separacion-servicios.md) define Backend API, AI Service, Indexer Service y SUM Gateway como procesos independientes del mismo sistema backend.
