"""Preserve the starting audited inventory and emit a field-level change log."""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/document_inventory.csv"
CURRENT = ROOT / "data/document_inventory_audited.csv"
SNAPSHOT = ROOT / "sources/document_inventory_pre_collection.csv"
CHANGES = ROOT / "sources/collection_corrections.csv"


def read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def starting_audit() -> tuple[list[str], list[dict[str, str]]]:
    spec = importlib.util.spec_from_file_location("audit_builder", ROOT / "scripts/build_repository_audit.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load the initial audit builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original_fields, rows = module.read_inventory()
    if len(rows) != 117:
        raise RuntimeError(f"Expected original inventory to have 117 rows; got {len(rows)}")
    rows.extend(dict(item) for item in module.ADDITIONS)
    fields = original_fields + module.AUDIT_FIELDS
    for row in rows:
        action, rationale = module.decision(row)
        row["ingestion_decision"] = action
        row["applicability"] = module.applicability(row)
        row["local_file_path"] = ""
        row["sha256"] = "NOT_AVAILABLE_NO_LOCAL_FILE"
        row["duplicate_group"] = "UNKNOWN_NO_LOCAL_BYTES"
        row["text_comparison"] = "NOT_POSSIBLE_NO_LOCAL_EXTRACTED_TEXT"
        row["extraction_quality"], row["manual_verification_required"] = module.quality(row)
        row["verified_source_urls"] = " | ".join(dict.fromkeys(filter(None, [row.get("url", ""), row.get("source_page", "")])))
        row["correction_log"] = rationale
    return fields, rows


def reason(field: str) -> str:
    reasons = {
        "local_file_path": "Downloaded and validated source file; local path recorded in manifest.",
        "sha256": "Computed SHA-256 from acquired original bytes; value is reproducible from the local file.",
        "file_identity": "Replaced NOT_COMPARED with byte-level SHA-256 after acquisition.",
        "duplicate_group": "Updated from unknown/no local bytes to hash comparison over acquired files.",
        "text_comparison": "Updated after page-labelled extraction and comparison; see extracted comparison notes.",
        "extraction_quality": "Updated after validating PDF signature, extracting pages, and detecting scan-only pages.",
        "manual_verification_required": "Updated with page/table/OCR verification needs found during extraction.",
        "access_review": "Updated after successful source download and PDF signature validation.",
        "review_note": "Updated with acquired source, extraction outcome, and page-level evidence.",
        "content_review": "Updated to reflect the acquired/extracted content and OCR or annex limitations.",
        "verified_source_urls": "Updated to retain all verified source URLs for matching components.",
        "relationship_evidence": "Updated with extracted-text comparison or source-document evidence.",
    }
    return reasons.get(field, "Collection-stage evidence update; the original value is preserved in the pre-collection snapshot.")


def main() -> None:
    start_fields, start_rows = starting_audit()
    write(SNAPSHOT, start_fields, start_rows)
    current_fields, current_rows = read(CURRENT)
    old = {row["doc_id"]: row for row in start_rows}

    pre_fields = [f"pre_collection_{field}" for field in current_fields if not field.startswith("pre_collection_") and field != "record_added_during_collection"]
    output_fields = current_fields + [f for f in pre_fields if f not in current_fields]
    if "record_added_during_collection" not in output_fields:
        output_fields.append("record_added_during_collection")

    changes: list[dict[str, str]] = []
    for row in current_rows:
        baseline = old.get(row["doc_id"])
        row["record_added_during_collection"] = "NO" if baseline else "YES"
        for field in output_fields:
            if field.startswith("pre_collection_"):
                original_field = field.removeprefix("pre_collection_")
                row[field] = baseline.get(original_field, "") if baseline else ""
        if baseline:
            for field in start_fields:
                before, after = baseline.get(field, ""), row.get(field, "")
                if before != after:
                    changes.append({
                        "doc_id": row["doc_id"],
                        "field": field,
                        "pre_collection_value": before,
                        "current_value": after,
                        "change_reason": reason(field),
                    })

    write(CURRENT, output_fields, current_rows)
    change_fields = ["doc_id", "field", "pre_collection_value", "current_value", "change_reason"]
    write(CHANGES, change_fields, changes)
    print(f"Preserved {len(start_rows)} starting audited rows in {SNAPSHOT.relative_to(ROOT)}")
    print(f"Logged {len(changes)} changed field values in {CHANGES.relative_to(ROOT)}")
    print(f"Current inventory: {len(current_rows)} rows, {len(output_fields)} columns")


if __name__ == "__main__":
    main()
