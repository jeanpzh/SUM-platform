"""Regenerate the document dictionary from the audited inventory and file manifest."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "data/document_inventory_audited.csv"
MANIFEST = ROOT / "sources/source_manifest.csv"
OUT = ROOT / "docs/document_dictionary.md"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ")


def main() -> None:
    _, rows = read_csv(INV)
    _, files = read_csv(MANIFEST)
    by_category: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_category[row.get("category", "UNKNOWN")].append(row)

    action_counts = Counter(row.get("ingestion_decision", "UNKNOWN") for row in rows)
    applicability_counts = Counter(row.get("applicability", "UNKNOWN") for row in rows)
    hash_counts = Counter(row.get("sha256", "UNKNOWN") for row in rows)
    file_types = Counter(row.get("file_type", "UNKNOWN") for row in files)
    hashes = [row.get("sha256", "") for row in files]
    exact_duplicate_groups = len([n for n in Counter(hashes).values() if n > 1])

    out = [
        "# FISI / UNMSM document dictionary — source collection edition",
        "",
        "Para una explicación sencilla de los 39 PDF adquiridos, consulte [`diccionario_39_documentos.md`](diccionario_39_documentos.md).",
        "",
        "Source of record metadata: `data/document_inventory_audited.csv`. Source of downloaded-file metadata: `sources/source_manifest.csv`.",
        "Original inventory values are preserved in the audited inventory. Acquisition and verification details are additive; missing plans, annexes and applicability are not inferred.",
        "",
        "## Collection status",
        "",
        f"- Inventory records: **{len(rows)}**.",
        f"- Downloaded and PDF-signature-validated local files: **{len(files)}** ({', '.join(f'{k}={v}' for k, v in sorted(file_types.items()))}).",
        f"- Acquired SHA-256 groups with multiple identical files: **{exact_duplicate_groups}**. All acquired files have distinct byte hashes; the 2026 matrícula bundle has exact extracted-text subcomponents across different PDFs (see `sources/extracted/text_comparisons.md`).",
        "- Ingestion readiness is not legal applicability: " + ", ".join(f"{k}={v}" for k, v in sorted(action_counts.items())) + ".",
        "- Applicability labels: " + ", ".join(f"{k}={v}" for k, v in sorted(applicability_counts.items())) + ".",
        "- OCR is required for scan-only pages in the Estatuto, RR 0438-R-09, RR 04626-R-06, RR 2272-R-13, RR 2810-R-13 and pages 3–18 of the RR 00744-R-20 directive. Do not ingest those extracts as complete text.",
        "- The downloaded RD 000163-2023-D-FISI file has only its one-page resolution although it cites a 96-folio curriculum annex; RD 000609-2022-D-FISI has only its one-page resolution although it cites a five-folio equivalency table.",
        "- The repository remains incomplete; see `docs/source_collection_report.md` and `docs/fisi_plan_coverage_matrix.md`.",
        "",
        "## Field guide",
        "",
        "| Field | Interpretation |",
        "|---|---|",
        "| `ingestion_decision` | INCLUDE, REVIEW_REQUIRED, DISCOVERY_ONLY, or EXCLUDE; readiness only. |",
        "| `applicability` | established, uncertain, limited to a population, or historical; independent of ingestion readiness. |",
        "| `local_file_path`, `sha256` | Validated local source object and byte hash when downloaded. |",
        "| `duplicate_group`, `text_comparison` | Byte-duplicate result versus extracted-text near/part comparison; different annexes/resolutions stay distinct. |",
        "| `extraction_quality`, `manual_verification_required` | Text extraction/OCR state and table/signature QA needs. |",
        "| `verified_source_urls` | Every known source URL for the document/component; source page remains separately recorded. |",
        "| `correction_log` | Audit normalization rationale; original values remain in their original fields. |",
        "",
        "## Downloaded file ledger",
        "",
        "| ID | File | Bytes | SHA-256 | Extract | OCR / manual QA |",
        "|---|---|---:|---|---|---|",
    ]
    for item in files:
        out.append(
            f"| {item['doc_id']} | [{cell(item['local_path'])}]({cell(item['exact_source_url'])}) | {item['size_bytes']} | `{item['sha256']}` | {cell(item['extraction_path'])} ({item['extracted_pages']} pages) | {cell(item['ocr_need'])}; {cell(item['manual_table_review'])} |"
        )
    out.extend(["", "## Records by category", ""])
    for category in sorted(by_category):
        out.extend([
            f"### {category} ({len(by_category[category])})",
            "",
            "| ID | Document | Ingestion | Applicability | Source URL | Local file / hash | Extraction / blocker |",
            "|---|---|---|---|---|---|---|",
        ])
        for row in by_category[category]:
            title = cell(row.get("title", ""))
            source = row.get("url", "")
            local = row.get("local_file_path", "")
            digest = row.get("sha256", "")
            local_col = f"`{cell(local)}` / `{digest}`" if local else "NOT DOWNLOADED"
            quality = row.get("extraction_quality", "")
            issue = row.get("manual_verification_required", "") or row.get("correction_log", "")
            out.append(
                f"| {row.get('doc_id','')} | [{title}]({source}) | {row.get('ingestion_decision','')} | {row.get('applicability','')} | [discovery/source page]({row.get('source_page','')}) | {local_col} | {cell(quality)} — {cell(issue)} |"
            )
        out.append("")

    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Synchronized {OUT.relative_to(ROOT)} for {len(rows)} inventory records and {len(files)} acquired files")


if __name__ == "__main__":
    main()
