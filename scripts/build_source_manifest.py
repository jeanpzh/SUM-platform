"""Validate, hash, and extract the downloaded source documents."""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
from collections import defaultdict
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = ROOT / "sources/originals"
EXTRACTED = ROOT / "sources/extracted"
INVENTORY = ROOT / "data/document_inventory_audited.csv"
MANIFEST = ROOT / "sources/source_manifest.csv"

DOC_BY_FILE = {
    "RR-000046-2026-R-UNMSM.pdf": "DOC-120",
    "RR-002642-2026-R.pdf": "DOC-005",
    "Reglamento-Matricula-Pregrado-2026.pdf": "DOC-002",
    "Cronograma-Pregrado-2026-anexo.pdf": "DOC-008",
    "Reglamento-Estatuto-UNMSM.pdf": "DOC-070",
    "Ley-Universitaria-30220-SUM.pdf": "DOC-072",
    "RR-04005-R-16-regularizacion-matricula.pdf": "DOC-052",
    "RR-0438-R-09-reactualizacion.pdf": "DOC-053",
    "Directiva-SUM-005-reactualizacion.pdf": "DOC-029",
    "Directiva-SUM-006-rectificacion.pdf": "DOC-030",
    "Directiva-SUM-007-convalidacion.pdf": "DOC-031",
    "Directiva-SUM-008-equivalencia.pdf": "DOC-033",
    "Directiva-SUM-009-reserva.pdf": "DOC-035",
    "Directiva-SUM-010-extemporanea.pdf": "DOC-036",
    "Directiva-SUM-001-2021-registro-plan.pdf": "DOC-022",
    "Directiva-SUM-011-registro-plan.pdf": "DOC-037",
    "RR-013045-2021-R-pautas-registro-plan.pdf": "DOC-018",
    "RR-2272-R-13-aprueba-directivas-SUM.pdf": "DOC-019",
    "RR-2810-R-13-aprueba-directivas-SUM.pdf": "DOC-020",
    "Guia-Estudiante-Pregrado-2026.pdf": "DOC-081",
    "Reglamento-Grados-Titulos-2022.pdf": "DOC-083",
    "Reglamento-Grados-Titulos-2021.pdf": "DOC-084",
    "Reglamento-Convalidacion-2021.pdf": "DOC-086",
    "FISI-Tramite-grado-bachiller.pdf": "DOC-103",
    "FISI-Tramite-titulo-profesional.pdf": "DOC-104",
    "FISI-flujograma-reactualizacion-reserva.pdf": "DOC-105",
    "Reglamento-Evaluacion-Pregrado-RR-007510-2021.pdf": "DOC-117",
    "RR-04626-R-06-regimen-estudios-evaluacion.pdf": "DOC-054",
    "RD-000163-2023-D-FISI-programa-curricular-2023.pdf": "DOC-121",
    "RD-000609-2022-D-FISI-equivalencias-plan-2014-2018.pdf": "DOC-122",
    "Programacion-asignaturas-Sistemas-Plan-2018.pdf": "DOC-123",
    "Programacion-asignaturas-Software-Plan-2018.pdf": "DOC-124",
    "Programacion-asignaturas-Ciencia-Computacion-Plan-2023.pdf": "DOC-125",
    "Reglamento-Matricula-Pregrado-VRAP-2026.pdf": "DOC-079",
    "Directiva-idioma-extranjero-pregrado-2024.pdf": "DOC-126",
    "Directiva-investigacion-grados-titulos-RR-00744-2020.pdf": "DOC-127",
    "FISI-Acta-Consejo-Facultad-2021-07-20-sesion-13.pdf": "DOC-128",
    "FISI-Acta-Consejo-Facultad-2021-07-27-sesion-14.pdf": "DOC-129",
    "FISI-Acta-Consejo-Facultad-2020-09-22-virtual17-ordinaria12.pdf": "DOC-130",
}

ADDITIONS = [
    {
        "title": "RD 000163-2023-D-FISI: Programa Curricular 2023 de Ingeniería de Sistemas",
        "url": "https://sistemas.unmsm.edu.pe/site/resoluciones-decanales/category/3-rd-2023?download=173:rd-151-200&start=160",
        "source_page": "https://sistemas.unmsm.edu.pe/site/resoluciones-decanales/category/3-rd-2023?limit=20&start=160",
        "category": "plan_de_estudios", "publication_date": "2023-02-20", "version": "RD-000163-2023-D-FISI",
        "status": "POSSIBLY_CURRENT", "priority": "CRITICAL",
        "notes": "Official FISI archive title identifies Programa Curricular 2023 for EP Ingeniería de Sistemas; inspect operative text and embedded plan annex before stating approval/effective scope.",
        "doc_id": "DOC-121", "document_type": "PDF", "audience": "UNDERGRADUATE", "academic_period": "2023",
        "reported_http_status": "200", "reported_checked_on": "2026-09-29", "content_review": "CONTENT_REVIEWED",
        "checked_on": "2026-09-29", "access_review": "RETRIEVED", "review_note": "Downloaded from FISI official category attachment; PDF signature, pages, operative clause, annex and table scope require review.",
        "corpus_action": "REVIEW_BEFORE_INGEST", "action_reason": "Potential base curricular record is critical; retain resolution and annex, verify approval and cohort application before ingestion.",
        "family_id": "fisi-systems-plan-2023", "relation_role": "PROGRAM_CURRICULUM_RESOLUTION_CANDIDATE",
        "related_doc_ids": "DOC-120;DOC-122;EXTERNAL:RR-000046-2026-R", "relationship_evidence": "Official archive attachment label plus text/pages to be inspected.",
        "file_identity": "PENDING_HASH", "original_title": "UNKNOWN (added during acquisition)",
        "original_publication_date": "UNKNOWN", "original_version": "UNKNOWN", "original_status": "UNKNOWN",
        "original_notes": "New official FISI source discovered by Playwright search and opened from the FISI archive listing.",
    },
    {
        "title": "RD 000609-2022-D-FISI: equivalency table Plan 2014 to Plan 2018",
        "url": "https://sistemas.unmsm.edu.pe/site/resoluciones-decanales/category/4-rd-2022?download=2522:rd-601-700&start=700",
        "source_page": "https://sistemas.unmsm.edu.pe/site/resoluciones-decanales/category/4-rd-2022?limit=20&start=700",
        "category": "plan_de_estudios", "publication_date": "2022-07-22", "version": "RD-000609-2022-D-FISI",
        "status": "HISTORICAL", "priority": "CRITICAL",
        "notes": "Official FISI archive title identifies a Plan 2014→2018 course-equivalency table. Historical transition evidence; do not use as a full Plan 2014 or 2018 curriculum.",
        "doc_id": "DOC-122", "document_type": "PDF", "audience": "UNDERGRADUATE", "academic_period": "Plan 2014→2018",
        "reported_http_status": "200", "reported_checked_on": "2026-09-29", "content_review": "CONTENT_REVIEWED",
        "checked_on": "2026-09-29", "access_review": "RETRIEVED", "review_note": "Downloaded from FISI official archive; table rows, operative basis, signatures and annex scope require visual verification.",
        "corpus_action": "REVIEW_BEFORE_INGEST", "action_reason": "Needed for historical migration/equivalency queries; not a current whole-plan or cohort assignment source.",
        "family_id": "fisi-systems-plan-2014-2018-equivalence", "relation_role": "EQUIVALENCY_RESOLUTION",
        "related_doc_ids": "DOC-121;DOC-120;EXTERNAL:PLAN-2014-EP-INGENIERIA-DE-SISTEMAS;EXTERNAL:PLAN-2018-EP-INGENIERIA-DE-SISTEMAS",
        "relationship_evidence": "Official FISI archive file title names table of equivalencies from Plan 2014 to Plan 2018.",
        "file_identity": "PENDING_HASH", "original_title": "UNKNOWN (added during acquisition)",
        "original_publication_date": "UNKNOWN", "original_version": "UNKNOWN", "original_status": "UNKNOWN",
        "original_notes": "New official FISI source discovered and followed in Playwright.",
    },
    {
        "title": "FISI programación de asignaturas — Ingeniería de Sistemas, Plan 2018",
        "url": "https://sistemas.unmsm.edu.pe/site/images/pdf/programacionAsignaturas_SISTEMAS_PLAN_2018.pdf",
        "source_page": "https://sistemas.unmsm.edu.pe/site/pregrado/ingenieria-de-sistemas",
        "category": "plan_de_estudios", "publication_date": "UNKNOWN", "version": "Plan 2018; programming report",
        "status": "UNKNOWN", "priority": "HIGH",
        "notes": "Official-host course-programming report. Not assumed to be the approved curriculum or complete course/prerequisite table.",
        "doc_id": "DOC-123", "document_type": "PDF", "audience": "UNDERGRADUATE", "academic_period": "UNKNOWN",
        "reported_http_status": "200", "reported_checked_on": "2026-09-29", "content_review": "CONTENT_REVIEWED",
        "checked_on": "2026-09-29", "access_review": "RETRIEVED", "review_note": "Playwright opened direct official PDF URL (HTTP 200/application/pdf); identify period, completeness and course-table extraction from pages.",
        "corpus_action": "REVIEW_BEFORE_INGEST", "action_reason": "Potential course offering aid only; verify period and do not substitute for an approved study plan.",
        "family_id": "fisi-systems-course-programming-plan-2018", "relation_role": "COURSE_PROGRAMMING_REPORT",
        "related_doc_ids": "DOC-121;DOC-122", "relationship_evidence": "Official FISI-host filename explicitly identifies Sistemas and Plan 2018.",
        "file_identity": "PENDING_HASH", "original_title": "UNKNOWN (added during acquisition)",
        "original_publication_date": "UNKNOWN", "original_version": "UNKNOWN", "original_status": "UNKNOWN",
        "original_notes": "Official FISI-host PDF discovered from Playwright search; direct PDF opened in Playwright.",
    },
    {
        "title": "FISI programación de asignaturas — Ingeniería de Software, Plan 2018",
        "url": "https://sistemas.unmsm.edu.pe/site/images/pdf/programacionAsignaturas_SOFTWARE_PLAN_2018.pdf",
        "source_page": "https://sistemas.unmsm.edu.pe/site/pregrado/ingenieria-de-software",
        "category": "plan_de_estudios", "publication_date": "UNKNOWN", "version": "Plan 2018; programming report",
        "status": "UNKNOWN", "priority": "HIGH",
        "notes": "Official-host course-programming report. Not assumed to be the approved curriculum or complete course/prerequisite table.",
        "doc_id": "DOC-124", "document_type": "PDF", "audience": "UNDERGRADUATE", "academic_period": "UNKNOWN",
        "reported_http_status": "200", "reported_checked_on": "2026-09-29", "content_review": "CONTENT_REVIEWED",
        "checked_on": "2026-09-29", "access_review": "RETRIEVED", "review_note": "Official FISI-host URL verified via Playwright; identify period, completeness and course-table extraction from pages.",
        "corpus_action": "REVIEW_BEFORE_INGEST", "action_reason": "Potential course offering aid only; verify period and do not substitute for an approved study plan.",
        "family_id": "fisi-software-course-programming-plan-2018", "relation_role": "COURSE_PROGRAMMING_REPORT",
        "related_doc_ids": "", "relationship_evidence": "Official FISI-host filename explicitly identifies Software and Plan 2018.",
        "file_identity": "PENDING_HASH", "original_title": "UNKNOWN (added during acquisition)",
        "original_publication_date": "UNKNOWN", "original_version": "UNKNOWN", "original_status": "UNKNOWN",
        "original_notes": "Official FISI-host PDF surfaced in the FISI plan search; downloaded from the named file URL.",
    },
    {
        "title": "FISI programación de asignaturas — Ciencia de la Computación, Plan 2023",
        "url": "https://sistemas.unmsm.edu.pe/site/images/pdf/programacionAsignaturas_CIENCIA_DE_LA_COMPUTACION_PLAN_2023.pdf",
        "source_page": "https://sistemas.unmsm.edu.pe/site/pregrado/ep-ciencia-de-la-computacion",
        "category": "plan_de_estudios", "publication_date": "UNKNOWN", "version": "Plan 2023; programming report",
        "status": "UNKNOWN", "priority": "HIGH",
        "notes": "Official-host course-programming report; Google discovery snippet identifies Plan 2023 and the EP. Not an approval instrument or complete plan by itself.",
        "doc_id": "DOC-125", "document_type": "PDF", "audience": "UNDERGRADUATE", "academic_period": "2023",
        "reported_http_status": "200", "reported_checked_on": "2026-09-29", "content_review": "CONTENT_REVIEWED",
        "checked_on": "2026-09-29", "access_review": "RETRIEVED", "review_note": "Official FISI-host PDF opened through Playwright; verify whether report is a current timetable or curriculum and whether prerequisites are complete.",
        "corpus_action": "REVIEW_BEFORE_INGEST", "action_reason": "Potential course offering aid only; verify period and do not substitute for an approved study plan.",
        "family_id": "fisi-computing-course-programming-plan-2023", "relation_role": "COURSE_PROGRAMMING_REPORT",
        "related_doc_ids": "", "relationship_evidence": "Official FISI-host filename explicitly identifies Ciencia de la Computación and Plan 2023.",
        "file_identity": "PENDING_HASH", "original_title": "UNKNOWN (added during acquisition)",
        "original_publication_date": "UNKNOWN", "original_version": "UNKNOWN", "original_status": "UNKNOWN",
        "original_notes": "Official FISI-host PDF discovered through Playwright search; opened via its official URL.",
    },
    {
        "title": "Directiva de acreditación de idioma extranjero en Pregrado UNMSM",
        "url": "https://viceacademico.unmsm.edu.pe/wp-content/uploads/2024/11/DIRECTIVA-DE-ACREDITACI%C3%93N-DE-IDIOMA-EXTRANJERO-EN-PREGRADO_UNMSM.pdf",
        "source_page": "https://viceacademico.unmsm.edu.pe/?page_id=8731",
        "category": "grados_titulos", "publication_date": "UNKNOWN", "version": "Directiva 2024 (resolution/date to inspect)",
        "status": "POSSIBLY_CURRENT", "priority": "CRITICAL",
        "notes": "Listed by the official VRAP normative page; acquire clauses defining language level, proof, exceptions, and transition scope.",
        "doc_id": "DOC-126", "document_type": "PDF", "audience": "UNDERGRADUATE", "academic_period": "UNKNOWN",
        "reported_http_status": "200", "reported_checked_on": "2026-09-29", "content_review": "CONTENT_REVIEWED",
        "checked_on": "2026-09-29", "access_review": "RETRIEVED", "review_note": "Attachment linked directly from official VRAP Normativa page; inspect approval/date and cohort clauses.",
        "corpus_action": "REVIEW_BEFORE_INGEST", "action_reason": "Potential current degree requirement; verify applicability by cohort and relation to current Grados y Títulos rule.",
        "family_id": "unmsm-language-requirement", "relation_role": "LANGUAGE_REQUIREMENT_DIRECTIVE",
        "related_doc_ids": "DOC-083;DOC-084;DOC-087", "relationship_evidence": "VRAP Normativa page lists Directiva de acreditación de idioma extranjero en Pregrado.",
        "file_identity": "PENDING_HASH", "original_title": "UNKNOWN (added during acquisition)",
        "original_publication_date": "UNKNOWN", "original_version": "UNKNOWN", "original_status": "UNKNOWN",
        "original_notes": "Direct attachment discovered and source-page link verified in Playwright.",
    },
    {
        "title": "Directiva general de investigación, tesis y trabajo de suficiencia para grados/títulos (RR 00744-R-20)",
        "url": "https://viceacademico.unmsm.edu.pe/wp-content/uploads/2020/09/Directiva-General-para-trabajo-de-investigaci%C3%B3n-para-Bachiller-tesis-o-trabajo-de-suficiencia-para-t%C3%ADtulo-profesional.-RR-N%C2%BA-00744-R-20-del-18-de-febrero-del-2020..pdf",
        "source_page": "https://viceacademico.unmsm.edu.pe/?page_id=8731",
        "category": "grados_titulos", "publication_date": "2020-02-18", "version": "RR-00744-R-20",
        "status": "POSSIBLY_CURRENT", "priority": "HIGH",
        "notes": "VRAP list identifies a general directive for bachelor's research work and professional thesis/proficiency work; verify amendments and applicability to current degree regulation.",
        "doc_id": "DOC-127", "document_type": "PDF", "audience": "UNDERGRADUATE", "academic_period": "UNKNOWN",
        "reported_http_status": "200", "reported_checked_on": "2026-09-29", "content_review": "CONTENT_REVIEWED",
        "checked_on": "2026-09-29", "access_review": "RETRIEVED", "review_note": "Actual attachment linked on official VRAP page; approval and relation to current degree requirements require clause review.",
        "corpus_action": "REVIEW_BEFORE_INGEST", "action_reason": "Potential research completion requirements; not sufficient alone to define cohort graduation checklist.",
        "family_id": "unmsm-degree-research-work", "relation_role": "RESEARCH_WORK_DIRECTIVE",
        "related_doc_ids": "DOC-083;DOC-084;DOC-126", "relationship_evidence": "Official VRAP Normativa page title and linked file name cite RR 00744-R-20.",
        "file_identity": "PENDING_HASH", "original_title": "UNKNOWN (added during acquisition)",
        "original_publication_date": "UNKNOWN", "original_version": "UNKNOWN", "original_status": "UNKNOWN",
        "original_notes": "Direct attachment discovered and source-page link verified in Playwright.",
    },
    {
        "title": "Acta Consejo de Facultad Virtual N.° 23, Sesión Ordinaria 13 (2021-07-20)",
        "url": "https://sistemas.unmsm.edu.pe/site/rd?task=download.send&id=145&catid=6&m=0",
        "source_page": "https://sistemas.unmsm.edu.pe/site/rd?task=download.send&id=145&catid=6&m=0",
        "category": "plan_de_estudios", "publication_date": "2021-07-20", "version": "Acta CF Virtual 23, Sesión Ordinaria 13",
        "status": "HISTORICAL", "priority": "CRITICAL",
        "notes": "Official FISI council minutes; Playwright PDF title/date indicate agenda on new Systems curriculum. Inspect action items for 2009 migration/equivalency decisions and avoid unnecessary ingestion of attendee personal data.",
        "doc_id": "DOC-128", "document_type": "PDF", "audience": "UNDERGRADUATE", "academic_period": "2021",
        "reported_http_status": "200", "reported_checked_on": "2026-09-29", "content_review": "CONTENT_REVIEWED",
        "checked_on": "2026-09-29", "access_review": "RETRIEVED", "review_note": "Playwright direct PDF status 200/application/pdf; rendered title says Acta CF Virtual 23, Session 13, 20 July 2021. Text/action items need clause/page verification.",
        "corpus_action": "REVIEW_BEFORE_INGEST", "action_reason": "Primary historical deliberation evidence; verify operative decision and redact/minimize participant personal data in any RAG extract.",
        "family_id": "fisi-systems-plan-transition-2009", "relation_role": "COUNCIL_MINUTES_CANDIDATE",
        "related_doc_ids": "DOC-118;EXTERNAL:RD-000510-D-FISI-19;EXTERNAL:RR-00721-R-20",
        "relationship_evidence": "Playwright rendered official FISI PDF; page 1 agenda identifies commission designing the new Systems curriculum. Resolution/approval clauses need text review.",
        "file_identity": "PENDING_HASH", "original_title": "UNKNOWN (added during acquisition)",
        "original_publication_date": "UNKNOWN", "original_version": "UNKNOWN", "original_status": "UNKNOWN",
        "original_notes": "Official FISI council minutes PDF discovered through FISI files and opened in Playwright.",
    },
    {
        "title": "Acta Consejo de Facultad Virtual N.° 24, Sesión Ordinaria 14 (2021-07-27)",
        "url": "https://sistemas.unmsm.edu.pe/site/rd?task=download.send&id=146&catid=6&m=0",
        "source_page": "https://sistemas.unmsm.edu.pe/site/rd?task=download.send&id=146&catid=6&m=0",
        "category": "plan_de_estudios", "publication_date": "2021-07-27", "version": "Acta CF Virtual 24, Sesión Ordinaria 14",
        "status": "HISTORICAL", "priority": "HIGH",
        "notes": "Official FISI council minutes; page 1 agenda concerns a proposed new EP Ingeniería de Software plan. Inspect whether it includes 2009-to-2018 migration/table decisions; not an operative regulation by itself.",
        "doc_id": "DOC-129", "document_type": "PDF", "audience": "UNDERGRADUATE", "academic_period": "2021",
        "reported_http_status": "200", "reported_checked_on": "2026-09-29", "content_review": "CONTENT_REVIEWED",
        "checked_on": "2026-09-29", "access_review": "RETRIEVED", "review_note": "Playwright direct PDF status 200/application/pdf; rendered title says Acta CF Virtual 24, Session 14, 27 July 2021; page 1 agenda is EPISW curriculum commission.",
        "corpus_action": "REVIEW_BEFORE_INGEST", "action_reason": "Historical faculty minutes may clarify approval and migration chronology; verify text, separate proposal from adopted act, and redact unnecessary personal data.",
        "family_id": "fisi-software-plan-transition", "relation_role": "COUNCIL_MINUTES_CANDIDATE",
        "related_doc_ids": "", "relationship_evidence": "Playwright rendered p.1 agenda: 'PROPUESTA - COMISION DE DISEÑO DEL NUEVO PLAN DE ESTUDIOS EPISW'.",
        "file_identity": "PENDING_HASH", "original_title": "UNKNOWN (added during acquisition)",
        "original_publication_date": "UNKNOWN", "original_version": "UNKNOWN", "original_status": "UNKNOWN",
        "original_notes": "Official FISI council minutes PDF discovered through FISI files and opened in Playwright.",
    },
    {
        "title": "Acta Consejo de Facultad Virtual N.° 17, Sesión Ordinaria 12 (2020-09-22)",
        "url": "https://sistemas.unmsm.edu.pe/site/rd?task=download.send&id=16&catid=5&m=0",
        "source_page": "https://sistemas.unmsm.edu.pe/site/rd?task=download.send&id=16&catid=5&m=0",
        "category": "plan_de_estudios", "publication_date": "2020-09-22", "version": "Acta CF Virtual 17, Sesión Ordinaria 12",
        "status": "HISTORICAL", "priority": "CRITICAL",
        "notes": "Official FISI council minutes cited by the plan-2009 notice. The notice reports approval of Plan 2009 validity through 2021-II; the acta's extracted item/operative record must be checked before asserting that exact decision.",
        "doc_id": "DOC-130", "document_type": "PDF", "audience": "UNDERGRADUATE", "academic_period": "2020",
        "reported_http_status": "200", "reported_checked_on": "2026-09-29", "content_review": "CONTENT_REVIEWED",
        "checked_on": "2026-09-29", "access_review": "RETRIEVED", "review_note": "Playwright direct attachment status 200/application/pdf, rendered page 1 title/date matches the FISI 2009 notice reference; inspect complete minutes for the plan resolution and result.",
        "corpus_action": "REVIEW_BEFORE_INGEST", "action_reason": "Critical primary evidence for notice-reported transition; meeting minutes include personal names, so restrict excerpts to the relevant agenda/action and redact unrelated attendees.",
        "family_id": "fisi-systems-plan-transition-2009", "relation_role": "COUNCIL_MINUTES_CANDIDATE",
        "related_doc_ids": "DOC-118;DOC-128;EXTERNAL:RD-000510-D-FISI-19;EXTERNAL:RR-00721-R-20",
        "relationship_evidence": "Playwright PDF viewer title shows Acta Consejo de Facultad Virtual No. 17, Sesión Ordinaria 12, 22 Sep 2020; page 1 screenshot. Full-text item-specific approval yet to be located in extracted pages.",
        "file_identity": "PENDING_HASH", "original_title": "UNKNOWN (added during acquisition)",
        "original_publication_date": "UNKNOWN", "original_version": "UNKNOWN", "original_status": "UNKNOWN",
        "original_notes": "Official FISI direct attachment linked from site; date/session match is directly rendered in Playwright.",
    },
]

FIELDS = [
    "doc_id", "title", "exact_source_url", "discovery_page", "retrieval_date",
    "local_path", "file_type", "size_bytes", "sha256", "download_validation",
    "extraction_path", "extracted_pages", "ocr_need", "manual_table_review",
    "extraction_notes",
]


def load_inventory() -> tuple[list[str], list[dict[str, str]]]:
    with INVENTORY.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def extract_pages(path: Path) -> tuple[list[str], str]:
    run = subprocess.run(
        ["mutool", "draw", "-F", "txt", "-o", "-", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    raw = run.stdout.decode("utf-8", errors="replace")
    pages = raw.split("\f")
    while pages and not pages[-1].strip():
        pages.pop()
    info = subprocess.run(
        ["mutool", "info", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    info_text = info.stdout.decode("utf-8", errors="replace")
    match = re.search(r"Pages:\s+(\d+)", info_text)
    page_count = int(match.group(1)) if match else len(pages)
    if len(pages) < page_count:
        pages.extend([""] * (page_count - len(pages)))
    pages = pages[:page_count]
    warning = run.stderr.decode("utf-8", errors="replace").strip()
    if any(not p.strip() for p in pages):
        warning = (warning + " | " if warning else "") + "one or more image-only/empty-text pages detected"
    return pages, warning


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def main() -> None:
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    inv_fields, records = load_inventory()
    existing_ids = {row["doc_id"] for row in records}
    for addition in ADDITIONS:
        if addition["doc_id"] not in existing_ids:
            for field in inv_fields:
                addition.setdefault(field, "")
            addition["ingestion_decision"] = "REVIEW_REQUIRED"
            addition["applicability"] = "limited to a population"
            addition["duplicate_group"] = "UNKNOWN_NO_LOCAL_BYTES"
            addition["text_comparison"] = "NOT_POSSIBLE_NO_LOCAL_EXTRACTED_TEXT"
            addition["verified_source_urls"] = f"{addition['url']} | {addition['source_page']}"
            records.append(addition)
            existing_ids.add(addition["doc_id"])
    by_id = {row["doc_id"]: row for row in records}
    manifest_rows: list[dict[str, str]] = []
    hashes: dict[str, list[str]] = defaultdict(list)
    extracted_by_id: dict[str, str] = {}
    acquisition_date = f"{date.today().isoformat()} (America/Lima)"

    for path in sorted(ORIGINALS.iterdir()):
        if not path.is_file():
            continue
        doc_id = DOC_BY_FILE.get(path.name)
        if not doc_id or doc_id not in by_id:
            raise SystemExit(f"No inventory mapping for {path.name}")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        hashes[digest].append(path.name)
        row = by_id[doc_id]
        is_pdf = data.startswith(b"%PDF-")
        if not is_pdf:
            validation = f"INVALID_PDF_SIGNATURE:{data[:30]!r}"
            pages, warnings = [], ""
        else:
            validation = "VALID_PDF_SIGNATURE"
            pages, warnings = extract_pages(path)
        extraction = EXTRACTED / f"{path.stem}.txt"
        extraction_text = "\n\n".join(f"===== PAGE {i+1} =====\n{page.strip()}" for i, page in enumerate(pages))
        extraction.write_text(extraction_text + "\n", encoding="utf-8")
        extracted_by_id[doc_id] = normalized(extraction_text)
        page_texts = [p.strip() for p in pages]
        empty_pages = [str(i + 1) for i, p in enumerate(page_texts) if not p]
        ocr = "REQUIRED_PAGES_" + ",".join(empty_pages) if empty_pages else "NOT_INDICATED_BY_EMPTY_TEXT; VISUALLY_CHECK_SCANS"
        terms = ("equivalenc", "prerrequis", "crédit", "codigo", "código", "asignatura", "tabla", "ciclo")
        needs_table = "YES_MANUAL" if any(term in extraction_text.casefold() for term in terms) else "NO_TABLE_CUE_DETECTED"
        note_parts = ["Per-page text extracted with MuPDF; page labels inserted."]
        if warnings:
            note_parts.append("MuPDF warning: " + warnings.replace("\n", " "))
        if empty_pages:
            note_parts.append("No text extracted on pages " + ",".join(empty_pages) + "; OCR required.")
        if needs_table.startswith("YES"):
            note_parts.append("Course/policy table terms detected; verify layout, footnotes, and row associations against rendered pages.")
        row["local_file_path"] = str(path.relative_to(ROOT))
        row["sha256"] = digest
        row["text_comparison"] = "BYTE_HASHED_NO_EXACT_DUPLICATE_IN_ACQUIRED_SET; extracted-text comparison recorded separately"
        row["duplicate_group"] = "NO_BYTE_IDENTICAL_FILE_IN_ACQUIRED_SET"
        row["extraction_quality"] = "TEXT_EXTRACTED_PAGE_LABELS; OCR_REQUIRED" if empty_pages else "TEXT_EXTRACTED_PAGE_LABELS; VISUAL_QA_REQUIRED"
        row["manual_verification_required"] = "; ".join(note_parts[1:]) or "Visual review required for signatures, footnotes, and page-level correctness."
        row["file_identity"] = f"SHA256:{digest}"
        row["access_review"] = "RETRIEVED"
        row["review_note"] = (row.get("review_note", "") + " Local source file acquired, PDF signature validated, SHA-256 recorded, and page-labelled extraction written; see sources/source_manifest.csv.").strip()
        if row.get("url", "").startswith(("https://sistemas.unmsm.edu.pe/", "https://viceacademico.unmsm.edu.pe/")):
            validation += "; CURL_TLS_CHAIN_NOT_VALIDATED (Playwright official source/link was separately verified)"
        manifest_rows.append({
            "doc_id": doc_id,
            "title": row["title"],
            "exact_source_url": row["url"],
            "discovery_page": row["source_page"],
            "retrieval_date": acquisition_date,
            "local_path": str(path.relative_to(ROOT)),
            "file_type": "PDF" if is_pdf else "INVALID/UNKNOWN",
            "size_bytes": str(len(data)),
            "sha256": digest,
            "download_validation": validation,
            "extraction_path": str(extraction.relative_to(ROOT)),
            "extracted_pages": str(len(pages)),
            "ocr_need": ocr,
            "manual_table_review": needs_table,
            "extraction_notes": " ".join(note_parts),
        })

    vrp_matricula_url = "https://viceacademico.unmsm.edu.pe/wp-content/uploads/2026/02/Reglamento-General-de-Matr%C3%ADcula.pdf"
    for doc_id in ("DOC-002", "DOC-005"):
        row = by_id[doc_id]
        existing_urls = [u.strip() for u in row.get("verified_source_urls", "").split("|") if u.strip()]
        if vrp_matricula_url not in existing_urls:
            existing_urls.append(vrp_matricula_url)
        row["verified_source_urls"] = " | ".join(existing_urls)
    by_id["DOC-002"]["relationship_evidence"] = (
        (by_id["DOC-002"].get("relationship_evidence", "") + " ").strip()
        + "VRAP combined PDF DOC-079 pages 3–20 has normalized extracted text identical to this 18-page annex (1.00000); source URLs retained, whole-file hashes differ."
    )
    by_id["DOC-005"]["relationship_evidence"] = (
        (by_id["DOC-005"].get("relationship_evidence", "") + " ").strip()
        + "VRAP combined PDF DOC-079 pages 1–2 has normalized extracted text identical to this resolution (1.00000); source URLs retained, whole-file hashes differ."
    )
    by_id["DOC-121"]["review_note"] += " Retrieved source file is only 1 page although clause 1 specifies 96 folios of annex; curriculum/plan annex is not present in this file."
    by_id["DOC-121"]["relationship_evidence"] = "RD 000163-2023-D-FISI p.1 clauses 1 and 3: approves Programa Curricular 2023 with 96-folio annex and sends resolution to Rectorado for ratification."
    by_id["DOC-121"]["manual_verification_required"] = "Acquire and validate missing 96-folio curricular annex; no course/credit/prerequisite claims from the resolution page alone."
    by_id["DOC-122"]["review_note"] += " Retrieved source file is only 1 page although clause 1 says the equivalency table is 5 folios; course table is absent."
    by_id["DOC-122"]["relationship_evidence"] = "RD 000609-2022-D-FISI p.1 recitals identify RR 02137-R-15 Plan 2014, RR 07026-R-17 Plan 2018, RR 06615-R-18 and RR 01529-R-19 amendments; operative clause 1 approves 2014→2018 table in five folios; clause 3 elevates for ratification."
    by_id["DOC-122"]["manual_verification_required"] = "Acquire and validate missing five-folio equivalency table; no course-by-course migration answer from this one-page resolution."
    by_id["DOC-127"]["manual_verification_required"] = "OCR pages 3–18; inspect image-only requirements, signatures, footnotes and cohort scope before citing."
    by_id["DOC-070"]["manual_verification_required"] = "OCR all 84 scanned pages; manually verify Statute Article 189 and amendment history before current standing answers."
    for doc_id in ("DOC-128", "DOC-129", "DOC-130"):
        by_id[doc_id]["manual_verification_required"] = "Use only the plan-related, page-cited excerpt; redact participant/student identifiers and unrelated personal data before RAG ingestion."
    by_id["DOC-130"]["review_note"] = (
        "Playwright rendered official Acta CF Virtual No. 17, ordinary session 12, dated 2020-09-22. Extracted minutes p.2–5 show immediate closure proposal rejected and closure from 2022-I accepted 8–1; RR 00698-R-20 is cited as an existing 2009–2014 equivalency approval."
    )
    by_id["DOC-118"]["review_note"] = (
        "Official FISI notice says Plan 2009 valid through 2021-II and gives cycle-group routes. DOC-130 p.5 independently supports end from 2022-I; the acquired Council minutes do not verify the notice's cycle-group routes."
    )
    by_id["DOC-126"]["publication_date"] = "2024-11-26"
    by_id["DOC-126"]["version"] = "RR-014041-2024-R/UNMSM"
    by_id["DOC-126"]["notes"] = (
        "RR 014041-2024-R approves a seven-folio language-accreditation directive. Art.3 covers students who began studies from the effective Ley 30220 period; Arts.4(g) and 5.4 set basic level and accept passed language courses within the assigned curriculum."
    )
    by_id["DOC-126"]["review_note"] = (
        "Extracted and page-labelled 9-page resolution/directive PDF: RR p.2 approves annex, directive pp.3–9. Applicability is limited by Art.3; language course equivalence is plan-specific."
    )
    by_id["DOC-127"]["review_note"] = (
        "RR 00744-R-20 pp.1–2 approve the 16-folio directive. Page 1 states scope for students entering from 2016 or incorporated into plans of that reference year; annex pages 3–18 are image-only and need OCR."
    )
    by_id["DOC-129"]["review_note"] = (
        "Extracted minutes pp.2–3 describe the proposed 2009→2018/2014 cycle migration and 2009→2018 table; both were explicitly left pending approval at this meeting."
    )
    by_id["DOC-128"]["review_note"] = "Extracted DOC-128 p.4 records a request for an extraordinary Faculty Council to consider the 2009→2018 equivalency table; request is not approval. Use only a redacted excerpt for RAG."
    by_id["DOC-123"]["publication_date"] = "2026-01-08 (print date)"
    by_id["DOC-123"]["academic_period"] = "2026-0"
    by_id["DOC-123"]["version"] = "Plan 2018; 2026-0 course-programming report"
    by_id["DOC-123"]["status"] = "TEMPORARY"
    by_id["DOC-124"]["publication_date"] = "2026-01-08 (print date)"
    by_id["DOC-124"]["academic_period"] = "2026-0"
    by_id["DOC-124"]["version"] = "Plan 2018; 2026-0 course-programming report"
    by_id["DOC-124"]["status"] = "TEMPORARY"
    by_id["DOC-125"]["publication_date"] = "2026-01-08 (print date)"
    by_id["DOC-125"]["academic_period"] = "2026-0"
    by_id["DOC-125"]["version"] = "Plan 2023; 2026-0 course-programming report"
    by_id["DOC-125"]["status"] = "TEMPORARY"

    # Exact duplicate groups are byte-hash based only. Keep all records/source URLs.
    hash_group = 0
    for digest, filenames in hashes.items():
        if len(filenames) > 1:
            hash_group += 1
            ids = [DOC_BY_FILE[name] for name in filenames]
            urls = [by_id[doc_id]["url"] for doc_id in ids]
            group = f"EXACT-{hash_group:03d}"
            for doc_id, url in zip(ids, urls):
                by_id[doc_id]["duplicate_group"] = group + "; all source URLs retained"

    # Near-text component matches are not byte-identical files and keep their document roles.
    by_id["DOC-079"]["text_comparison"] = "COMBINED_PDF_COMPONENTS_MATCH_DOC-005_PP1-2_AND_DOC-002_PP1-18; whole-file bytes differ"
    by_id["DOC-002"]["text_comparison"] = "NORMALIZED_TEXT_IDENTICAL_TO_DOC-079_PP3-20 (1.00000); whole-file hashes differ"
    by_id["DOC-005"]["text_comparison"] = "NORMALIZED_TEXT_IDENTICAL_TO_DOC-079_PP1-2 (1.00000); whole-file hashes differ"
    by_id["DOC-083"]["text_comparison"] = "NEAR_TEXT_CANDIDATE_DOC-084; normalized whole-package similarity 0.8521; distinct 2022 transition amendment"
    by_id["DOC-084"]["text_comparison"] = "NEAR_TEXT_CANDIDATE_DOC-083; normalized whole-package similarity 0.8521; retain separate editions"
    by_id["DOC-121"]["extraction_quality"] = "PARTIAL_RESOLUTION_ONLY_96_FOLIO_ANNEX_ABSENT"
    by_id["DOC-121"]["content_review"] = "CONTENT_REVIEWED_PARTIAL_ANNEX_MISSING"
    by_id["DOC-122"]["extraction_quality"] = "PARTIAL_RESOLUTION_ONLY_5_FOLIO_TABLE_ABSENT"
    by_id["DOC-122"]["content_review"] = "CONTENT_REVIEWED_PARTIAL_ANNEX_MISSING"
    by_id["DOC-079"]["review_note"] = "Official VRAP Normativa page link acquired and verified; PDF contains RR 002642-2026 pp.1–2 plus the 18-page regulation pp.3–20. Its components are text-identical to DOC-005/DOC-002; source URL preserved."
    by_id["DOC-120"]["review_note"] = "Attachment downloaded from official Gob.pe record, PDF signature validated; Playwright visual review and per-page text extraction confirm EP Ingeniería de Sistemas and two corrected equivalency rows. Local hash and extraction recorded; manual second-person table QA remains required."
    by_id["DOC-127"]["content_review"] = "CONTENT_REVIEWED_PARTIAL_OCR_REQUIRED"
    by_id["DOC-070"]["content_review"] = "OCR_REQUIRED_ALL_PAGES"
    by_id["DOC-053"]["content_review"] = "OCR_REQUIRED"
    by_id["DOC-054"]["content_review"] = "OCR_REQUIRED"
    by_id["DOC-019"]["content_review"] = "OCR_REQUIRED"
    by_id["DOC-020"]["content_review"] = "OCR_REQUIRED"

    # Compare only documents already selected as meaningful candidate editions.
    pairs = [("DOC-083", "DOC-084"), ("DOC-072", "DOC-096")]
    comparison_lines = [
        "# Extracted-text comparison notes",
        "",
        "Normalized whitespace/case comparisons are candidate signals. Exact page-subdocument matches are reported separately from whole-file hashes.",
        "Only locally extracted text is compared; differences in annexes, amendment clauses, signatures, tables, and scans require visual review.",
        "",
    ]
    for left, right in pairs:
        if left in extracted_by_id and right in extracted_by_id:
            ratio = SequenceMatcher(None, extracted_by_id[left], extracted_by_id[right]).ratio()
            comparison_lines.append(f"- {left} vs {right}: similarity={ratio:.4f}; retain as separate records pending clause/page diff.")
        else:
            comparison_lines.append(f"- {left} vs {right}: NOT_COMPARED; one or both candidate files are not locally present.")
    if "DOC-002" in extracted_by_id and "DOC-079" in extracted_by_id and "DOC-005" in extracted_by_id:
        def page_text(doc_id: str) -> list[str]:
            source = next(ROOT / row["local_file_path"] for row in records if row["doc_id"] == doc_id)
            extracted = (EXTRACTED / f"{source.stem}.txt").read_text(encoding="utf-8")
            return re.split(r"===== PAGE \d+ =====", extracted)[1:]

        compare_pairs = [("DOC-005", page_text("DOC-079")[:2], "DOC-079 p.1–2"),
                         ("DOC-002", page_text("DOC-079")[2:], "DOC-079 p.3–20")]
        for standalone_id, bundled_pages, label in compare_pairs:
            standalone = " ".join(page_text(standalone_id)).casefold()
            bundled = " ".join(bundled_pages).casefold()
            standalone = re.sub(r"\s+", " ", standalone).strip()
            bundled = re.sub(r"\s+", " ", bundled).strip()
            ratio = SequenceMatcher(None, standalone, bundled).ratio()
            comparison_lines.append(f"- {standalone_id} vs {label}: normalized extracted text similarity={ratio:.5f}; byte hashes remain distinct because DOC-079 is a 2-page RR plus 18-page annex bundle. Keep DOC-005 (approval) and DOC-002 (annex) as distinct logical documents; retain the DOC-079 URL as a matching source for both components.")
    else:
        comparison_lines.append("- Enrollment bundle comparison DOC-002/DOC-005 vs DOC-079: not complete; one or more files missing.")
    (ROOT / "sources/extracted/text_comparisons.md").write_text("\n".join(comparison_lines) + "\n", encoding="utf-8")

    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(manifest_rows)
    with INVENTORY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=inv_fields)
        writer.writeheader()
        writer.writerows(records)
    print(f"Validated/extracted {len(manifest_rows)} files; exact duplicate groups={hash_group}")
    print(f"Wrote {MANIFEST.relative_to(ROOT)} and updated {INVENTORY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
