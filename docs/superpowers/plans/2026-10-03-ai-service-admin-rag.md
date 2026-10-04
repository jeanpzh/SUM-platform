# Admin AI Service and Agentic RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar el AI Service administrativo completo, conectado al corpus publicado y al panel, con proveedores intercambiables, auditoría durable y métricas RAG verificables.

**Architecture:** Backend API conserva identidad, ejecuciones, outbox, eventos y métricas; Inngest invoca AI Service con un `run_id`; AI Service lee `institutional.published_chunks`, aplica cuotas Redis y usa dos agentes LangChain acotados. UI autentica al administrador y consume estado/SSE mediante su proxy de servidor.

**Tech Stack:** Python 3.12, FastAPI, PostgreSQL/pgvector, Inngest Python, LangChain, redis-py, React, TanStack Start, Better Auth, Zod, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-03-ai-service-admin-rag-design.md`

## Global Constraints

- Solo flujo administrativo; SUM Gateway, datos privados de estudiantes e interfaz estudiantil quedan fuera.
- Usar generaciones publicadas y la cuenta `sum_retrieval` de solo lectura; nunca importar repositorios de otro servicio.
- Proveedores permitidos: Ollama, OpenAI API (incluidos modelos Codex disponibles por API), Anthropic y Google; secretos solo en servidor.
- Pregunta de 3–2000 caracteres; máximo 20 UUID de documentos; `top_k` entre 1 y 10.
- Por ejecución: máximo 5 llamadas al modelo, 6 herramientas, 2 rondas, 8 fragmentos, 8 000 tokens de entrada estimados, 1 000 de salida y 120 s.
- Por dependencia: SQL 3 s, embeddings 10 s, modelo 30 s, callback 5 s; un reintento transitorio dentro del plazo global.
- Cuotas iniciales compartidas: 10 consultas/minuto por admin, 30 llamadas/minuto y 4 simultáneas por proveedor; `429` lleva `Retry-After`.
- Retención inicial: ejecuciones/respuestas/evidencia 30 días y agregados sin pregunta 90 días.
- `UI/AGENTS.md`: se ejecutó `pnpm exec intent list`; `@tanstack/intent` falta. Informar su ausencia y no descargar sustituto.
- La raíz de `SUM` no tiene `.git`; los pasos de commit se ejecutan solo si el trabajo pasa a un checkout Git. No inicializar Git por cuenta propia.

## Review Focus

1. `provider` o `model` desconocido: `422`, sin invocar un modelo. Prueba en Task 3.
2. Mismo `Idempotency-Key` con cuerpo distinto: `409`, sin segunda ejecución ni outbox. Prueba en Task 1.
3. Cambio de publicación entre búsquedas: `CORPUS_CHANGED`, sin mezclar versiones. Prueba en Task 4.
4. Redis indisponible: fallo cerrado antes de una llamada de pago. Prueba en Task 5.
5. Citas inexistentes o fuera del alcance: abstención segura y evento auditado. Prueba en Task 6.

## File map

| Unidad | Archivos principales y responsabilidad |
|---|---|
| Contratos/estado | `packages/contracts/src/sum_contracts/ai.py`; `infra/postgres/006_ai_runs.sql`; `services/backend-api/src/sum_backend/ai_repository.py` |
| API/identidad | `services/backend-api/src/sum_backend/ai_routes.py`, `ai_security.py`, `app.py`, `config.py`; `UI/src/lib/auth.ts`, `UI/src/lib/ai/admin-auth.server.ts`, `UI/src/lib/ai/proxy.server.ts` |
| Servicio | `services/ai-service/src/sum_ai/{app,config,models,retrieval,embeddings,quota,tools,runner,workflow,reporter}.py` |
| UI | `UI/src/lib/ai/client.ts`, `UI/src/hooks/use-ai-chat.ts`, `UI/src/components/admin/{chat-view,chat-turn,metrics-view}.tsx`, rutas admin/API |
| Métricas | `services/backend-api/src/sum_backend/ai_metrics.py`; `services/ai-service/src/sum_ai/evaluation.py`; `data/ai-evaluation/*.json` |
| Despliegue | `services/ai-service/pyproject.toml`, `infra/Dockerfile.ai`, `compose.yaml`, `.env.example`, `pyproject.toml`, `docs/ai-service.md` |

---

### Task 1: Contratos y registro durable de ejecuciones

**Files:** Create `packages/contracts/src/sum_contracts/ai.py`, `infra/postgres/006_ai_runs.sql`, `services/backend-api/src/sum_backend/ai_repository.py`, `tests/test_ai_repository.py`; modify `packages/contracts/pyproject.toml`, `services/backend-api/src/sum_backend/outbox.py` only if the existing dispatcher needs a generic claim.

**Interfaces:** Produce `CreateRunRequest`, `RunContext`, `AuditEvent`, `RunResult` (Pydantic); `AI_RUN_REQUESTED = "ai/admin.run.requested"`; `AiRunRepository.create(owner: str, key: str, request: CreateRunRequest) -> tuple[dict, bool]`, `get(run_id: str, owner: str) -> dict`, `context(run_id: str) -> RunContext`, `apply_event(run_id: str, event: AuditEvent) -> dict`, `events(run_id: str, after: int, owner: str) -> list[dict]`, `cancel(run_id: str, owner: str) -> dict`. Task 7 consumes these contracts.

- [ ] Write tests for identical idempotent replay, changed-body `409`, owner-scoped read, duplicate `operation_id`, terminal-state rejection, and atomic run plus outbox insertion. Use the existing `tests/support.py` style and one PostgreSQL integration fixture for transaction claims.
- [ ] Run `uv run pytest tests/test_ai_repository.py -q`; expect failures because the contracts/repository do not exist.
- [ ] Add Pydantic to `sum-contracts`, models with bounded fields and forbidden extras, and migration tables `ai_runs`, `ai_events`, `ai_artifacts`, `ai_usage`; extend `application.outbox` with nullable `run_id`, nullable `job_id`, and a check that exactly one is present. Index owner/status/time and `(run_id, operation_id)`; grant backend role only.
- [ ] Implement `AiRunRepository` with one transaction for run/outbox creation and one transaction for each event/terminal result. Keep outbox payload to contract version and `run_id`.
- [ ] Run `uv run pytest tests/test_ai_repository.py -q`; expect pass. Commit the task files if a root Git checkout exists; otherwise record the missing checkout.

### Task 2: Sesión administrativa y proxy seguro

**Files:** Modify `UI/src/lib/auth.ts`, `UI/src/routes/admin.tsx`, `UI/package.json`, `UI/pnpm-lock.yaml`, `services/backend-api/src/sum_backend/config.py`, `infra/postgres/002_logins.sh`, `compose.yaml`, `.env.example`; create `UI/src/routes/login.tsx`, `UI/src/lib/ai/admin-auth.server.ts`, `UI/src/lib/ai/proxy.server.ts`, `UI/src/routes/api.ai.$.ts`, `services/backend-api/src/sum_backend/ai_security.py`, `UI/tests/unit/ai-proxy.test.mjs`, `tests/test_ai_security.py`, `infra/postgres/007_admin_auth.sql` generado desde la configuración Better Auth y revisado antes de aplicarlo.

**Interfaces:** `requireAdmin(request: Request): Promise<{ id: string; email: string }>` verifica sesión y allowlist; `proxyAi(request: Request, path: string): Promise<Response>` valida ruta/método/origen, firma `{sub,role,exp,method,path,body_sha256}` y reenvía al backend; `verify_admin_assertion(value: str, method: str, path: str, body_digest: str, secret: str) -> str` devuelve `sub`. Task 7 usa el proxy y Task 3 no recibe credenciales de navegador.

- [ ] Write tests: sin sesión `401` sin fetch; origen cruzado `403`; email no permitido `403`; firma vencida o cuerpo cambiado `401`; admin autorizado reenvía una sola vez.
- [ ] Run `cd UI && node --import ./tests/unit/register.mjs --test tests/unit/ai-proxy.test.mjs` and `uv run pytest tests/test_ai_security.py -q`; expect failures.
- [ ] Configurar Better Auth con PostgreSQL persistente y rol SQL `sum_auth` limitado a tablas de autenticación, `emailAndPassword.disableSignUp: true`, plugin admin, secreto obligatorio y bootstrap mediante CLI `auth create-admin` instalado como dependencia fija. Exponer PostgreSQL solo en loopback para el servidor UI local. `beforeLoad` de `/admin` usa función de servidor para redirigir a `/login`; cada ruta API comprueba sesión por sí misma. El backend valida afirmación HMAC corta y token de servidor; no confía en `X-Admin-Identity` libre.
- [ ] Run the two focused suites and `cd UI && pnpm build`; expect pass. Commit if Git exists.

### Task 3: Esqueleto del AI Service y catálogo de modelos

**Files:** Create `services/ai-service/pyproject.toml`, `services/ai-service/src/sum_ai/{__init__,config,models,app}.py`, `tests/test_ai_models.py`; modify root `pyproject.toml` and `uv.lock`.

**Interfaces:** `AiSettings.from_env() -> AiSettings` valida URLs, tokens, límites y proveedores; `ModelRegistry.from_settings(settings: AiSettings) -> ModelRegistry`; `.list_available() -> list[ModelChoice]`; `.resolve(provider: str, model: str) -> BaseChatModel` solo acepta allowlist y modelos con herramientas/salida estructurada. `create_app(settings: AiSettings | None = None, ...) -> FastAPI` expone `/health` e `/internal/models` autenticado.

- [ ] Write tests for four providers configured, missing key marked unavailable, model desconocido `422`, modelo sin tool calling rejected, price table with effective date, and no secret in catalog/exception.
- [ ] Run `uv run pytest tests/test_ai_models.py -q`; expect failures.
- [ ] Add LangChain and its provider integrations, FastAPI, redis-py and Inngest dependencies to the AI workspace member. Build provider adapters through `init_chat_model`/supported integrations with `timeout=30`, `max_retries=0`, a dated price table and a server config allowlist; never accept arbitrary base URLs from a request.
- [ ] Run focused tests and `uv run ruff check services/ai-service`; expect pass. Commit if Git exists.

### Task 4: Recuperación publicada y compatibilidad vectorial

**Files:** Create `services/ai-service/src/sum_ai/{embeddings,retrieval}.py`, `tests/test_ai_retrieval.py`, `tests/integration/test_ai_published_retrieval.py`; modify `infra/postgres/006_ai_runs.sql` for required dimension indexes/permissions.

**Interfaces:** `async QueryEmbedder.embed(question: str, profile: EmbeddingProfile) -> list[float]`; `async PublishedRetriever.retrieve(question: str, document_ids: tuple[str,...], top_k: int) -> RetrievalBatch`; `async more(run: RunContext, query: str, top_k: int) -> RetrievalBatch`; `async context(run: RunContext, chunk_id: str, radius: int) -> list[Evidence]`. `RetrievalBatch` includes evidence and pinned `{document_id:generation_id}` map.

- [ ] Write tests for query prefix/revision/dimension, read-only published view, two-profile rank fusion, bounded context, unsupported profile, parameterized document filters, and `CORPUS_CHANGED` after publication pointer changes.
- [ ] Run `uv run pytest tests/test_ai_retrieval.py -q`; expect failures.
- [ ] Implement TEI/Ollama/OpenAI query embedding adapters compatible with `EmbeddingProfile`, one query vector per present profile, rank fusion, hash-keyed short cache and current-generation checks before every follow-up. Use `sum_retrieval` and a 3 s DB statement timeout; configure indexes for admitted dimensions.
- [ ] Run unit tests now; run the published-corpus integration test through the `ai-test` Compose profile added in Task 8. Commit if Git exists.

### Task 5: Cuotas distribuidas y presupuesto

**Files:** Create `services/ai-service/src/sum_ai/quota.py`, `tests/test_ai_quota.py`; modify `services/ai-service/src/sum_ai/config.py`, `compose.yaml` para añadir Redis antes de la prueba distribuida.

**Interfaces:** `async QuotaManager.reserve(actor_id: str, provider: str, model: str, estimated_tokens: int) -> Reservation`, `async settle(reservation: Reservation, used_tokens: int) -> None`, `async release(reservation: Reservation) -> None`; reservation includes id, expiry and remaining per-run budget. Task 6 calls these methods for every model call.

- [ ] Write tests with two QuotaManager instances sharing Redis: 10 admin requests/minute, 30 provider model calls/minute, four in flight, token reservation/refund, TTL recovery after crash, `Retry-After`, and Redis failure before model invocation.
- [ ] Run `uv run pytest tests/test_ai_quota.py -q`; expect failures.
- [ ] Implement atomic Redis scripts for request/token buckets and leased concurrency; add a Redis service to Compose and fail closed when it cannot confirm a reservation. Count actual usage once by reservation ID.
- [ ] Run focused tests and Ruff; expect pass. Commit if Git exists.

### Task 6: Dos agentes LangChain, herramientas y respuesta verificable

**Files:** Create `services/ai-service/src/sum_ai/{tools,runner}.py`, `tests/test_ai_runner.py`; modify `services/ai-service/src/sum_ai/models.py`.

**Interfaces:** `build_research_tools(retriever: PublishedRetriever, run: RunContext) -> list[BaseTool]` permite solo búsqueda, contexto adyacente y metadatos publicados; `AgentRunner(registry: ModelRegistry, retriever: PublishedRetriever, quota: QuotaManager, limits: AgentLimits)` y `async run(run: RunContext, recorder: AuditRecorder) -> RunResult`; `validate_answer(answer: StructuredAnswer, evidence: list[Evidence]) -> RunResult`. `async AuditRecorder.record(event: AuditEvent) -> None` se implementa en Task 7.

- [ ] Write tests with fake tool-calling models: mandatory retrieval before model, model chooses one optional tool, no evidence skips model, invalid citation or extra document yields abstention, prompt-injection text cannot add tools, five-call/six-tool limits, one transient retry and overall timeout.
- [ ] Run `uv run pytest tests/test_ai_runner.py -q`; expect failures.
- [ ] Build `ResearchAgent` with `create_agent`, named tools and LangChain call-limit middleware; build `AnswerAgent` with Pydantic structured output and no tools. Validate citations independently; allow one repair call; record observable tool requests/results, token usage and dated estimated cost without model reasoning text.
- [ ] Run focused tests and Ruff; expect pass. Commit if Git exists.

### Task 7: Backend API, callbacks, Inngest y SSE

**Files:** Create `services/backend-api/src/sum_backend/{ai_client,ai_routes}.py`, `services/ai-service/src/sum_ai/{reporter,workflow}.py`, `tests/test_ai_api.py`, `tests/test_ai_workflow.py`; modify `services/backend-api/src/sum_backend/{app,config}.py`, `services/ai-service/src/sum_ai/app.py`, `services/backend-api/src/sum_backend/outbox.py`.

**Interfaces:** `AiServiceClient.list_models() -> list[ModelChoice]` calls the internal catalog with a 5 s timeout; `create_ai_router(repository: AiRunRepository, settings: Settings, ai_client: AiServiceClient) -> APIRouter` serves the spec's `/v1/admin/ai/*`; `create_app` gains optional `ai_repository`/`ai_client` injections so existing fake-repository tests remain isolated; `async HttpAuditRecorder.record(event: AuditEvent) -> None` posts internally with 5 s timeout; `register(client: inngest.Inngest, runner: AgentRunner) -> list` handles `AI_RUN_REQUESTED` with `run_id` only. Task 9 consumes run/SSE endpoints.

- [ ] Write HTTP/workflow tests for invalid input `422`, idempotent `202`, replay SSE from sequence, cancel during tool step, duplicated callback, callback after terminal state, failed provider safe code, and outbox event containing only IDs.
- [ ] Run `uv run pytest tests/test_ai_api.py tests/test_ai_workflow.py -q`; expect failures.
- [ ] Add backend router and internal context/callback endpoints; attach AI repository without changing existing indexing semantics. Register an Inngest function with bounded retries and idempotent phase IDs; store private artifacts in Backend API before publishing terminal event.
- [ ] Run focused tests and `uv run pytest tests/test_api.py -q`; expect pass. Commit if Git exists.

### Task 8: Despliegue y recorrido de servicio

**Files:** Create `infra/Dockerfile.ai`, `infra/inngest-dev.yaml`, `docs/ai-service.md`; modify `compose.yaml`, `.env.example`, `README.md`; create `tests/integration/test_ai_stack.py` and an `ai-test` Compose profile with test dependencies and repository tests mounted read-only.

**Interfaces:** Compose services `ai` and `redis`; `ai` uses `sum_retrieval` DB URL and internal Backend URL/token. Inngest registers both indexer and AI host. Health/readiness includes database, Redis and model catalog status without exposing secrets.

- [ ] Write integration test: create a published fixture, select a fake/local model, submit admin run through Backend API, follow SSE, assert cited result and audit; assert AI DB role cannot read staged chunks or mutate publications.
- [ ] Run `uv run pytest tests/integration/test_ai_stack.py -q`; expect failure before wiring.
- [ ] Add image, service configuration, role grants, migration path for existing PostgreSQL volumes, Inngest dev config with both SDK URLs, Redis health check and env documentation. Keep AI internal, with no public port mapping.
- [ ] Run `docker compose config`, start composed dependencies, then run `docker compose --profile test run --rm ai-test pytest tests/integration/test_ai_published_retrieval.py tests/integration/test_ai_stack.py -q`; expect pass. Commit if Git exists.

### Task 9: Admin chat con proveedor, evidencias y traza

**Files:** Create `UI/src/lib/ai/client.ts`, `UI/src/hooks/use-ai-chat.ts`, `UI/tests/unit/ai-client.test.mjs`, `UI/tests/e2e/ai-admin.spec.ts`; modify `UI/src/components/admin/{chat-view,chat-turn}.tsx`; optionally create focused `UI/src/components/admin/ai-source-citation.tsx` for backend evidence.

**Interfaces:** `fetchModels(signal?: AbortSignal): Promise<ModelChoice[]>`, `createRun(input: CreateRunRequest, key: string): Promise<Run>`, `watchRun(runId: string, after: number, onEvent: (event: AuditEvent) => void): () => void`; hook exposes selected provider/model, submit, status, answer, evidence, trace, usage and retry.

- [ ] Write client tests for parsed catalog, invalid response, SSE resume, cancellation, quota error and citation link; add one browser test of a full admin question against mocked API data.
- [ ] Run `cd UI && node --import ./tests/unit/register.mjs --test tests/unit/ai-client.test.mjs` and `cd UI && pnpm exec playwright test tests/e2e/ai-admin.spec.ts`; expect failures.
- [ ] Replace local `retrieveChunks` use only in admin chat, preserve local search if desired, add provider/model selector, run progress, answer, citation inspection, trace and safe empty/error states. Keep credentials server-side and all returned data schema-validated with Zod.
- [ ] Run focused tests and `cd UI && pnpm build`; expect pass. Commit if Git exists.

### Task 10: Evaluación etiquetada y métricas auditables

**Files:** Create `services/backend-api/src/sum_backend/ai_metrics.py`, `services/ai-service/src/sum_ai/evaluation.py`, `data/ai-evaluation/admin-rag-v1.json`, `tests/test_ai_metrics.py`, `tests/test_ai_evaluation.py`; modify `infra/postgres/006_ai_runs.sql`, `services/backend-api/src/sum_backend/ai_routes.py`, `services/backend-api/src/sum_backend/ai_repository.py` for retention purge.

**Interfaces:** `MetricsProjector.project(after_event_id: int, limit: int) -> int` upserts hourly buckets idempotently; `get_metrics(filters: MetricsFilters) -> MetricsResponse`; `evaluate(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> EvaluationScores` returns recall@k, precision@k, MRR. Evaluation requests enqueue low-priority runs with dataset/model version.

- [ ] Write tests for stage mean/count and p50/p95 buckets, no double-count on replay, filter by provider/model/generation, 1 relevant of 2 at rank 2 gives recall@4=0.5/precision@4=0.25/MRR=0.5, stale labels rejected, no-label metric shown unavailable, and 30/90-day purges preserving only aggregates.
- [ ] Run `uv run pytest tests/test_ai_metrics.py tests/test_ai_evaluation.py -q`; expect failures.
- [ ] Implement backend projector, hourly histograms, paged drilldown and idempotent retention purge; validate a versioned JSON golden set tied to the integration fixture at startup and execute evaluations through AI Service at lower priority under the same quotas. Production without a matching curated set reports no labeled evaluation.
- [ ] Run focused tests and Ruff; expect pass. Commit if Git exists.

### Task 11: Pestaña Métricas y cierre de documentación

**Files:** Create `UI/src/routes/admin.metrics.tsx`, `UI/src/components/admin/metrics-view.tsx`, `UI/src/lib/ai/metrics.ts`, `UI/tests/unit/ai-metrics.test.mjs`; modify `UI/src/components/pdf-dashboard/dashboard-shell.tsx`, `docs/ai-service.md`.

**Interfaces:** `fetchMetrics(filters: MetricsFilters, signal?: AbortSignal): Promise<MetricsResponse>`; charts render operation/timing/cost and labeled quality separately, with an equivalent data table and links to run details.

- [ ] Write tests for filters, empty evaluation state (“sin evaluación etiquetada”), average/p50/p95 labels, rate-limit counts, accessible table and drilldown link to a run.
- [ ] Run `cd UI && node --import ./tests/unit/register.mjs --test tests/unit/ai-metrics.test.mjs`; expect failures.
- [ ] Add `/admin/metrics` navigation, responsive charts and tables, evaluation trigger/status, and copy distinguishing real traffic from labeled evaluation. Document runbook, provider variables, retention, migrations and known provider availability in `docs/ai-service.md`.
- [ ] Run focused tests, `cd UI && pnpm build`, backend/AI focused suites and one integrated admin browser flow; expect pass. Commit if Git exists.

## Final verification

- [ ] Run Python unit/integration suites relevant to AI, `ruff check` on changed Python, UI unit tests/build and Compose integration once. Inspect failures and rerun only affected checks after fixes.
- [ ] Manually inspect one complete run: API result, SSE sequence, evidence/version IDs, audit trace, metric bucket and UI citation target all agree.
- [ ] Confirm secrets and raw model responses are absent from browser payloads, Inngest events and normal logs.
- [ ] Review the final changed-file inventory; report that Git commits/worktrees could not be used if the root still lacks `.git`.
