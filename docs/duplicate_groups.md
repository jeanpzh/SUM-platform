# Duplicate groups and file-identity audit

Audit updated: 2026-09-29 America/Lima. Source inventory retained all original URL records and appended acquired FISI records.

## Exact duplicates

**No byte-identical duplicate group was found among the 39 downloaded PDFs.** Their SHA-256 values are in `sources/source_manifest.csv` and in the corresponding audited inventory rows. No source content was removed. For files not acquired, hash status remains unavailable.

Two source PDFs contain page subdocuments whose normalized extracted text matches exactly, while the full PDFs have different byte hashes:

- DOC-079 pages 1–2 match the standalone RR 002642-2026-R file DOC-005 (text ratio 1.00000).
- DOC-079 pages 3–20 match the standalone 18-page regulation DOC-002 (text ratio 1.00000).

DOC-079 is one combined resolution-plus-annex file. Keep DOC-005 and DOC-002 as separate logical records; store one copy of the 18-page regulation content with both DOC-002 and DOC-079 source URLs, and keep the two-page approving resolution content attached as a distinct record. This is a demonstrated text-level component relationship, not a byte-identical file group.

## Candidate copy/version families — keep distinct pending comparison

| Candidate family | Records | Why compare | Current treatment |
|---|---|---|---|
| Undergraduate enrollment texts/resolutions | DOC-002, DOC-003, DOC-005, DOC-043, DOC-079, DOC-080, DOC-114, DOC-115, DOC-116 | Similar subject and overlapping resolution chain; annual regulations/amendments may differ materially. | DOC-079 contains text-identical RR DOC-005 and regulation annex DOC-002 as separate page ranges, but full bytes differ. Other editions/resolutions remain distinct pending comparison. |
| 2026 academic calendar | DOC-007, DOC-008, DOC-082, DOC-106 | Same academic period/resolution labels across SUM, VRAP and FISI hosts. | Keep resolution, annex and faculty/university copies distinct. No byte or text equivalence demonstrated. |
| 2025 academic calendar | DOC-009, DOC-010 | Resolution and annex, not duplicates by role. | Keep separate; historical applicability. |
| 2024/2023 calendars | DOC-011–DOC-014, DOC-044 | Resolution PDFs and annexes for distinct periods/roles. | Keep separate; no cross-year deduplication. |
| Law 30220 copies | DOC-072, DOC-096 (plus discovery page DOC-071) | Same underlying law may have different consolidation dates, annotations, or amendments. | Keep separate; compare publication/consolidation text before declaring mirrors. |
| General degrees-and-titles regulation | DOC-083, DOC-084 | Similar titles and adjacent editions; transition clauses may differ. | Keep separate; do not label identical/repealed solely by title/date. |
| Faculty systems-plan sources | DOC-108, DOC-118–DOC-125, DOC-128–DOC-130 | Distinct plans, approval instruments, transition minutes, offering snapshots and equivalency tables. | Keep distinct. RD 000163 and RD 000609 one-page resolution files omit their cited 96-folio and 5-folio annexes. RR 000046 is a two-page amendment for two rows only. |
| General degrees and titles | DOC-083, DOC-084 | Adjacent regulation packages with overlapping extracted text. | Normalized text similarity 0.8521; DOC-083 adds the 2022 extension of automatic bachelor eligibility through 2023-II. Different resolution/transition content; retain separately. |
| Teaching-activity regulation family | DOC-045, DOC-047, DOC-060, DOC-061, DOC-088 | Base/amendments/potential consolidated rendering. | Keep base and amendments distinct; no full text/hash comparison. |

## Required rerun after collection download

1. Acquire the missing plan and annex files listed in `docs/source_collection_report.md`; add hashes and extraction rows to the manifest.
2. Preserve one content object for exact byte duplicates and all verified URLs. For DOC-079 component matches, retain the resolution and annex roles as distinct logical records and associate both URLs with the matching annex content.
3. OCR scan-only PDFs, compare normalized text only as a candidate detector, and visually inspect differences in resolution, annex, amendment, footnotes, course tables, signatures and scanned pages.
4. Never merge merely because resolution numbers, titles or file names match.
