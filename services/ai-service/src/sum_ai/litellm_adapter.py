"""One LiteLLM transport for LangChain agents and bounded connection probes."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import date

# Do not fetch a mutable remote price map during import or model construction.
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm
from langchain_litellm import ChatLiteLLM

litellm.suppress_debug_info = True
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

PREFIXES = {"ollama": "ollama_chat", "google": "gemini", "custom": "openai"}


def model_name(provider: str, model: str) -> str:
    prefix = PREFIXES.get(provider, provider)
    return model if model.startswith(prefix + "/") else f"{prefix}/{model}"


def chat_model(provider: str, model: str, api_key: str, base_url: str | None,
               timeout: float = 30) -> ChatLiteLLM:
    return ChatLiteLLM(model=model_name(provider, model),
        api_key=api_key or "local-no-key", api_base=base_url,
        request_timeout=timeout, max_retries=0,
        model_kwargs={"num_retries": 0})


def model_pricing(provider: str, model: str) -> dict:
    pricing = {"input_usd_per_million": None, "output_usd_per_million": None,
               "pricing_date": date.today().isoformat(), "source": "litellm-bundled"}
    if provider == "ollama":
        return {**pricing, "input_usd_per_million": 0, "output_usd_per_million": 0,
                "source": "local"}
    if provider == "custom":
        return {**pricing, "source": "manual"}
    try:
        info = litellm.get_model_info(model=model_name(provider, model))
        for field, key in (("input_usd_per_million", "input_cost_per_token"),
                           ("output_usd_per_million", "output_cost_per_token")):
            value = info.get(key)
            if value is not None and 0 <= float(value) * 1_000_000 <= 10000:
                pricing[field] = float(value) * 1_000_000
    except Exception:
        pass  # Unknown pricing requires an explicit operator-supplied rate.
    return pricing


PROBE_TOOL = {"type": "function", "function": {
    "name": "connection_probe", "description": "Confirm the connection with value ok.",
    "parameters": {"type": "object", "properties": {"value": {"type": "string", "enum": ["ok"]}},
                   "required": ["value"], "additionalProperties": False}}}


async def probe_connection(registry, quota, actor_id: str, runtime, model: str) -> dict:
    started = time.monotonic()
    reservation = await quota.reserve(actor_id, runtime.provider, model, 384)
    used_tokens = 384  # A failed or lost response may still be billed.
    result = {"success": False, "code": "AI_PROVIDER_UNAVAILABLE", "tools_supported": False,
              "input_tokens": 0, "output_tokens": 0}
    try:
        async with asyncio.timeout(8):
            client = registry.with_runtime(runtime).resolve(runtime.provider, model)
            reply = await client.bind_tools([PROBE_TOOL]).ainvoke(
                "Call connection_probe with value ok. Do not return ordinary text.",
                max_tokens=128, timeout=8, config={"callbacks": [], "tags": ["connection-probe"]})
        usage = reply.usage_metadata or {}
        result["input_tokens"] = max(0, min(9000, int(usage.get("input_tokens", 0))))
        result["output_tokens"] = max(0, min(9000, int(usage.get("output_tokens", 0))))
        if usage:
            used_tokens = min(9000, result["input_tokens"] + result["output_tokens"])
        valid = any(call.get("name") == "connection_probe" and call.get("args") == {"value": "ok"}
                    for call in reply.tool_calls)
        result.update(success=valid, tools_supported=valid,
                      code="AI_CONNECTION_OK" if valid else "AI_TOOLS_NOT_VERIFIED")
    except TimeoutError:
        result["code"] = "AI_PROVIDER_TIMEOUT"
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        result["code"] = {401: "AI_PROVIDER_AUTH_FAILED", 403: "AI_PROVIDER_AUTH_FAILED",
                          404: "AI_MODEL_UNKNOWN", 429: "AI_PROVIDER_RATE_LIMIT",
                          408: "AI_PROVIDER_TIMEOUT", 400: "AI_PROVIDER_INPUT_UNSUPPORTED"}.get(status, "AI_PROVIDER_UNAVAILABLE")
        if isinstance(exc, litellm.Timeout):
            result["code"] = "AI_PROVIDER_TIMEOUT"
    finally:
        await quota.settle(reservation, used_tokens)
    return {**result, "latency_ms": round((time.monotonic() - started) * 1000, 1)}
