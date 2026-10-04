"""Build auditable repository metadata while preserving the supplied inventory."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/document_inventory.csv"
INVENTORY = ROOT / "data/document_inventory_audited.csv"
DICTIONARY = ROOT / "docs/document_dictionary.md"

AUDIT_FIELDS = [
    "ingestion_decision",
    "applicability",
    "local_file_path",
    "sha256",
    "duplicate_group",
    "text_comparison",
    "extraction_quality",
    "manual_verification_required",
    "verified_source_urls",
    "correction_log",
]

ADDITIONS = [
    {
        "title": "Comunicado FISI sobre vigencia y adecuación del Plan 2009 de Ingeniería de Sistemas",
        "url": "https://sistemas.unmsm.edu.pe/site/noticias/35-importante/188-comunicado-sobre-la-vigencia-del-plan-de-estudios-2009-de-la-escuela-profesional-de-ingenieria-de-sistemas",
        "source_page": "https://sistemas.unmsm.edu.pe/site/noticias/35-importante/188-comunicado-sobre-la-vigencia-del-plan-de-estudios-2009-de-la-escuela-profesional-de-ingenieria-de-sistemas",
        "category": "plan_de_estudios",
        "publication_date": "UNKNOWN",
        "version": "Plan 2009; Council session 2020-09-22",
        "status": "HISTORICAL",
        "priority": "CRITICAL",
        "notes": "Official FISI notice says Plan 2009 valid through 2021-II and gives cycle-group routes to 2018, 2014, or completion under 2009. Does not establish admission year or return rule.",
        "doc_id": "DOC-118",
        "document_type": "WEB_PAGE",
        "audience": "UNDERGRADUATE",
        "academic_period": "through 2021-II",
        "reported_http_status": "200",
        "reported_checked_on": "2026-09-30",
        "content_review": "PAGE_REVIEWED",
        "checked_on": "2026-09-30",
        "access_review": "RETRIEVED",
        "review_note": "Playwright body text verified; exact stated cycle routes preserved. The underlying council decision and plan equivalency documents are not attached.",
        "corpus_action": "REVIEW_BEFORE_INGEST",
        "action_reason": "Historical transition notice is needed for cohort/return questions but must be paired with the underlying approval and applicable plans.",
        "family_id": "fisi-systems-plan-transition-2009",
        "relation_role": "TRANSITION_NOTICE",
        "related_doc_ids": "DOC-108;EXTERNAL:RD-000510-D-FISI-19;EXTERNAL:RR-00721-R-20",
        "relationship_evidence": "Body: Council Virtual No. 17 / Ordinary Session No. 12 (2020-09-22); Plan 2009 through 2021-II; bullets 1–3 specify cycle routes. No direct relationship to the later resolution chain asserted.",
        "file_identity": "WEB_PAGE; no downloaded source file",
        "original_title": "UNKNOWN (added in audit)",
        "original_publication_date": "UNKNOWN",
        "original_version": "UNKNOWN",
        "original_status": "UNKNOWN",
        "original_notes": "Added from official FISI page verified in Playwright on 2026-09-30.",
    },
    {
        "title": "RR 000046-2026-R/UNMSM: modificación de equivalencias Plan 2018–Plan 2023 (Gob.pe record)",
        "url": "https://www.gob.pe/institucion/unmsm/normas-legales/7601870-000046-2026-r-unmsm",
        "source_page": "https://www.gob.pe/institucion/unmsm/normas-legales/7601870-000046-2026-r-unmsm",
        "category": "plan_de_estudios",
        "publication_date": "2026-01-08",
        "version": "RR-000046-2026-R/UNMSM",
        "status": "POSSIBLY_CURRENT",
        "priority": "CRITICAL",
        "notes": "Official legal record identifies EP Ingeniería de Sistemas and summarizes ratification/modification chain; attachment is separate DOC-120.",
        "doc_id": "DOC-119",
        "document_type": "WEB_PAGE",
        "audience": "UNDERGRADUATE",
        "academic_period": "Plan 2018–Plan 2023",
        "reported_http_status": "200",
        "reported_checked_on": "2026-09-30",
        "content_review": "PAGE_REVIEWED",
        "checked_on": "2026-09-30",
        "access_review": "RETRIEVED",
        "review_note": "Playwright status 200 and record body verified. Record says RR ratifies RD 000738-2025 and RD 001281-2025, modifying RD 000777-2024 expanded by RD 001030-2024; attachment cites foja 78. Signed attachment itself identifies EP Ingeniería de Sistemas.",
        "corpus_action": "DISCOVERY_ONLY",
        "action_reason": "Official source/metadata record supports provenance; use attached signed resolution DOC-120 for operative clauses and table.",
        "family_id": "fisi-systems-equivalence-2018-2023",
        "relation_role": "OFFICIAL_RECORD",
        "related_doc_ids": "DOC-120;EXTERNAL:RD-000777-2024-D-FISI;EXTERNAL:RD-001030-2024-D-FISI;EXTERNAL:RD-000738-2025-D-FISI;EXTERNAL:RD-001281-2025-D-FISI",
        "relationship_evidence": "Gob.pe record operative description and paragraph, dated 2026-01-08; attachment verified visually in Playwright.",
        "file_identity": "HTML page; no local file hash",
        "original_title": "UNKNOWN (added in audit)",
        "original_publication_date": "UNKNOWN",
        "original_version": "UNKNOWN",
        "original_status": "UNKNOWN",
        "original_notes": "Added from official Gob.pe record verified in Playwright on 2026-09-30.",
    },
    {
        "title": "Signed attachment: RR 000046-2026-R/UNMSM and amended equivalency table, EP Ingeniería de Sistemas",
        "url": "https://cdn.www.gob.pe/uploads/document/file/9263767/7601870-resolucion-rectoral-n-000046-2026-r-unmsm.pdf?v=1767903832",
        "source_page": "https://www.gob.pe/institucion/unmsm/normas-legales/7601870-000046-2026-r-unmsm",
        "category": "plan_de_estudios",
        "publication_date": "2026-01-06 (signed; Gob.pe record dated 2026-01-08)",
        "version": "RR-000046-2026-R/UNMSM",
        "status": "POSSIBLY_CURRENT",
        "priority": "CRITICAL",
        "notes": "Two-page signed PDF. Page 1 names EP Ingeniería de Sistemas and amendment lineage; page 2 contains DICE/DEBE DECIR course-table corrections and says the rest remains in force.",
        "doc_id": "DOC-120",
        "document_type": "PDF",
        "audience": "UNDERGRADUATE",
        "academic_period": "Plan 2018–Plan 2023",
        "reported_http_status": "200",
        "reported_checked_on": "2026-09-30",
        "content_review": "VISUAL_REVIEWED",
        "checked_on": "2026-09-30",
        "access_review": "RETRIEVED_BROWSER_ONLY",
        "review_note": "Retrieved/rendered in Playwright PDF viewer and inspected as page screenshots 1–2. No local PDF file was saved, so no hash or text extraction is available. Table transcription and signature metadata require independent manual QA before indexing.",
        "corpus_action": "REVIEW_BEFORE_INGEST",
        "action_reason": "Critical plan equivalency amendment, but table-cell extraction/OCR and local-file integrity are not validated.",
        "family_id": "fisi-systems-equivalence-2018-2023",
        "relation_role": "AMENDING_RESOLUTION_AND_EQUIVALENCY_TABLE",
        "related_doc_ids": "DOC-119;EXTERNAL:RR-013181-2024-R;EXTERNAL:RD-000777-2024-D-FISI;EXTERNAL:RD-001030-2024-D-FISI;EXTERNAL:RD-000738-2025-D-FISI;EXTERNAL:RD-001281-2025-D-FISI",
        "relationship_evidence": "Page 1: Visto names EP Ingeniería de Sistemas; considers RR 013181-2024 and RDs 000777/001030; page 2 operative 1 has DICE/DEBE DECIR tables, operative 2 modifies RR 013181-2024 and retains everything else; table heading Plan 2018 / Plan 2023.",
        "file_identity": "Attachment URL distinct from HTML record; local bytes unavailable; NOT_HASHED",
        "original_title": "UNKNOWN (added in audit)",
        "original_publication_date": "UNKNOWN",
        "original_version": "UNKNOWN",
        "original_status": "UNKNOWN",
        "original_notes": "Added after Playwright visual inspection of both PDF pages on 2026-09-30.",
    },
]


def read_inventory() -> tuple[list[str], list[dict[str, str]]]:
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def decision(row: dict[str, str]) -> tuple[str, str]:
    existing = row.get("corpus_action", "")
    if existing == "INCLUDE":
        return "INCLUDE", "Prior selected corpus record; keep conditional on current extraction and chunk QA."
    if existing == "DISCOVERY_ONLY":
        return "DISCOVERY_ONLY", "Locator/catalog page; do not treat as operative rule text."
    if existing == "OUT_OF_SCOPE":
        return "EXCLUDE", "Outside the undergraduate FISI student corpus defined by the existing review."
    if existing == "SOURCE_GAP":
        return "REVIEW_REQUIRED", "Missing/inaccessible source locator is an unresolved blocker, not an ingestible content file."
    return "REVIEW_REQUIRED", "Content identity, legal status, extraction quality, or scope has not been fully verified for ingestion."


def applicability(row: dict[str, str]) -> str:
    if row.get("status") == "HISTORICAL":
        return "historical"
    if row.get("doc_id") in {"DOC-002", "DOC-005"}:
        return "established"
    if row.get("audience") not in ("", "UNDETERMINED"):
        return "limited to a population"
    if row.get("academic_period") not in ("", "UNKNOWN"):
        return "limited to a population"
    return "uncertain"


def quality(row: dict[str, str]) -> tuple[str, str]:
    if row.get("doc_id") == "DOC-120":
        return "VISUAL_REVIEWED_TABLE_UNVERIFIED", "Manual table transcription, footnotes, and signature validation required."
    if row.get("content_review") == "CONTENT_REVIEWED":
        return "PRIOR_CONTENT_REVIEW_NO_LOCAL_EXTRACT", "Verify extracted text/pages against the source PDF before ingestion."
    if row.get("content_review") == "PAGE_REVIEWED":
        return "PAGE_TEXT_REVIEWED_ATTACHMENT_NOT_AVAILABLE", "No local attachment/text available for extraction QA."
    return "NOT_ASSESSED_NO_LOCAL_DOCUMENT", "Download source attachment and inspect tables, prerequisites, footnotes, signatures, and scanned pages."


def main() -> None:
    original_fields, rows = read_inventory()
    if len(rows) != 117:
        raise SystemExit(f"Expected the 117-row source inventory; found {len(rows)}")
    for extra in ADDITIONS:
        rows.append(extra)

    fields = original_fields + AUDIT_FIELDS
    for row in rows:
        act, rationale = decision(row)
        row["ingestion_decision"] = act
        row["applicability"] = applicability(row)
        row["local_file_path"] = ""
        row["sha256"] = "NOT_AVAILABLE_NO_LOCAL_FILE"
        row["duplicate_group"] = "UNKNOWN_NO_LOCAL_BYTES"
        row["text_comparison"] = "NOT_POSSIBLE_NO_LOCAL_EXTRACTED_TEXT"
        row["extraction_quality"], row["manual_verification_required"] = quality(row)
        row["verified_source_urls"] = " | ".join(dict.fromkeys(filter(None, [row.get("url", ""), row.get("source_page", "")])))
        row["correction_log"] = rationale

    with INVENTORY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    by_category: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_category[row.get("category", "UNKNOWN")].append(row)
    actions = Counter(row["ingestion_decision"] for row in rows)
    apps = Counter(row["applicability"] for row in rows)

    lines = [
        "# FISI / UNMSM document dictionary — audited inventory edition",
        "",
        "Generated from `data/document_inventory_audited.csv` by `scripts/build_repository_audit.py`.",
        "The supplied 117 inventory records and every original field/value are preserved; audit fields are appended. Three Playwright-verified FISI transition/equivalency records were added as DOC-118–DOC-120.",
        "",
        "## Audit status",
        "",
        f"- Records: {len(rows)} ({len(rows)-len(ADDITIONS)} preserved source records + {len(ADDITIONS)} audit additions).",
        "- Ingestion decisions: " + ", ".join(f"{k}={v}" for k, v in sorted(actions.items())) + ".",
        "- Applicability labels: " + ", ".join(f"{k}={v}" for k, v in sorted(apps.items())) + ".",
        "- No local PDF/DOCX files were present. Hashes and extracted-text comparisons are unavailable; candidate copies were not merged.",
        "- Applicability is independent of ingestion readiness. `established` describes only explicit applicability evidence in the reviewed records; `uncertain` is not a negative determination.",
        "- See `docs/repository_audit_report.md`, `data/document_relationships.csv`, and `docs/duplicate_groups.md` for evidence and unresolved items.",
        "",
        "## Definitions",
        "",
        "| Field | Meaning |",
        "|---|---|",
        "| `ingestion_decision` | INCLUDE, REVIEW_REQUIRED, DISCOVERY_ONLY, or EXCLUDE. Separate from validity. |",
        "| `applicability` | established, uncertain, limited to a population, or historical. |",
        "| `sha256` | Local byte digest; NOT_AVAILABLE_NO_LOCAL_FILE means the source was not downloaded into this workspace. |",
        "| `duplicate_group` / `text_comparison` | No exact/near-duplicate claims absent local bytes and extracted text. Topic families are not identity claims. |",
        "| `extraction_quality` | Assessment of current local extraction evidence; prior review notes do not stand in for a local extraction. |",
        "| `verified_source_urls` | URL and discovery/source page retained on each record. |",
        "| `correction_log` | Rationale for the normalized ingestion decision; original `corpus_action`, `status`, notes, and `original_*` values remain intact. |",
        "",
        "## Records by category",
        "",
    ]
    for category in sorted(by_category):
        lines.extend([f"### {category} ({len(by_category[category])})", "", "| ID | Document | Ingestion | Applicability | Source | Extraction / correction |", "|---|---|---|---|---|---|"])
        for row in by_category[category]:
            title = row.get("title", "").replace("|", "\\|")
            source = row.get("url", "")
            note = (row.get("manual_verification_required", "") or row.get("correction_log", "")).replace("|", "\\|")
            lines.append(f"| {row.get('doc_id','')} | [{title}]({source}) | {row['ingestion_decision']} | {row['applicability']} | [source/page]({row.get('source_page','')}) | {note} |")
        lines.append("")

    DICTIONARY.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {INVENTORY.relative_to(ROOT)} ({len(rows)} rows, {len(fields)} columns)")
    print(f"Synchronized {DICTIONARY.relative_to(ROOT)} across {len(by_category)} categories")


if __name__ == "__main__":
    main()
