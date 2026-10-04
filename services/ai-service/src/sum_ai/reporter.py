"""Authenticated, bounded callbacks to the durable Backend API."""

from __future__ import annotations

from uuid import uuid4

import httpx
from sum_contracts.ai import AuditEvent, RunContext
from sum_contracts.models import ServiceError, require_uuid


class HttpAuditRecorder:
    def __init__(self, base_url: str, token: str, run_id: str):
        self.run_id = require_uuid(run_id)
        self.attempt_id = uuid4().hex[:16]
        self.client = httpx.AsyncClient(base_url=base_url,
                                        headers={"Authorization": "Bearer " + token}, timeout=5)

    async def context(self, run_id: str | None = None) -> RunContext:
        response = await self.client.get(f"/internal/ai/runs/{require_uuid(run_id or self.run_id)}")
        if response.status_code == 409:
            raise ServiceError("AI_RUN_TERMINAL", "La ejecución ya terminó.", 409)
        response.raise_for_status()
        return RunContext.model_validate(response.json())

    async def record(self, event: AuditEvent) -> None:
        if event.kind not in {"completed", "failed", "cancelled"}:
            event = event.model_copy(update={"operation_id": self.attempt_id + ":" + event.operation_id})
        response = await self.client.post(f"/internal/ai/runs/{self.run_id}/events", json=event.model_dump(mode="json"))
        if response.status_code == 409:
            raise ServiceError("AI_RUN_TERMINAL", "La ejecución ya terminó.", 409)
        response.raise_for_status()

    async def close(self):
        await self.client.aclose()
