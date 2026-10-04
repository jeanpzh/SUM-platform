# Document research summary — UNMSM / FISI academic RAG

Run date: 2026-09-29 · Method: **Playwright MCP** (browser navigation + in-page/API fetch) · Deliverables: `data/document_inventory.csv` (source of truth), `docs/document_dictionary.md`, `data/research_state.json`, `logs/research.log`.

## Totals

| Metric | Value |
|---|---|
| Inventory rows | **117** |
| Verified HTTP 200/206 | 114 |
| Broken (HTTP 404) | 3 |
| Excluded by policy | personal-data lists (`matriculados.htm`, `egresados.htm`, `resoluciones-decanales/`, `actas-de-consejo/`) and SUM login-required flows |
| Distinct hosts | 9 (all `*.unmsm.edu.pe`, `*.gob.pe`, `medicina.unmsm.edu.pe`) |
| Rows with a verified/extracted version id | 71 |
| Rows with a publication date | 17 (rest deliberately `UNKNOWN`) |

### By category
`matricula` 18 · `calendario_horarios_oferta` 15 · `reglamento_academico` 13 · `procedimientos_tramites` 12 · `organizacion_institucional` 11 · `retiros_reservas_reincorporacion` 8 · `evaluacion_calificacion` 8 · `plan_de_estudios` 7 · `formularios` 7 · `sum_sistema` 7 · `grados_titulos` 6 · `fisi_especifico` 4 · `prerrequisitos` **1**

### By status
`POSSIBLY_CURRENT` 59 · `CURRENT` 20 · `UNKNOWN` 18 · `SUPERSEDED` 9 · `HISTORICAL` 8 · `TEMPORARY` 3

### By priority
`HIGH` 39 · `LOW` 35 · `MEDIUM` 25 · `CRITICAL` 18

### By source
`sum.unmsm.edu.pe` 77 · `viceacademico.unmsm.edu.pe` 19 · `sistemas.unmsm.edu.pe` (FISI) 12 · `*.gob.pe` 4 · `www.unmsm.edu.pe` 2 · others 3

## Key findings

1. **Current vs. superseded matrícula regulation is explicit on SUM.** `reglamentomat.htm` embeds `assets/ReglamentoCompleto/reglamento2026.pdf` as the main document (via `PDFObject.embed`) and labels `reglamentoMatricula.pdf` as `ANTIGUO REGLAMENTO DE MATRÍCULA`, with an HTML comment `REGLAMENTO reemplado por reglamentoMatricula`. The approving resolution number is **not** present in the page text, so it stays `POSSIBLY_CURRENT` / `version=UNKNOWN` until the PDF itself is read.
2. **Four versions of the Reglamento de Matrícula are reachable** across sources — SUM `reglamento2026.pdf`, SUM `reglamentoMatricula.pdf`, viceacademico `2026/02/…` and `2025/03/…`, plus gob.pe RR `006376-2023`, `002891-2025`, `002642-2026`. They must be kept as separate rows and reconciled by reading the PDFs; do not collapse them.
3. **`prerrequisitos` coverage is 1 row** — the Guía del Estudiante de Pregrado 2026 (viceacademico, HTTP 200). This is the single highest-value ingestion target.
4. **The official Plan de Estudios links are broken.** `sum.unmsm.edu.pe/loginWebSum/planes.htm`, `planes2018.htm` → 404 (linked from SUM nav, `www.unmsm.edu.pe` students page and FISI); `sistemas.unmsm.edu.pe/sistemas/eap/plan2018` → 404 (the "Plan de estudios" anchor on the UNMSM career page). **No public, working plan/malla or prerrequisitos source was found.**
5. **FISI-specific high-value documents** all resolve: `Flujograma_de_Matricula_-_Reactualizacion_-_Reserva.pdf`, `Tramite_Grado_Academico_Bachiller_MAT_2.pdf`, `Tramite_Titulo_Profesional_MAT.pdf`, the 2026-II rectificación/extemporánea formatos (`.docx`), and the FISI copy of cronograma 2026.
6. **Reglamento General de Evaluación del Aprendizaje RR 007510-2021** is only reachable through other faculty sites (`medicina.unmsm.edu.pe`) and gob.pe — it is not in the SUM index.

## Gaps

| Gap | Evidence | Suggested next step |
|---|---|---|
| Plan de estudios / malla curricular (Ing. Sistemas) | 3 official links return 404 | Search faculty PDFs, `UNMSM` VRIP/plan registros, or capture from `Plan de estudios` registries (RR 013045-2021 / Directiva 001-2021 / Directiva 11 describe the registry process) |
| Prerrequisitos and límites de crédito as structured data | Only 1 row; content not yet read | Read `Guía-del-estudiante-de-pregrado-2026.pdf` first, then `reglamento2026.pdf` |
| SUM `pregrado.htm` "Requisitos" tabs | Present as text in page, no linked document | Capture full tab text (matrícula tradicional / vía internet) as page-derived record |
| Publication dates / approving resolutions | 100 rows still `UNKNOWN` date | Extract from PDF first pages (RR numbers carry the year) in the verify pass |
| FISI `resoluciones-decanales` and `actas` | Excluded by policy (personal data) | Keep excluded; index only the index page titles if needed |

## Broken links (recorded, not silently dropped)

- `https://sum.unmsm.edu.pe/loginWebSum/planes.htm` — 404 (linked from SUM nav, www.unmsm, FISI)
- `https://sum.unmsm.edu.pe/loginWebSum/planes2018.htm` — 404 (linked from SUM nav)
- `https://sistemas.unmsm.edu.pe/sistemas/eap/plan2018` — 404 (linked as "Plan de estudios" from the UNMSM career page)
- `fisi.unmsm.edu.pe` / `www.fisi.unmsm.edu.pe` — DNS NXDOMAIN; the faculty lives at `sistemas.unmsm.edu.pe`

## Duplicates / conflicts to reconcile at ingestion

- Reglamento de Matrícula: SUM `reglamento2026.pdf` vs SUM `reglamentoMatricula.pdf` vs viceacademico `2026/02` vs viceacademico `2025/03` vs gob.pe RR 006376-2023 / 002891-2025 / 002642-2026 → **7 candidate copies of one instrument**.
- Reglamento General de Grados y Títulos: viceacademico `2022/03` vs `2021/12` (same index, older copy kept as `SUPERSEDED`).
- Ley 30220: SUM `Ley_Universitaria_30220.PDF` vs viceacademico `2017/08/Ley-universitaria-30220.pdf`.
- Cronograma 2026 RR-014408-2025-R: SUM copy, viceacademico `2025/12/CRONOGRAMA-DE-ACTIVIDADE-2026.pdf`, and FISI copy (3 hosts, same resolution).
- RGAD: SUM `RR_01042_20t` + `014104-2022-R` + `012530-2023-R` vs viceacademico `2026/02/Reglamento-General-para-la-Actividad-Académica-Docente.pdf`.

## Tooling limitations encountered (record for future runs)

- `playwright_browser_navigate` fails with `TypeError: Cannot read properties of undefined (reading 'url')` — **use `playwright_browser_run_code_unsafe`** (`async (page) => …`).
- Page/context closes between or during calls (`Target page…closed`, `Detached while handling command`); do goto + extraction in a single code block, `waitUntil: 'commit'` for slow hosts, and `about:blank` between navigations.
- TLS chains are not trusted by the API-request context for `sistemas.unmsm.edu.pe`, `viceacademico.unmsm.edu.pe`, `sgd.unmsm.edu.pe` → navigate with the browser (or in-page `fetch(…, {method:'HEAD'})`); `sum.unmsm.edu.pe`, `www.unmsm.edu.pe`, `gob.pe` work through `context.request`.
- `browser.newContext()` is rejected (`Not allowed`).
- `.docx` navigation raises `Download is starting` and kills the page — record these URLs, do not loop on them.
- All research was done through Playwright MCP; the standalone pipeline that used to live in `scripts/research/` has been removed (unused). Stats are re-derivable from `data/document_inventory.csv`; the human-readable index is `docs/document_dictionary.md`.

## Suggested next steps

1. Read `Guía-del-estudiante-de-pregrado-2026.pdf` and `reglamento2026.pdf` to fill prerrequisitos, créditos and límites de carga, and to assign the real approving RR numbers/dates to the `UNKNOWN` rows.
2. Resolve the plan-de-estudios gap (broken official links) before any ingestion pass that promises curriculum coverage.
3. Run a reconciliation pass over the 7 Reglamento de Matrícula candidates and mark exactly one `CURRENT`.
4. Regenerate `docs/document_dictionary.md` from the CSV after every inventory change.
5. Manually review ≥20 CSV rows (spot-check status/priority/notes) before trusting the inventory.
