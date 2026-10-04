# FISI source collection report

**Collection date:** 2026-09-29 America/Lima (Playwright capture timestamps through 2026-09-30 UTC).  
**Status:** substantial acquisition completed; **repository remains incomplete** and is not a comprehensive curriculum RAG corpus.

## Executive result

- Preserved the 120 prior inventory rows and added DOC-121–DOC-130; the audited inventory now has **130 records**. The initial 120-row audited snapshot is saved at `sources/document_inventory_pre_collection.csv`; all field-level changes are logged in `sources/collection_corrections.csv`. The untouched original 117-row inventory remains `data/document_inventory.csv`.
- Acquired **39 publicly linked PDF files** into `sources/originals/`. Each has a source URL, discovery page, retrieval date, local path, file type, byte size, SHA-256 and download validation in `sources/source_manifest.csv`.
- Extracted page-labelled text into `sources/extracted/`. MuPDF confirms the PDFs; exact file hashes show **0 byte-identical duplicates among the acquired set**.
- Two combined-PDF components have exact normalized extracted-text matches, without byte identity: DOC-079 pages 1–2 match DOC-005 (RR 002642-2026-R), and pages 3–20 match DOC-002 (the 18-page regulation). Keep the approving RR and regulation as distinct logical records and preserve the VRAP source URL as an alternate source for each component.
- Playwright acquisition found key official sources, including the 96-folio Systems 2023 curriculum resolution, the 2014→2018 equivalency resolution, 2020/2021 Faculty Council minutes, the 2024 language directive and an official 2026 course-offering report. Several downloaded PDFs omit the annexes their resolutions cite; they are recorded as incomplete, not treated as full curricula.
- There is no RAG runtime/index here. Retrieval tests are not reported as passed.

## 1. Documents acquired and verified

The complete 39-file ledger, exact URLs, sizes, SHA-256 hashes, local paths, extraction paths, page counts and OCR/manual-review status is [`sources/source_manifest.csv`](../sources/source_manifest.csv). Original files are under [`sources/originals/`](../sources/originals/); page-labelled text is under [`sources/extracted/`](../sources/extracted/).

### FISI plans, migration and offerings

- **DOC-121 — RD 000163-2023-D-FISI**, one-page resolution approving the 2023 curricular program for EP Ingeniería de Sistemas. The operative clause says its annex is 96 folios; those pages are **not present** in the downloaded PDF.
- **DOC-122 — RD 000609-2022-D-FISI**, one-page resolution approving a 2014→2018 equivalency table and citing the Systems plan approvals. It says the equivalency annex is five folios; those pages are **not present** in the downloaded PDF.
- **DOC-123–DOC-125 — course-programming reports** for Systems Plan 2018, Software Plan 2018 and Computing Plan 2023. They are dated **8 January 2026** and cover **2026-0**; they show courses scheduled/offered, not complete curriculum, credits, prerequisites or admission cohorts.
- **DOC-118 — FISI Plan 2009 validity notice** and **DOC-130 — 2020 Council Acta No. 17/session 12**. The notice says Plan 2009 was valid through 2021-II and gives cycle-group routes. The Acta records an 8–1 vote to make Plan 2009 ineffective from 2022-I; it does not establish the notice’s cycle-by-cycle course table.
- **DOC-128 and DOC-129 — July 2021 Council minutes**. They show a request to consider 2009→2018 equivalencies and a later proposed migration/table; the July 27 Acta says the migration and table items remained pending approval at that meeting. Redacted, page-cited research excerpts are in `sources/extracted/FISI-Acta*-redacted-extract.txt`.
- **DOC-120 — RR 000046-2026-R/UNMSM**. Its two-page attachment identifies EP Ingeniería de Sistemas and amends specific rows in the Plan 2018↔2023 table. Page 2’s two `DEBE DECIR` rows were manually compared with the rendered Playwright page and extracted text.

### University-wide matrícula, equivalency, evaluation and degree sources

- Current enrollment: RR 002642-2026-R, SUM’s 18-page regulation, the VRAP combined RR+annex PDF, and the 2026 academic-calendar annex (DOC-002, DOC-005, DOC-008, DOC-079).
- Reactualization/reservation/rectification and related procedures: SUM Directivas 005–010, Directivas 001-2021 and 011, RR 013045-2021, RR 04005-R-16, RR 0438-R-09, and SUM Directiva approval resolutions RR 2272-R-13/RR 2810-R-13 (DOC-018–DOC-037, DOC-052–DOC-053, as mapped in manifest).
- Course convalidation: RR 005516-2021 with its four-folio annex (DOC-086); the older SUM Directivas 007 and 008 remain distinct and their present applicability is not assumed.
- Evaluation, Statute and law: RR 007510-2021 evaluation regulation, RR 04626-R-06, Law 30220 and the 84-page Statute PDF (DOC-054, DOC-070, DOC-072, DOC-117).
- Degrees/language/research: 2021 and 2022 General Degrees and Titles files, RR 014041-2024 language directive, RR 00744-R-20 research/thesis directive, and the FISI bachelor/title checklists (DOC-083/084, DOC-103/104, DOC-126/127).

### File integrity and text comparison

- Every acquired file passed the `%PDF-` signature check and had page-level text extraction where the PDF contained a text layer. SHA-256 values are recorded in the manifest.
- **No byte-identical duplicates** were found among the 39 downloaded files. All acquired source files have distinct SHA-256 values.
- `sources/extracted/text_comparisons.md` records similarity candidates. DOC-083 vs DOC-084 (2021/2022 degree-rule packages) remain separate: the 2022 file adds a distinct transition extending automatic-bachelor treatment through 2023-II. DOC-002/DOC-079 page-subdocument comparisons are exact normalized text matches (1.00000) but whole files are different because DOC-079 contains the approval RR plus annex.
- The older SUM enrollment directives quote a superseded matrícula base and conflict on some periods with the 2026 regulation. They remain separate, historical/procedural candidates; do not use their “two years” reservation limit in place of the current three-year rule.

## 2. Suitable for a limited initial corpus

These sources can support **narrow, well-qualified** answers after citation/chunk QA:

1. **Current university-wide matrícula:** DOC-005 approval RR + DOC-002 regulation. Store the regulation once; keep the DOC-079 VRAP URL as an alternate source for the exact-text annex and preserve the separate RR approval. Scope is undergraduate; assigned-plan applicability still needs plan/cohort evidence.
2. **Period-specific 2026 calendar:** DOC-008, only for questions about 2026 and only after the dated activities are separated from the resolution/annex metadata.
3. **Language accreditation:** DOC-126, limited to the population in Art. 3 and exact procedures/alternatives in Arts. 4–5.4. Do not replace course-plan-specific language evidence with the FISI “optional certificate” checklist.
4. **Specific Systems 2018↔2023 equivalence corrections:** DOC-120, only the two verified `DEBE DECIR` rows and only for EP Ingeniería de Sistemas. Exclude from live retrieval until second-person table QA and plan assignment are available.
5. **Convalidation principles:** DOC-086 can support what the 2021 university regulation says (including the 80% syllabus criterion); label its temporal/legal applicability as review-required until later amendments are ruled out.
6. **Historical Plan 2009 end-date excerpt:** use only the redacted Acta17 excerpt plus the FISI notice, with the two sources’ different evidentiary scopes clearly separated. Do not include full meeting minutes with attendee names.

Do **not** put the following into a general answer corpus yet: DOC-121 or DOC-122 as if their annexes were present; the 2026 programming reports as curriculum/prerequisite tables; the full council minutes with attendee identifiers; scan-only Estatuto/directives; or the FISI DOC-103/DOC-104 checklists as definitive cohort graduation rules.

## 3. Unresolved gaps and official sources attempted

### Exact documents to obtain from FISI/UNMSM

1. **RD 000510-D-FISI-19 (16 Aug 2019)** and **RR 00721-R-20 (18 Feb 2020)**, including signed operative text/attachments. FISI 2023 Decanal files cite them, but no direct source attachment was located. Obtain the specific decision that left Plan 2009 without validity and its ratification.
2. **RR 00698-R-20 (18 Feb 2020)** and its 2009→2014 equivalency table. DOC-130 Council minutes cite it as already approving that table, but the resolution/table is not present in SUM/FISI files collected.
3. **Full Plan 2009, Plan 2014, Plan 2018, and current Plan 2023 curricula** for EP Ingeniería de Sistemas, including all approved annex pages, course codes, cycle, credits, prerequisites, electives, offerings, degree requirements and approved amendments. Exact cited plan instruments include RR 02137-R-15, RR 07026-R-17, RR 06615-R-18, RR 01529-R-19, and RD 000163-2023-D-FISI; the full RD163 annex (96 folios) is missing.
4. **RD 000609-2022-D-FISI five-folio 2014→2018 table annex.** The one-page resolution is downloaded; table pages are not.
5. **RR 013181-2024-R, RD 000777-2024-D-FISI, RD 001030-2024-D-FISI, RD 000738-2025-D-FISI and RD 001281-2025-D-FISI**, including the annex/table at folios 78/80 and any whole-curriculum ratification. RR 000046-2026-R alone establishes the amendment chain and two corrected rows, not the complete table or curriculum.
6. **Migration/course-continuity decision after the 27 July 2021 Council minutes.** DOC-129 says the 2009→2018/2014 migration and 2009→2018 equivalency were still pending. Obtain the later Council/Decanal/Rectoral decision and table that adopted any proposal, plus course discontinuation/last-offering rules.
7. For **Ingeniería de Software, Ciencia de la Computación and Inteligencia Artificial**, obtain each EP’s approved curriculum, approving resolution, amendments, admission cohorts/assigned-plan mapping, prerequisites, credits and transition rules. Current source collection only has two 2026-0 programming reports and the AI discovery label.
8. **Cohort-specific FISI graduation checklist** identifying approved curricular version and transition rules, plus OCR-validated current Estatuto/Art. 189 and full RR 00744-R-20 directive. The FISI bachelor form says language proof is optional, whereas RR 014041-2024 sets an Art. 3 population and a basic-language route/plan-course alternative; the FISI page needs a dated, approved cohort mapping.

### Attempts / source behavior

- **FISI Resoluciones Decanales:** official Playwright archive lists RD 000163-2023 and RD 000609-2022. Downloaded files are valid one-page PDFs, but their cited curricular/equivalency annexes are absent. The inspected RD 2024 archive pages only exposed records through RD 000764; cited RD 000777/001030 were not found there.
- **FISI Council archive/download links:** retrieved official Actas 17 (2020-09-22), 23 (2021-07-20), and 24 (2021-07-27). These resolve the 2020 closure vote and show 2021 migration items pending, but they do not provide the later adopted 2009→2018 table.
- **SUM plan registries:** FISI navigation links to `https://sum.unmsm.edu.pe/loginWebSum/planes.htm`; the previously tested official locator returned 404. The 2018 registry link remains inaccessible; failure is not proof of repeal.
- **Gob.pe RR 000046-2026-R:** record and attachment acquired; no underlying decanal PDF attachments were exposed in the record. Gob.pe search for the RD/RR identifiers returned the ratifying record or unrelated results, not the specific resolutions.
- **VRAP Normativa:** official page currently links matrícula, degree/title, convalidation, language accreditation, and research/thesis directivas; relevant linked PDFs were acquired. The degree annex for RR 00744-R-20 is image-only for pages 3–18.
- Several FISI/VRAP hosts have TLS-chain errors in curl. Their exact links and PDF response types were verified in Playwright; files were checked for PDF signature and hashed. Manifest flags this transport detail; browser-verified official source URLs are preserved.

## 4. Academic questions the evidence can and cannot support

| Question | Evidence can support | Evidence cannot support yet |
|---|---|---|
| What current university enrollment process generally applies to a pregrado student? | RR 002642-2026-R/DOC-002 articles and 2026 dates from DOC-008. | A student’s exact plan/cohort placement, school-specific earlier filing date or right to return from separation without their record and applicable transition instrument. Ask assigned plan and interruption/abandonment status when unknown. |
| What happens to an older-plan student who reactualizes? | 2026 RGM Art. 31 places reactualization on the current plan; its definitions distinguish current-plan students from students in extinction who entered during validity and continue without interruption. Art. 30 bars reactualization after established abandonment. | Which complete current curriculum/prerequisites the individual must take, whether a legacy exception applies, or student-specific eligibility. FISI plan/assignment documents are missing. |
| Was Systems Engineering Plan 2009 allowed past 2021-II? | FISI Acta 17 p.5 accepted ending effect from 2022-I; FISI notice says only through 2021-II. | Whether the notice’s cycle-by-cycle destination routes or a later 2009→2018 table were formally adopted. Acta 24 says the July 2021 proposal/table remained pending. Obtain later instrument/table. |
| Which Systems courses are equivalent across Plan 2018 and 2023? | RR 000046-2026-R page 2 changes two listed entries; answer only those rows and cite them. | Equivalence of any unlisted course, the complete transition table, effects across whole plans, or whether a student is assigned to either plan. Annex history and assigned plan are needed. |
| Which Plan 2014 courses count under Plan 2018? | RD 000609-2022-D-FISI p.1 confirms a resolution approving a 2014→2018 table. | The course-by-course answer; its cited five-folio annex is absent. |
| What prerequisites/credits apply under two FISI plans? | Current FISI course-programming reports identify plan labels and 2026-0 scheduled offerings for three EP/plan combinations. | Complete prerequisites, credits, curriculum, cohort mapping or substitutions. These offering reports are not approved study plans. |
| What are degree requirements for a student’s cohort? | RR 014041-2024 language rule for its defined Art. 3 population and the 2020 bachelor-research directive’s stated scope, subject to OCR for its annex. RR 003078-2022 automatic-bachelor exception is limited through 2023-II. | A definitive FISI cohort checklist, current degree route for a particular assigned plan, or universal language exception. Ask admission cohort and assigned plan; obtain FISI’s approved cohort checklist and OCR/verify relevant annexes. |

## Retrieval-validation status

The five requested scenarios (returning older-plan student; cross-plan prerequisites; equivalency after migration; graduation requirements by cohort; current enrollment for an older-plan student) are represented in the prior audit’s retrieval oracle and this matrix, but **were not run against a live RAG system**. There is no RAG runtime/index here. These scenarios remain NOT EXECUTED; do not report them as passing.

## Runtime indexing handoff

The planned admin dashboard/runtime owns upload, format routing, extraction, chunking and embeddings. This collection prepares its inputs; it does not pre-index or claim runtime retrieval:

- Treat `sources/originals/` as immutable source objects. Persist `sources/source_manifest.csv` provenance (source/discovery URL, retrieval date, local path, content type, byte length, SHA-256) with every indexed chunk.
- Keep resolution, regulation annex, amendment, equivalency table, meeting minute and dated offering report as different logical records even when one PDF bundles several parts. The page ranges and `data/document_relationships.csv` are the linking map.
- For PDFs, preserve page boundaries from `sources/extracted/`. PyMuPDF may be used for digital-text PDFs; the manifest marks image-only pages requiring OCR. Image uploads such as PNG/JPEG require OCR and a visual QA state before they can support legal/course claims.
- Only index a curriculum table after matching codes, cycles, credits, types, prerequisites and footnotes against rendered pages. RD 000163 and RD 000609 currently lack their cited plan/table annex pages, so their existing one-page PDFs cannot supply that content.
- Use SHA-256 for exact file identity. For the enrollment bundle, avoid duplicate regulation chunks by keeping one regulation content object associated with both exact-text source URLs, while retaining the separate RR approval record. Keep remaining near-text families separate until their clause/page differences are checked.
- Carry `doc_id`, source URL(s), page, school, level, plan, cohort if explicit, issuing authority, resolution, effective/historical period, relation IDs, extraction/OCR status and ingestion/applicability labels into runtime metadata. Unknown plan assignment should trigger a clarification request rather than a guessed filter.

## Deliverable pointers

- Revised inventory: [`data/document_inventory_audited.csv`](../data/document_inventory_audited.csv)
- Preserved starting inventory and field-level correction log: [`sources/document_inventory_pre_collection.csv`](../sources/document_inventory_pre_collection.csv), [`sources/collection_corrections.csv`](../sources/collection_corrections.csv)
- Synchronized dictionary: [`docs/document_dictionary.md`](document_dictionary.md)
- Plain-language guide to the 39 acquired PDFs (Spanish): [`docs/diccionario_39_documentos.md`](diccionario_39_documentos.md)
- Evidence-backed relationships: [`data/document_relationships.csv`](../data/document_relationships.csv)
- Coverage matrix: [`docs/fisi_plan_coverage_matrix.md`](fisi_plan_coverage_matrix.md)
- Download ledger/hash/extraction QA: [`sources/source_manifest.csv`](../sources/source_manifest.csv)
- Duplicate/text comparison notes: [`docs/duplicate_groups.md`](duplicate_groups.md), [`sources/extracted/text_comparisons.md`](../sources/extracted/text_comparisons.md)
