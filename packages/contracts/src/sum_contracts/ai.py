"""Versioned, bounded contracts shared by the admin RAG services."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .ai_providers import ProviderRuntime
from .models import CONTRACT_VERSION
from .student import StudentAnalysis, StudentOptions

AI_RUN_REQUESTED = "ai/admin.run.requested"
AI_EVALUATION_REQUESTED = "ai/admin.evaluation.requested"
AI_STUDENT_REQUESTED = "ai/student.consultation.requested"
AI_CONTRACT_VERSION = CONTRACT_VERSION


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class CreateRunRequest(StrictModel):
    question: str = Field(min_length=3, max_length=2000)
    provider: Literal["ollama", "openai", "anthropic", "google", "groq", "custom"]
    model: str = Field(min_length=1, max_length=150, pattern=r"^[A-Za-z0-9._:/-]+$")
    document_ids: tuple[UUID, ...] = Field(default=(), max_length=20)
    top_k: int = Field(default=4, ge=1, le=10)
    provider_config_id: UUID | None = None
    provider_revision: int | None = Field(default=None, ge=1)
    audience: Literal["admin", "student"] = "admin"
    student_options: StudentOptions | None = None

    @model_validator(mode="after")
    def student_scope(self):
        if self.audience == "student" and (self.student_options is None or self.provider_config_id):
            raise ValueError("Student runs require options and a server configured model")
        if self.audience == "admin" and self.student_options is not None:
            raise ValueError("Academic context is reserved for student consultations")
        return self

    @model_validator(mode="after")
    def paired_provider_version(self):
        if (self.provider_config_id is None) != (self.provider_revision is None):
            raise ValueError("Provider connection ID and revision must be supplied together")
        return self

    @field_validator("document_ids")
    @classmethod
    def distinct_documents(cls, ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
        if len(set(ids)) != len(ids):
            raise ValueError("document_ids must be distinct")
        return ids

    def fingerprint(self) -> str:
        canonical = self.model_dump_json(exclude_none=True,
            exclude={"audience", "student_options"} if self.audience == "admin" else set())
        return hashlib.sha256(canonical.encode()).hexdigest()


class Evidence(StrictModel):
    chunk_id: UUID
    document_id: UUID
    version_id: UUID
    generation_id: UUID
    page: int = Field(ge=1)
    locator: str = Field(max_length=500)
    text: str = Field(max_length=10000)
    rank: int = Field(ge=1)
    score: float | None = None


class Citation(StrictModel):
    chunk_id: UUID
    document_id: UUID
    version_id: UUID
    generation_id: UUID
    page: int = Field(ge=1)
    locator: str = Field(max_length=500)


class RunUsage(StrictModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0, ge=0)
    pricing_date: str | None = None


class EvaluationScores(StrictModel):
    recall_at_k: float = Field(ge=0, le=1)
    precision_at_k: float = Field(ge=0, le=1)
    mrr: float = Field(ge=0, le=1)
    k: int = Field(ge=1, le=10)


class EvaluationCase(StrictModel):
    case_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=3, max_length=2000)
    document_ids: tuple[UUID, ...] = Field(max_length=20)
    generation_ids: tuple[UUID, ...] = Field(min_length=1, max_length=20)
    relevant_ids: tuple[UUID, ...] = Field(min_length=1, max_length=100)


class EvaluationContext(StrictModel):
    dataset_id: str = Field(min_length=1, max_length=100)
    dataset_version: str = Field(min_length=1, max_length=100)
    case: EvaluationCase


class EvaluationDataset(StrictModel):
    dataset_id: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=100)
    cases: tuple[EvaluationCase, ...] = Field(min_length=1, max_length=100)


class RunResult(StrictModel):
    answer: str = Field(max_length=12000)
    citations: tuple[Citation, ...] = Field(default=(), max_length=8)
    evidence: tuple[Evidence, ...] = Field(default=(), max_length=8)
    provider: str = Field(max_length=30)
    model: str = Field(max_length=150)
    usage: RunUsage = Field(default_factory=RunUsage)
    timings: dict[str, float] = Field(default_factory=dict)
    tool_trace: tuple[dict, ...] = Field(default=(), max_length=6)
    limitations: tuple[str, ...] = Field(default=(), max_length=5)
    abstained: bool = False
    evaluation: EvaluationScores | None = None
    student_analysis: StudentAnalysis | None = None


class AuditEvent(StrictModel):
    operation_id: str = Field(min_length=1, max_length=200)
    kind: Literal["started", "stage", "evidence", "tool", "usage", "completed", "failed", "cancelled"]
    stage: Literal["validating", "planning", "collecting_context", "checking", "retrieving", "researching", "composing", "verifying"] | None = None
    duration_ms: float | None = Field(default=None, ge=0)
    code: str | None = Field(default=None, max_length=80, pattern=r"^[A-Z0-9_]+$")
    payload: dict = Field(default_factory=dict)
    result: RunResult | None = None

    @field_validator("payload")
    @classmethod
    def bounded_payload(cls, payload):
        if len(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()) > 16384:
            raise ValueError("Audit payload exceeds 16 KiB")
        return payload

    @model_validator(mode="after")
    def valid_result_and_usage(self):
        if self.result is not None and self.kind != "completed":
            raise ValueError("Only completion can include a result")
        if self.kind == "usage":
            allowed = {"input_tokens", "output_tokens", "estimated_cost_usd", "pricing_date", "usage_estimated"}
            if set(self.payload) - allowed:
                raise ValueError("Unexpected usage fields")
            RunUsage.model_validate({key: value for key, value in self.payload.items() if key != "usage_estimated"})
        return self


class RunContext(StrictModel):
    contract_version: int = AI_CONTRACT_VERSION
    run_id: UUID
    owner_id: str
    request: CreateRunRequest
    status: Literal["queued", "running"]
    created_at: datetime
    evaluation: EvaluationContext | None = None
    provider_runtime: ProviderRuntime | None = Field(default=None, repr=False)
    model_calls: int = Field(default=0, ge=0, le=5)
    model_usage: RunUsage = Field(default_factory=RunUsage)
    corpus_sha256: str | None = None
