from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Callable

from sum_contracts.models import Block, Page, ServiceError

from .ports import Extractor


def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).replace("\x00", "").replace("\r\n", "\n").strip()


class TextExtractor:
    def page_count(self, source: Path) -> int:
        return 1

    def extract(self, source: Path, first: int, last: int, options: dict) -> list[Page]:
        try:
            text = normalize(source.read_text(encoding="utf-8-sig"))
        except UnicodeError:
            raise ServiceError(
                "ARCHIVO_INVALIDO", "El texto debe usar codificación UTF-8."
            ) from None
        blocks = []
        for i, paragraph in enumerate(re.split(r"\n\s*\n", text)):
            # Keep tokenizer and chunk construction memory bounded for long TXT files.
            for start in range(0, len(paragraph), 32000):
                block = paragraph[start : start + 32000].strip()
                if block:
                    blocks.append(
                        Block(block, locator=f"párrafo {i + 1}, parte {start // 32000 + 1}")
                    )
        return [Page(1, tuple(blocks))]


class PdfExtractor:
    def __init__(self, image: bool = False):
        self.image = image

    def _open(self, source: Path):
        import pymupdf

        doc = pymupdf.open(source)
        if self.image:
            if doc[0].rect.width * doc[0].rect.height > 30_000_000:
                doc.close()
                raise ServiceError(
                    "ARCHIVO_INVALIDO", "La imagen supera el tamaño de procesamiento permitido."
                )
            content = doc.convert_to_pdf()
            doc.close()
            doc = pymupdf.open(stream=content, filetype="pdf")
        if doc.needs_pass:
            doc.close()
            raise ServiceError("ARCHIVO_INVALIDO", "El PDF está protegido por contraseña.")
        return doc

    def page_count(self, source: Path) -> int:
        with self._open(source) as doc:
            return doc.page_count

    def extract(self, source: Path, first: int, last: int, options: dict) -> list[Page]:
        pages = []
        with self._open(source) as doc:
            for number in range(first, last):
                page = doc[number]
                raw = page.get_text("text", sort=True)
                ocr = len(raw.strip()) < 30 or raw.count("\ufffd") > max(1, len(raw) // 20)
                textpage = None
                if ocr:
                    # Bound rendered pixel count before invoking OCR.
                    if page.rect.width * page.rect.height * (200 / 72) ** 2 > 30_000_000:
                        raise ServiceError(
                            "ARCHIVO_INVALIDO", "La página supera el tamaño permitido para OCR."
                        )
                    try:
                        language = "spa+eng" if options["idioma"] == "es-en" else "spa"
                        textpage = page.get_textpage_ocr(language=language, dpi=200, full=True)
                    except Exception:
                        raise ServiceError(
                            "OCR_NO_DISPONIBLE", "No se pudo reconocer el texto en español."
                        ) from None
                table_blocks, table_rects = [], []
                if options["tipo_documento"] == "plan_estudios":
                    try:
                        tables = page.find_tables().tables
                        for index, table in enumerate(tables):
                            rows = table.extract()
                            if not rows or not any(any(cell for cell in row) for row in rows):
                                raise ServiceError(
                                    "CALIDAD_TABLA", "Una tabla requiere revisión de extracción."
                                )
                            table_rects.append(table.bbox)
                            header = rows[0]
                            for row_number, row in enumerate(rows):
                                cells = [
                                    f"{normalize(str(header[col] or f'Columna {col + 1}'))}: {normalize(str(cell or ''))}"
                                    for col, cell in enumerate(row)
                                ]
                                table_blocks.append(
                                    Block(
                                        " | ".join(cells),
                                        "table",
                                        f"tabla {index + 1}, fila {row_number + 1}",
                                    )
                                )
                        if ocr:
                            # OCR alone cannot certify row/column alignment in study plans.
                            raise ServiceError(
                                "CALIDAD_TABLA", "El plan escaneado requiere revisión de tablas."
                            )
                    except ServiceError:
                        raise
                    except Exception:
                        raise ServiceError(
                            "CALIDAD_TABLA", "No se pudo conservar la estructura de las tablas."
                        ) from None
                blocks = []
                for i, item in enumerate(page.get_text("blocks", sort=True, textpage=textpage)):
                    if len(item) > 6 and item[6] != 0:
                        continue
                    x0, y0, x1, y1, text = item[:5]
                    inside_table = any(
                        x0 >= a - 2 and y0 >= b - 2 and x1 <= c + 2 and y1 <= d + 2
                        for a, b, c, d in table_rects
                    )
                    if not inside_table and normalize(text):
                        blocks.append(Block(normalize(text), locator=f"bloque {i + 1}"))
                blocks.extend(table_blocks)
                pages.append(Page(number + 1, tuple(blocks), ocr))
        return pages


class ExtractorRegistry:
    def __init__(self, factories: dict[str, Callable[[], Extractor]] | None = None):
        self.factories = factories or {
            "application/pdf": PdfExtractor,
            "image/png": lambda: PdfExtractor(image=True),
            "image/jpeg": lambda: PdfExtractor(image=True),
            "text/plain": TextExtractor,
        }

    def resolve(self, mime: str) -> Extractor:
        try:
            return self.factories[mime]()
        except KeyError:
            raise ServiceError(
                "FORMATO_NO_ADMITIDO", "No existe un extractor para este formato."
            ) from None


def process_source(action: str, mime: str, path: str, first: int, last: int, options: dict):
    """Spawn-safe entry point: each process opens its own document."""
    try:
        extractor = ExtractorRegistry().resolve(mime)
        if action == "count":
            return extractor.page_count(Path(path))
        return [page.to_dict() for page in extractor.extract(Path(path), first, last, options)]
    except ServiceError:
        raise
    except Exception:
        raise ServiceError(
            "ARCHIVO_INVALIDO", "El archivo está dañado o no se puede leer."
        ) from None
