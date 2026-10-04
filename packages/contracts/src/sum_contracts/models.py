from __future__ import annotations

import dataclasses
from datetime import date
from enum import StrEnum
from typing import Any
from uuid import UUID

CONTRACT_VERSION = 1
INDEX_REQUESTED = "document/index.requested"


class ServiceError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(code, message, status)
        self.code, self.message, self.status = code, message, status

    def __str__(self) -> str:
        return self.message


class JobStopped(ServiceError):
    def __init__(self):
        super().__init__("TRABAJO_INACTIVO", "El trabajo fue cancelado o reemplazado.", 409)


class Status(StrEnum):
    QUEUED = "en_cola"
    PROCESSING = "procesando"
    COMPLETED = "completado"
    FAILED = "fallido"
    CANCELLED = "cancelado"


TERMINAL = {Status.COMPLETED, Status.FAILED, Status.CANCELLED}
STAGES = (
    "validando",
    "extrayendo",
    "fragmentando",
    "generando_vectores",
    "guardando",
    "publicando",
)
PRIORITIES = {"baja": -120, "normal": 0, "alta": 120}
DOCUMENT_TYPES = {"plan_estudios", "reglamento", "resolucion", "directiva", "otro"}


def require_uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ServiceError("IDENTIFICADOR_INVALIDO", "El identificador no es válido.") from None


@dataclasses.dataclass(frozen=True)
class Metadata:
    titulo: str
    tipo_documento: str
    institucion: str = "UNMSM"
    prioridad: str = "normal"
    es_prueba: bool = False
    idioma: str = "es"
    unidad_emisora: str | None = None
    codigo_documento: str | None = None
    fuente_url: str | None = None
    facultad: str | None = None
    carrera: str | None = None
    version_curricular: str | None = None
    fecha_emision: str | None = None
    vigente_desde: str | None = None
    vigente_hasta: str | None = None
    periodos_aplicables: tuple[str, ...] = ()
    relaciones: tuple[str, ...] = ()

    @classmethod
    def parse(cls, data: Any) -> Metadata:
        if not isinstance(data, dict):
            raise ServiceError("METADATOS_INVALIDOS", "Los metadatos deben ser un objeto JSON.")
        fields = {f.name for f in dataclasses.fields(cls)}
        if set(data) - fields:
            raise ServiceError(
                "METADATOS_INVALIDOS", "Los metadatos contienen campos desconocidos."
            )
        values = dict(data)
        for name in fields - {"periodos_aplicables", "relaciones", "es_prueba"}:
            value = values.get(name)
            if value is not None and (not isinstance(value, str) or len(value) > 2048):
                raise ServiceError("METADATOS_INVALIDOS", f"El campo '{name}' no es válido.")
            if isinstance(value, str):
                values[name] = value.strip()
        if "es_prueba" in values and type(values["es_prueba"]) is not bool:
            raise ServiceError("METADATOS_INVALIDOS", "El indicador de prueba no es válido.")
        if not values.get("titulo") or not values.get("tipo_documento"):
            raise ServiceError("METADATOS_INVALIDOS", "Se requieren título y tipo de documento.")
        if len(values["titulo"]) > 300 or values["tipo_documento"] not in DOCUMENT_TYPES:
            raise ServiceError("METADATOS_INVALIDOS", "El título o tipo de documento no es válido.")
        if values.get("prioridad", "normal") not in PRIORITIES:
            raise ServiceError("METADATOS_INVALIDOS", "La prioridad debe ser alta, normal o baja.")
        if values.get("idioma", "es") not in {"es", "es-en"}:
            raise ServiceError(
                "IDIOMA_NO_ADMITIDO", "Se admite español o contenido bilingüe español-inglés."
            )
        for name in ["periodos_aplicables", "relaciones"]:
            items = values.get(name, [])
            if (
                not isinstance(items, (list, tuple))
                or len(items) > 100
                or any(
                    not isinstance(item, str) or not item.strip() or len(item) > 300
                    for item in items
                )
            ):
                raise ServiceError("METADATOS_INVALIDOS", f"El campo '{name}' no es válido.")
            values[name] = tuple(items)
        for name in ["fecha_emision", "vigente_desde", "vigente_hasta"]:
            if values.get(name):
                try:
                    date.fromisoformat(values[name])
                except ValueError:
                    raise ServiceError(
                        "FECHA_INVALIDA", f"El campo '{name}' requiere una fecha AAAA-MM-DD."
                    ) from None
        if values.get("vigente_desde") and values.get("vigente_hasta"):
            if values["vigente_desde"] > values["vigente_hasta"]:
                raise ServiceError(
                    "FECHA_INVALIDA", "El inicio de vigencia no puede ser posterior al fin."
                )
        if values.get("fuente_url") and not values["fuente_url"].startswith(
            ("https://", "http://")
        ):
            raise ServiceError("FUENTE_INVALIDA", "La fuente debe ser una dirección HTTP o HTTPS.")
        return cls(**values)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class Block:
    text: str
    kind: str = "paragraph"
    locator: str = ""


@dataclasses.dataclass(frozen=True)
class Page:
    number: int
    blocks: tuple[Block, ...]
    ocr: bool = False
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def parse(cls, data: dict) -> Page:
        return cls(
            data["number"],
            tuple(Block(**b) for b in data["blocks"]),
            data.get("ocr", False),
            tuple(data.get("warnings", [])),
        )


@dataclasses.dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    page: int
    locator: str
    ordinal: int
    metadata: dict
    token_count: int

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class EmbeddingProfile:
    model: str
    revision: str
    dimension: int
    max_tokens: int = 512
    passage_prefix: str = "passage: "
    query_prefix: str = "query: "
    normalized: bool = True

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def validate_progress(data: Any) -> dict:
    if not isinstance(data, dict) or set(data) - {"operation_id", "stage", "message", "counts"}:
        raise ServiceError("PROGRESO_INVALIDO", "La actualización de progreso no es válida.")
    if (
        data.get("stage") not in STAGES
        or not isinstance(data.get("operation_id"), str)
        or not 1 <= len(data["operation_id"]) <= 200
    ):
        raise ServiceError(
            "PROGRESO_INVALIDO", "La etapa o identificador de operación no es válido."
        )
    if not isinstance(data.get("message"), str) or len(data["message"]) > 300:
        raise ServiceError("PROGRESO_INVALIDO", "El mensaje de progreso no es válido.")
    counts = data.get("counts", {})
    if not isinstance(counts, dict) or set(counts) - {"paginas", "fragmentos", "vectores"}:
        raise ServiceError("PROGRESO_INVALIDO", "Los contadores no son válidos.")
    if any(type(v) is not int or not 0 <= v <= 10_000_000 for v in counts.values()):
        raise ServiceError("PROGRESO_INVALIDO", "Los contadores no son válidos.")
    return data
