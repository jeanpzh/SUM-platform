"""Short-timeout internal client for AI model discovery."""

import httpx
from sum_contracts.ai_providers import ConnectionProbeResult
from sum_contracts.models import ServiceError


class AiServiceClient:
    def __init__(self, base_url: str, service_token: str):
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token

    async def admit_request(self, actor: str, key: str, fingerprint: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(self.base_url + "/internal/admit",
                    headers={"Authorization": "Bearer " + self.service_token},
                    json={"actor_id": actor, "key": key, "fingerprint": fingerprint})
            if response.status_code in {429, 503}:
                code = ("AI_USER_RATE_LIMIT" if actor.startswith("student:") else "AI_ADMIN_RATE_LIMIT") if response.status_code == 429 else "AI_QUOTA_UNAVAILABLE"
                error = ServiceError(code, "La capacidad de IA no está disponible.", response.status_code)
                error.retry_after = max(1, min(86400, int(response.headers.get("Retry-After", "1"))))
                raise error
            response.raise_for_status()
        except ServiceError:
            raise
        except Exception as exc:
            raise ServiceError("AI_QUOTA_UNAVAILABLE", "No se pudo confirmar capacidad de IA.", 503) from exc

    async def list_models(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(self.base_url + "/internal/models",
                                        headers={"Authorization": "Bearer " + self.service_token})
            response.raise_for_status()
            return response.json()

    async def model_pricing(self, provider: str, model: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(self.base_url + "/internal/models/pricing",
                    headers={"Authorization": "Bearer " + self.service_token},
                    params={"provider": provider, "model": model})
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise ServiceError("AI_PRICING_UNAVAILABLE", "No se pudieron cargar tarifas automáticas.", 503) from exc

    async def test_provider(self, actor: str, runtime, model: str) -> dict:
        data = runtime.model_dump(mode="json")
        data["api_key"] = runtime.api_key.get_secret_value()
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                response = await client.post(self.base_url + "/internal/providers/test",
                    headers={"Authorization": "Bearer " + self.service_token},
                    json={"actor_id": actor, "runtime": data, "model": model})
            if response.status_code in {429, 503}:
                error = ServiceError("AI_QUOTA_UNAVAILABLE" if response.status_code == 503 else "AI_PROVIDER_RATE_LIMIT",
                    "No hay capacidad para probar la conexión ahora.", response.status_code)
                error.retry_after = max(1, min(180, int(response.headers.get("Retry-After", "1"))))
                raise error
            response.raise_for_status()
            return ConnectionProbeResult.model_validate(response.json()).model_dump(mode="json")
        except ServiceError:
            raise
        except httpx.TimeoutException as exc:
            raise ServiceError("AI_PROVIDER_TIMEOUT", "La prueba superó el tiempo permitido.", 504) from exc
        except Exception as exc:
            raise ServiceError("AI_PROVIDER_UNAVAILABLE", "No se pudo completar la prueba de conexión.", 503) from exc
