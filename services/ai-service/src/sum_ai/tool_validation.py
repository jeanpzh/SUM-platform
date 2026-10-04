"""Reject invalid research arguments with audited, bounded feedback to the agent."""
from __future__ import annotations

import json
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from pydantic import ValidationError
from sum_contracts.ai import AuditEvent
from sum_contracts.models import ServiceError

from .tools import RESEARCH_TOOL_SCHEMAS


class ResearchToolValidationMiddleware(AgentMiddleware):
    def __init__(self, trace, recorder, max_calls: int):
        self.trace, self.recorder, self.max_calls = trace, recorder, max_calls

    async def _reject(self, request, message: str):
        if len(self.trace) >= self.max_calls:
            raise ServiceError("AI_TOOL_LIMIT", "Se alcanzó el límite de herramientas.", 429)
        name = request.tool_call["name"]
        arguments = request.tool_call.get("args", {})
        try:
            serialized = json.dumps(arguments, ensure_ascii=False, allow_nan=False)
            bounded = arguments if len(serialized.encode()) <= 2000 else {
                "preview": serialized.encode()[:2000].decode(errors="ignore"), "truncated": True}
        except (TypeError, ValueError):
            bounded = {"preview": repr(arguments)[:500], "truncated": True}
        # Bound rejected inputs too: the audit contract caps each payload at 16 KiB.
        item = {"tool": name, "arguments": bounded, "code": "AI_TOOL_INPUT_INVALID",
                "validation_message": message[:1000], "chunk_ids": [], "duration_ms": 0}
        number = len(self.trace) + 1
        self.trace.append(item)
        if hasattr(self.recorder, "context"):
            await self.recorder.context()
        await self.recorder.record(AuditEvent(operation_id=f"tool-input:{number}:rejected",
            kind="tool", code="AI_TOOL_INPUT_INVALID", duration_ms=0, payload=item))
        return ToolMessage(content=f"{name}: {message[:1000]} Correct the arguments using the tool schema. "
            "You may finish with evidence already retrieved if another tool call is unnecessary.",
            name=name, tool_call_id=request.tool_call["id"], status="error")

    async def awrap_tool_call(self, request, handler):
        schema = RESEARCH_TOOL_SCHEMAS.get(request.tool_call["name"])
        if schema is None:
            return await handler(request)
        try:
            schema.model_validate(request.tool_call.get("args", {}))
        except ValidationError as exc:
            errors = exc.errors(include_input=False, include_url=False)
            message = "; ".join(f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in errors[:4])
            return await self._reject(request, message)
        try:
            return await handler(request)
        except ServiceError as exc:
            if exc.code != "AI_TOOL_INPUT_INVALID":
                raise
            return await self._reject(request, exc.message)
