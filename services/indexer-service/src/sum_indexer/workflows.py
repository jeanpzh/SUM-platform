from __future__ import annotations

import asyncio
import logging
from time import perf_counter_ns
from uuid import uuid4

from sum_contracts.models import (
    CONTRACT_VERSION,
    INDEX_REQUESTED,
    JobStopped,
    ServiceError,
    Status,
    require_uuid,
)

METHOD_STAGES = {
    "validate": "validando",
    "extract": "extrayendo",
    "chunk": "fragmentando",
    "embed": "generando_vectores",
    "store": "guardando",
    "publish": "publicando",
}


async def reconcile_outcomes(vectors, reporter) -> dict:
    pending = await asyncio.to_thread(vectors.pending_outcomes)
    delivered = 0
    for outcome in pending:
        job_id = str(outcome["job_id"])
        try:
            if outcome["kind"] == "completed":
                await reporter.complete(job_id, outcome["payload"])
            else:
                await reporter.fail(job_id, outcome["payload"]["code"])
            await asyncio.to_thread(vectors.acknowledge_outcome, job_id)
            delivered += 1
        except JobStopped:
            # Cancellation or replacement permanently prevents publication.
            await asyncio.to_thread(vectors.acknowledge_outcome, job_id)
        except Exception:
            # Keep the durable outcome for the next cron invocation.
            continue
    return {"delivered": delivered}


async def run_stage(pipeline, method: str, job_id: str) -> dict:
    job_id = require_uuid(job_id)
    operation = getattr(pipeline, method)

    async def heartbeat():
        while True:
            await asyncio.sleep(20)
            await pipeline.context(job_id)
            await pipeline.reporter.progress(
                job_id,
                f"heartbeat-{method}",
                METHOD_STAGES[method],
                "El documento sigue en procesamiento.",
            )

    work, pulse = None, None
    attempt_id = str(uuid4())
    started = None
    outcome = "fallido"
    try:
        await pipeline.reporter.timing(
            job_id, {"attempt_id": attempt_id, "stage": METHOD_STAGES[method], "action": "start"}
        )
        started = perf_counter_ns()
        async with asyncio.timeout(pipeline.settings.stage_timeout):
            work = asyncio.create_task(operation(job_id))
            pulse = asyncio.create_task(heartbeat())
            done, _ = await asyncio.wait({work, pulse}, return_when=asyncio.FIRST_COMPLETED)
            if pulse in done:
                await pulse
            result = await work
            outcome = "cancelado" if result.get("status") == Status.CANCELLED else "completado"
            return result
    except JobStopped:
        outcome = "cancelado"
        return {"job_id": job_id, "status": Status.CANCELLED}
    except ServiceError as exc:
        if exc.status >= 500:
            raise RuntimeError(exc.code) from None
        await asyncio.to_thread(pipeline.vectors.enqueue_failure, job_id, exc.code)
        await reconcile_outcomes(pipeline.vectors, pipeline.reporter)
        return {"job_id": job_id, "status": Status.FAILED, "code": exc.code}
    except asyncio.CancelledError:
        outcome = "interrumpido"
        raise
    except TimeoutError:
        raise RuntimeError("LIMITE_TIEMPO") from None
    except Exception:
        raise RuntimeError("ERROR_TRANSITORIO_DE_INDEXACION") from None
    finally:
        for task in (work, pulse):
            if task is not None and not task.done():
                task.cancel()
        await asyncio.gather(
            *(task for task in (work, pulse) if task is not None), return_exceptions=True
        )
        if started is not None:
            duration_ms = (perf_counter_ns() - started) / 1_000_000
            # Timing delivery must not turn successfully published work into a failed job.
            try:
                await pipeline.reporter.timing(
                    job_id,
                    {
                        "attempt_id": attempt_id,
                        "stage": METHOD_STAGES[method],
                        "action": "end",
                        "duration_ms": duration_ms,
                        "outcome": outcome,
                    },
                )
            except Exception:
                logging.getLogger("sum.indexer").warning(
                    "Could not close stage timing for job %s attempt %s", job_id, attempt_id
                )


def register(client, pipeline):
    import inngest

    async def on_failure(ctx):
        original = ctx.event.data.get("event", {})
        job_id = require_uuid(original.get("data", {}).get("job_id", ""))

        async def record():
            await asyncio.to_thread(pipeline.vectors.enqueue_failure, job_id, "REINTENTOS_AGOTADOS")
            await reconcile_outcomes(pipeline.vectors, pipeline.reporter)
            return {"job_id": job_id}

        return await ctx.step.run("record-failure", record)

    functions = []
    settings = pipeline.settings
    limits = {
        "validate": settings.extraction_concurrency,
        "extract": settings.extraction_concurrency,
        "chunk": settings.extraction_concurrency,
        "embed": settings.embedding_concurrency,
        "store": settings.writing_concurrency,
        "publish": settings.writing_concurrency,
    }

    def make_phase(method):
        @client.create_function(
            fn_id=f"index-{method}-v1",
            trigger=inngest.TriggerEvent(event=f"document/index.{method}"),
            concurrency=[inngest.Concurrency(limit=limits[method])],
            priority=inngest.Priority(run="event.data.priority"),
            retries=3,
            on_failure=on_failure,
        )
        async def phase(ctx):
            if ctx.event.data.get("contract_version") != CONTRACT_VERSION:
                raise inngest.NonRetriableError("VERSION_DE_CONTRATO_NO_ADMITIDA")
            job_id = require_uuid(ctx.event.data.get("job_id", ""))
            return await ctx.step.run(method, run_stage, pipeline, method, job_id)

        return phase

    phases = {method: make_phase(method) for method in METHOD_STAGES}
    functions.extend(phases.values())

    @client.create_function(
        fn_id="index-document-v1",
        trigger=inngest.TriggerEvent(event=INDEX_REQUESTED),
        idempotency="event.data.job_id",
        retries=3,
        on_failure=on_failure,
    )
    async def orchestrate(ctx):
        if ctx.event.data.get("contract_version") != CONTRACT_VERSION:
            raise inngest.NonRetriableError("VERSION_DE_CONTRATO_NO_ADMITIDA")
        job_id = require_uuid(ctx.event.data.get("job_id", ""))
        data = {
            "job_id": job_id,
            "contract_version": CONTRACT_VERSION,
            "priority": ctx.event.data.get("priority", 0),
        }
        for method, function in phases.items():
            result = await ctx.step.invoke(method, function=function, data=data)
            if result.get("status") in {Status.CANCELLED, Status.FAILED, Status.COMPLETED}:
                return {"job_id": job_id, "status": result["status"]}
        return {"job_id": job_id, "status": Status.COMPLETED}

    @client.create_function(
        fn_id="reconcile-index-outcomes-v1",
        trigger=inngest.TriggerCron(cron="*/1 * * * *"),
        concurrency=[inngest.Concurrency(limit=1)],
        retries=3,
    )
    async def reconcile(ctx):
        return await ctx.step.run(
            "deliver-outcomes", reconcile_outcomes, pipeline.vectors, pipeline.reporter
        )

    functions.extend([orchestrate, reconcile])
    return functions
