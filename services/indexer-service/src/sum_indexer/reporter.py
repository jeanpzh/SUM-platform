from __future__ import annotations

import asyncio

from sum_contracts.models import CONTRACT_VERSION, JobStopped, ServiceError, require_uuid


class HttpJobReporter:
    def __init__(self, url: str, token: str):
        import httpx

        self.client = httpx.AsyncClient(
            base_url=url, headers={"Authorization": f"Bearer {token}"}, timeout=30
        )

    async def request(self, method: str, job_id: str, suffix: str = "", data: dict | None = None):
        path = f"/internal/indexing-jobs/{require_uuid(job_id)}{suffix}"
        response = await self.client.request(method, path, json=data)
        if response.status_code == 409:
            raise JobStopped()
        if response.status_code >= 500:
            raise RuntimeError("BACKEND_NO_DISPONIBLE")
        if response.status_code >= 400:
            raise ServiceError(
                "CONTRATO_RECHAZADO",
                "El backend rechazó el contrato interno.",
                response.status_code,
            )
        return response.json()

    async def context(self, job_id: str) -> dict:
        context = await self.request("GET", job_id)
        if context.get("contract_version") != CONTRACT_VERSION:
            raise ServiceError("CONTRATO_RECHAZADO", "La versión del contrato no es compatible.")
        return context

    async def progress(
        self, job_id: str, operation: str, stage: str, message: str, counts: dict | None = None
    ):
        await self.request(
            "POST",
            job_id,
            "/progress",
            {"operation_id": operation, "stage": stage, "message": message, "counts": counts or {}},
        )

    async def embedding_profile(self, job_id: str, profile: dict):
        await self.request("PUT", job_id, "/embedding-profile", profile)

    async def timing(self, job_id: str, data: dict):
        for attempt in range(3):
            try:
                return await self.request("POST", job_id, "/timing", data)
            except (JobStopped, ServiceError):
                raise
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(0.2 * 2**attempt)

    async def complete(self, job_id: str, manifest: dict):
        await self.request("POST", job_id, "/complete", manifest)

    async def fail(self, job_id: str, code: str):
        await self.request("POST", job_id, "/fail", {"code": code})

    async def close(self):
        await self.client.aclose()
