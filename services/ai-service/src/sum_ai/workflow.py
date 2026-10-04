"""Inngest carries only run IDs; Backend API owns the durable state."""

from __future__ import annotations

import inngest
from sum_contracts.ai import (
    AI_CONTRACT_VERSION,
    AI_EVALUATION_REQUESTED,
    AI_RUN_REQUESTED,
    AI_STUDENT_REQUESTED,
    AuditEvent,
)
from sum_contracts.models import ServiceError, require_uuid


async def run_once(run_id: str, runner, reporter):
    run_id = require_uuid(run_id)
    try:
        context = await reporter.context(run_id)
    except ServiceError as exc:
        if exc.code == "AI_RUN_TERMINAL":
            return {"run_id": run_id}
        raise
    await reporter.record(AuditEvent(operation_id="run:started", kind="started", stage="validating"))
    try:
        result = await runner.run(context, reporter)
    except ServiceError as exc:
        if exc.code != "AI_RUN_TERMINAL":
            await reporter.record(AuditEvent(operation_id="run:failed", kind="failed", code=exc.code))
        if exc.code == "AI_RUN_TERMINAL":
            return {"run_id": run_id}
        raise inngest.NonRetriableError(exc.code) from exc
    await reporter.record(AuditEvent(operation_id="run:completed", kind="completed",
                                     stage="verifying", result=result))
    return {"run_id": run_id}


def register(client: inngest.Inngest, runner, reporter_factory):
    async def on_failure(ctx):
        original = ctx.event.data.get("event", {})
        run_id = require_uuid(original.get("data", {}).get("run_id", ""))
        reporter = reporter_factory(run_id)
        try:
            await reporter.record(AuditEvent(operation_id="run:failed", kind="failed",
                                             code="AI_RETRIES_EXHAUSTED"))
        except ServiceError as exc:
            if exc.code != "AI_RUN_TERMINAL":
                raise
        finally:
            await reporter.close()
        return {"run_id": run_id}

    async def handle(ctx):
        if ctx.event.data.get("contract_version") != AI_CONTRACT_VERSION:
            raise inngest.NonRetriableError("AI_CONTRACT_VERSION")
        run_id = require_uuid(ctx.event.data.get("run_id", ""))

        async def process():
            reporter = reporter_factory(run_id)
            try:
                return await run_once(run_id, runner, reporter)
            finally:
                await reporter.close()

        return await ctx.step.run("execute-admin-rag", process)

    @client.create_function(fn_id="ai-admin-run-v1", trigger=inngest.TriggerEvent(event=AI_RUN_REQUESTED),
                            idempotency="event.data.run_id", retries=1, on_failure=on_failure,
                            concurrency=[inngest.Concurrency(limit=4)])
    async def execute(ctx):
        return await handle(ctx)

    @client.create_function(fn_id="ai-admin-evaluation-v1", trigger=inngest.TriggerEvent(event=AI_EVALUATION_REQUESTED),
                            idempotency="event.data.run_id", retries=1, on_failure=on_failure,
                            priority=inngest.Priority(run="-120"), concurrency=[inngest.Concurrency(limit=1)])
    async def evaluate(ctx):
        return await handle(ctx)

    @client.create_function(fn_id="ai-student-consultation-v1", trigger=inngest.TriggerEvent(event=AI_STUDENT_REQUESTED),
                            idempotency="event.data.run_id", retries=1, on_failure=on_failure,
                            concurrency=[inngest.Concurrency(limit=4)])
    async def student(ctx):
        return await handle(ctx)

    return [execute, evaluate, student]
