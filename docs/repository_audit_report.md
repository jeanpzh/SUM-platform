# FISI repository audit before RAG ingestion — prior metadata snapshot

> **Superseded for acquisition status on 2026-09-29.** Source documents were subsequently downloaded and extracted. See the current [source collection report](source_collection_report.md), [FISI plan coverage matrix](fisi_plan_coverage_matrix.md), `sources/source_manifest.csv`, and `sources/extracted/`. This file is retained as the initial audit baseline; its “no local files” statements below describe that earlier snapshot only.

**Audit date:** 2026-09-30  
**Scope:** supplied UNMSM/FISI source inventory plus new verified FISI transition/equivalency sources.  
**Disposition:** **NOT COMPLETE — not ready for broad RAG ingestion.** This is metadata/evidence validation, not a legal opinion.

## Executive result

- Preserved all **117** original URL records and original inventory fields/values; appended audit fields and added three Playwright-verified records (**DOC-118–DOC-120**), for **120** total records in `data/document_inventory_audited.csv`.
- The original `corpus_action` is retained unchanged. New `ingestion_decision` uses only `INCLUDE`, `REVIEW_REQUIRED`, `DISCOVERY_ONLY`, and `EXCLUDE`. Applicability is a separate field using `established`, `uncertain`, `limited to a population`, or `historical`.
- **No downloaded PDF/DOCX files exist in the workspace.** Accordingly there are zero computable local file hashes and zero local extracted-text comparisons. Do not interpret the `NONE_CONFIRMED` duplicate label as evidence that URLs are unique; it means exact duplicate status is unknown.
- Playwright verified the official SUM Directivas index (HTTP 200), official SUM enrollment index (HTTP 200), FISI 2009-plan notice, Gob.pe RR 000046-2026 record (HTTP 200), and rendered the RR attachment (2 pages) for visual review.
- Key correction: RR 000046-2026-R's signed attachment expressly identifies **EP Ingeniería de Sistemas** (page 1) and contains a 2018/2023 equivalency table (page 2). The prior FISI-plan review's “covered EP UNKNOWN” is superseded by direct visual evidence. The table lists specific corrections, not blanket equivalence of every course or entire plans.
- Two critical unresolved evidence classes block intended retrieval: approved plan texts/course maps and cohort/transition rules (especially older-plan returners); and official graduation requirements by cohort. Local attachment extraction and table QA also remain pending.

## Playwright verification and source provenance

### SUM Directivas index

`https://sum.unmsm.edu.pe/directivas.htm` returned 200 through Playwright. Its body lists Directivas 1–15; descriptions include Directiva 5 reactualización, 6 rectificación, 7 convalidación, 8 equivalencia, 9 reserva, 10 matrícula extemporánea and 11 study-plan registration. It also lists RR 013045-2021-R, RR 2272-R-13 and RR 2810-R-13 as resolutions that approve SUM directives. This verifies the index labels and discovery links only; it does **not** prove each directive remains in force or the scope of its approval resolution. Those attachments remain separate records and require clause review.

### SUM enrollment index

`https://sum.unmsm.edu.pe/reglamentomat.htm` returned 200. The page labels the new enrollment regulation, lists annex topics, separately labels an “ANTIGUO REGLAMENTO DE MATRÍCULA,” and separately lists RR 03524-R-14 and RR 002642-2026-R. It identifies source-page roles but is not a substitute for the regulation and resolution texts. Retain the old text, amendment and current approval as distinct documents.

### FISI 2009-plan transition notice

The official FISI page opened and its complete body was read in Playwright. It reports Faculty Council Virtual No. 17 / Ordinary Session No. 12 on 22 September 2020 approving validity of Plan 2009 through 2021-II. Its bullets say cycles 1–6 could convalidate to 2018; cycles 7–8 to 2014; cycles 9–10 could finish under 2009. The notice gives neither admission years nor an assigned-plan mapping, course-by-course table, return-after-interruption procedure or mandatory/optional migration rule. The referenced Council record and the separate RD 000510-D-FISI-19 / RR 00721-R-20 chain remain uninspected; the apparent validity/completion tension is unresolved.

### RR 000046-2026-R and attachment

The official Gob.pe record returned 200 and states (record dated 8 January 2026) that RR 000046-2026-R ratifies RD 000738-2025-D-FISI and RD 001281-2025-D-FISI, in the sense of modifying RD 000777-2024-D-FISI, expanded by RD 001030-2024-D-FISI, concerning the Plan 2018–Plan 2023 equivalency table in an annex.

The linked signed PDF was opened in the browser PDF viewer and visually inspected:

- **Page 1:** resolution dated 6 January 2026; *Visto* expressly names the Professional School of Systems Engineering. It recounts RR 013181-2024-R, RDs 000777/001030-2024, and the Plan 2018-to-2023 equivalency-table lineage. It also describes later requests/modifications associated with the two 2025 decanal resolutions.
- **Page 2:** `DICE` / `DEBE DECIR` paired tables headed `PLAN 2018` and `PLAN 2023`, followed by language that the rest remains in force and an operative clause modifying RR 013181-2024-R. Visually readable entries include course codes, cycles, names, credits and type; the raster table needs second-person manual QA before converting into searchable rows.
- The resolution PDF and its embedded table are a separate attachment from the HTML record. The two are linked in DOC-119/120; they are not duplicate documents.

Screenshots captured through Playwright: [`rr000046-attachment-audit.png`](evidence/screenshots/rr000046-attachment-audit.png) (p.1) and [`rr000046-annex-folio78-audit.png`](evidence/screenshots/rr000046-annex-folio78-audit.png) (p.2). Page 2 is two pages in the attachment; “foja 78” refers to the annex folio in the cited underlying file, not page 78 of this two-page signed RR attachment.

## Ingestion and applicability

The synchronized dictionary displays each audited record and these independent fields:

- **INCLUDE:** only records previously selected and reviewed, still conditional on extracting/chunking the local file and validating citations.
- **REVIEW_REQUIRED:** content, applicability, provenance or extraction needs more work. This includes potential historical rules that are useful for period-specific questions.
- **DISCOVERY_ONLY:** source indexes/catalogs; use to discover primary records, not as operative rule text.
- **EXCLUDE:** outside the defined undergraduate FISI student corpus.
- **Applicability:** `established` only where reviewed text establishes scope; `limited to a population` where audience/period is explicit; `historical` for historical material; otherwise `uncertain`.

An item may be ingestion-ready but not applicable to an unspecified user, or have established scope but still require extraction QA. `CURRENT` and `INCLUDE` do not prove every FISI student's assigned plan or cohort eligibility.

## Hashes, duplicate candidates, and extraction quality

See `docs/duplicate_groups.md` and `data/document_inventory_audited.csv`. Exact duplicate groups are **not confirmed** because local source bytes are absent. Candidate families remain separate, including enrollment editions, cross-host calendar files, law copies, degrees regulations and the 2018/2023 equivalency lineage. No resolution, annex, amendment, equivalency table or mirror is collapsed on title or URL similarity.

No extracted document text was available for quality scoring. For all source URLs, the audit flags missing local files and extracted text; the RR 000046 table receives the more specific `VISUAL_REVIEWED_TABLE_UNVERIFIED` flag. On download, inspect:

- course-code rows, cycle/credit/type columns and `DICE`/`DEBE DECIR` replacements;
- prerequisite tables, notes, footnotes, legends and cross-page headers;
- resolution signatures and approval/date fields;
- scan-only pages that need OCR, with OCR output checked visually against the image.

Do not trust PDF text extraction for curriculum tables until the row/column associations and footnotes are manually checked.

## Evidence-backed relationships

Machine-readable table: `data/document_relationships.csv`.

Examples with explicit support:

| Source → target | Relationship | Evidence |
|---|---|---|
| DOC-005 → DOC-002 | APPROVES | RR 002642-2026-R operative clause 1; 18-page regulation annex. |
| DOC-051 → DOC-050 | EXTENDS | RR 07482-R-19 operative clause 1; through December 2020. |
| DOC-120 → RR 013181-2024-R | AMENDS | Signed attachment p.2 operative clause 2; “DICE/DEBE DECIR” table text. |
| DOC-120 → 2018 and 2023 Systems plans | EQUIVALENCE_BETWEEN | Attachment p.1 names EP Ingeniería de Sistemas; p.2 table headings pair Plan 2018 and Plan 2023. This supports only the listed table rows. |
| DOC-120 → RD 000777/001030/000738/001281 | AMENDS / EXTENDS (as specified in CSV) | Gob.pe record operative description; signed PDF's page 1 identifies the EP and chain. |
| DOC-118 → Faculty Council decision | REPORTS_APPROVAL_BY | FISI notice body; underlying minutes are unavailable, so this records the notice's claim and is marked medium confidence. |

No `REPEALS` relationship is recorded without an inspected operative clause establishing it. The 2009 notice and reported 2019/2020 resolution chain remain unresolved rather than collapsed into a definitive repeal conclusion.

## Retrieval validation scenarios

There is no local content store or RAG runtime in the repository, so live retrieval execution cannot be claimed. These are **retrieval-oracle tests**: expected supporting records and answer constraints to run after ingestion. Until then, mark them **BLOCKED / NOT EXECUTED**, not passed.

| Query scenario | Expected source selection and supported answer | Required clarification / failure behavior | Status |
|---|---|---|---|
| Older-plan student returning after interruption | Retrieve current enrollment rule DOC-005/DOC-002 (including reactualization/current-plan clause) plus assigned-plan/transition records. Explain current-plan placement only with the cited clause; consult DOC-118 for the historical 2009 cycle transition if relevant. | Ask the student’s assigned plan, school, last enrolled semester, and interruption length if missing. Do not infer plan from admission year or imply the 2009 notice grants current return rights. Approved plan and transition gaps prevent a complete determination. | BLOCKED — current RAG/index absent; critical transition sources missing. |
| Prerequisites under different plans | Retrieve only the approved plan/malla for each named plan/cohort and the 2026 student guide if relevant. Cite course rows/footnotes and plan identifiers. | If plan not supplied, ask which assigned plan; if either plan's approved prerequisite source is absent, state that the comparison cannot be verified. Never mix prerequisites across plans. | BLOCKED — no local mallas; only one prerequisite-related discovery record is inventoried. |
| Equivalency after migration | Retrieve DOC-120 and its relation to DOC-119. Cite the exact 2018↔2023 correction table and limit answer to listed courses; DOC-118 only for its distinct 2009 cycle route. | Ask source and destination assigned plans and course code. Do not infer equivalence for unlisted courses or assign the table to another EP. Manually verify table transcription before response. | PARTIAL EVIDENCE — source verified; table QA/local file and cohort applicability remain pending. |
| Graduation requirements by cohort | Retrieve currently applicable university degree regulation, transitional clauses, FISI degree requirements and assigned-plan curriculum; preserve distinct cohorts/transition rules. | Ask admission cohort and assigned plan. Without applicable regulation and FISI requirements, do not give a definitive checklist. | BLOCKED — cohort-specific FISI/degree requirement chain not established. |
| Current enrollment rules for an older-plan student | Retrieve DOC-005/DOC-002 for university-wide enrollment rules and the applicable plan-transition/current-plan clause; retrieve 2026-II calendar only for period deadlines. | Ask assigned plan, school, and semester if not known. Distinguish general pregrado scope from legacy-plan placement. Do not present a faculty filing deadline as the SUM deadline. | BLOCKED — rules exist, but assigned plan/current-plan interaction is not fully resolvable. |

## Remaining blockers (critical)

1. **Download and retain actual source attachments locally** from each verified page. Then compute SHA-256 and compare normalized text. Current hashes are unavailable.
2. Obtain the approved Systems plans (2009, 2014, 2018, 2023) and direct approval instruments, full course/prerequisite tables, revisions and cohort rules; verify which 2018 and 2023 course-table text remains after RR 000046-2026.
3. Retrieve the underlying 2020 FISI council minutes/resolution and RD 000510-D-FISI-19 / RR 00721-R-20 to reconcile formal Plan 2009 status with the 2021-II completion arrangement and post-interruption students.
4. Obtain the four decanal decisions in the 2018/2023 equivalency chain and RR 013181-2024-R; inspect full annex folios 78/80 or relevant pages, history and all affected table rows.
5. Obtain cohort-applicable university degree regulation and FISI bachelor/title checklists, with approval/amendment/transitional clauses; map graduation rules to assigned plan and cohort.
6. Download and extract enrollment resolutions/regulation and Directivas 005–010 with signatures, dates, annexes and approval relationships; verify applicability/current status and FISI filing windows.
7. Run per-document extraction QA, especially PDF course tables, prerequisites, footnotes, signatures and scanned pages; validate citations against page images.
8. Implement retrieval tests in the actual RAG pipeline and check citations, plan-conditioned filtering, clarify-when-unknown behavior and historical-source isolation.

Until these are resolved, **do not describe the repository as complete or the five test scenarios as passing**.
