"""Idempotent terminal-run projection; HTTP reads bounded hourly aggregates."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import DateTime, Float, cast, column, delete, func, select, table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .ai_tables import (
    artifacts,
    evaluations,
    events,
    metric_buckets,
    metric_runs,
    rejection_buckets,
    runs,
)
from .ai_tables import usage as usage_table

LATENCY_BOUNDS = (100, 250, 500, 1000, 2000, 5000, 10000, 30000, 60000, 120000, 300000, 600000)


def _histogram(values):
    counts = [0] * (len(LATENCY_BOUNDS) + 1)
    for value in values:
        bucket = next((index for index, bound in enumerate(LATENCY_BOUNDS) if value <= bound), len(LATENCY_BOUNDS))
        counts[bucket] += 1
    return counts


def _summary(count, total, histogram):
    def quantile(fraction):
        if not count:
            return None
        target, seen = math.ceil(count * fraction), 0
        for index, frequency in enumerate(histogram):
            seen += frequency
            if seen >= target:
                return LATENCY_BOUNDS[index] if index < len(LATENCY_BOUNDS) else None
        return None
    return {"count": count, "mean_ms": total / count if count else None,
            "p50_ms": quantile(0.5), "p95_ms": quantile(0.95), "percentiles_approximate": True}


def summarize_latencies(values: list[float]) -> dict:
    return _summary(len(values), sum(values), _histogram(values))


def _merge(left: dict, right: dict):
    result = dict(left)
    for key, value in right.items():
        if key == "histogram":
            result[key] = [a + b for a, b in zip(left.get(key, [0] * len(value)), value, strict=True)]
        else:
            result[key] = result.get(key, 0) + value
    return result


class MetricsProjector:
    def __init__(self, database):
        self.database = database

    def project(self, after_event_id: int = 0, limit: int = 100) -> int:
        # Track terminal run IDs, because a global event cursor can skip runs still in flight.
        with self.database.engine.begin() as conn:
            conn.execute(select(func.pg_advisory_xact_lock(func.hashtextextended("ai-metrics-projector", 0))))
            projected = select(metric_runs.c.run_id).where(metric_runs.c.run_id == runs.c.id).exists()
            query = select(runs).where(runs.c.status.in_(["completed", "failed", "cancelled"]), ~projected,
                (runs.c.status != "cancelled") | (runs.c.finished_at <= func.now() - timedelta(seconds=130))
                ).order_by(runs.c.finished_at, runs.c.id).limit(limit)
            rows = conn.execute(query).mappings().all()
            for row in rows:
                run_events = conn.execute(select(events).where(events.c.run_id == row["id"]).order_by(events.c.sequence)).mappings().all()
                result = row["result"] or {}
                proof = conn.scalar(select(artifacts.c.data).where(artifacts.c.run_id == row["id"], artifacts.c.kind == "retrieval")) or {}
                generations = sorted({item["generation_id"] for item in result.get("evidence", [])} | set(proof.get("generation_ids", [])))
                corpus_key = hashlib.sha256(json.dumps(generations).encode()).hexdigest()[:24]
                duration = max(0, (row["finished_at"] - row["created_at"]).total_seconds() * 1000)
                usage = conn.execute(select(
                    func.coalesce(func.sum(usage_table.c.input_tokens), 0).label("input_tokens"),
                    func.coalesce(func.sum(usage_table.c.output_tokens), 0).label("output_tokens"),
                    func.coalesce(func.sum(usage_table.c.estimated_cost_usd), 0).label("estimated_cost_usd")
                ).where(usage_table.c.run_id == row["id"])).mappings().one()
                total = {"count": 1, "duration_sum_ms": duration, "histogram": _histogram([duration]),
                         "abstentions": int(result.get("abstained", False)),
                         "rate_limits": int(row["error_code"] in {"AI_ADMIN_RATE_LIMIT", "AI_PROVIDER_RATE_LIMIT", "AI_TOKEN_LIMIT"}),
                         "timeouts": int(row["error_code"] == "AI_TIMEOUT"),
                         "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
                         "estimated_cost_usd": float(usage.get("estimated_cost_usd", 0)),
                         "tool_calls": sum(event["kind"] == "tool" and event["operation_id"].endswith(":start") for event in run_events)}
                stages = {"total": total}
                for event in run_events:
                    if event["kind"] == "stage" and event["duration_ms"] is not None:
                        contribution = {"count": 1, "duration_sum_ms": event["duration_ms"], "histogram": _histogram([event["duration_ms"]])}
                        stage = event["stage"]
                        stages[stage] = _merge(stages.get(stage, {}), contribution)
                quality = result.get("evaluation")
                if quality:
                    stages["total"].update(evaluation_count=1, recall_sum=quality["recall_at_k"],
                                            precision_sum=quality["precision_at_k"], mrr_sum=quality["mrr"])
                hour = row["created_at"].replace(minute=0, second=0, microsecond=0)
                traffic = "evaluation" if row["evaluation_id"] else "interactive"
                for stage, contribution in stages.items():
                    key = (hour, row["owner_id"], row["request"]["provider"], row["request"]["model"], row["status"], corpus_key, traffic, stage)
                    names = ("hour", "owner_id", "provider", "model", "status", "corpus_key", "traffic", "stage")
                    values = dict(zip(names, key, strict=True))
                    previous = conn.scalar(select(metric_buckets.c.data).where(
                        *(metric_buckets.c[name] == value for name, value in values.items())))
                    data = _merge(previous or {}, contribution)
                    statement = pg_insert(metric_buckets).values(**values, generation_ids=generations, data=data)
                    conn.execute(statement.on_conflict_do_update(index_elements=[metric_buckets.c[name] for name in names],
                        set_={"data": statement.excluded.data}))
                conn.execute(pg_insert(metric_runs).values(run_id=row["id"]).on_conflict_do_nothing())
            return len(rows)

    def get_metrics(self, owner: str, days: int = 7, provider: str = "", model: str = "",
                    generation: str = "", status: str = "") -> dict:
        from datetime import timedelta
        buckets = table("ai_metric_buckets", column("owner_id"), column("hour", DateTime(timezone=True)),
            column("provider"), column("model"), column("status"), column("traffic"), column("stage"),
            column("generation_ids", JSONB), column("data", JSONB), schema="application")
        c = buckets.c
        conditions = [c.owner_id == owner, c.hour >= func.now() - timedelta(days=days)]
        for name, value in (("provider", provider), ("model", model), ("status", status)):
            if value:
                conditions.append(c[name] == value)
        if generation:
            conditions.append(c.generation_ids.has_key(generation))
        hour = func.date_trunc("day" if days > 30 else "hour", c.hour).label("hour")
        fields = ("count", "duration_sum_ms", "abstentions", "rate_limits", "timeouts", "input_tokens",
                  "output_tokens", "estimated_cost_usd", "tool_calls", "evaluation_count", "recall_sum", "precision_sum", "mrr_sum")
        totals = []
        for name in fields:
            totals.extend([name, func.sum(func.coalesce(cast(c.data[name].astext, Float), 0))])
        histogram = func.jsonb_build_array(*[func.sum(func.coalesce(cast(c.data["histogram"][index].astext, Float), 0)) for index in range(len(LATENCY_BOUNDS) + 1)])
        query = select(hour, c.stage, c.traffic, c.status,
            func.jsonb_build_object(*totals, "histogram", histogram).label("data")).where(*conditions).group_by(hour, c.stage, c.traffic, c.status).order_by(hour)
        with self.database.engine.begin() as conn:
            rows = conn.execute(query).mappings().all()
        stages, hourly = {}, defaultdict(dict)
        statuses = defaultdict(int)
        quality_data = {}
        for row in rows:
            data = row["data"]
            if row["traffic"] == "evaluation":
                if row["stage"] == "total":
                    quality_data = _merge(quality_data, {key: data.get(key, 0) for key in ("evaluation_count", "recall_sum", "precision_sum", "mrr_sum")})
                continue
            stage = row["stage"]
            stages[stage] = _merge(stages.get(stage, {}), data)
            if stage == "total":
                statuses[row["status"]] += data["count"]
                hour = row["hour"].isoformat()
                hourly[hour] = _merge(hourly[hour], data)
        def summarize(data):
            return _summary(data.get("count", 0), data.get("duration_sum_ms", 0), data.get("histogram", [0] * (len(LATENCY_BOUNDS) + 1)))
        total = stages.get("total", {})
        if not generation and not status:
            conditions = [rejection_buckets.c.owner_id == owner, rejection_buckets.c.hour >= func.now() - timedelta(days=days)]
            for name, value in (("provider", provider), ("model", model)):
                if value:
                    conditions.append(rejection_buckets.c[name] == value)
            with self.database.engine.begin() as conn:
                rejected = conn.scalar(select(func.coalesce(func.sum(rejection_buckets.c.count), 0)).where(*conditions))
            total["rate_limits"] = total.get("rate_limits", 0) + rejected
        quality_count = quality_data.get("evaluation_count", 0)
        return {"days": days, "summary": {**summarize(total), "statuses": dict(statuses),
                **{key: total.get(key, 0) for key in ("abstentions", "rate_limits", "timeouts", "input_tokens", "output_tokens", "estimated_cost_usd", "tool_calls")}},
                "stages": [{"stage": stage, **summarize(data)} for stage, data in stages.items() if stage != "total"],
                "series": [{"hour": hour, **summarize(data), "estimated_cost_usd": data.get("estimated_cost_usd", 0)} for hour, data in hourly.items()],
                "quality": {"count": quality_count, "recall_at_k": quality_data["recall_sum"] / quality_count,
                    "precision_at_k": quality_data["precision_sum"] / quality_count,
                    "mrr": quality_data["mrr_sum"] / quality_count} if quality_count else None}

    def record_rejection(self, owner, provider, model):
        statement = pg_insert(rejection_buckets).values(hour=func.date_trunc("hour", func.now()),
            owner_id=owner, provider=provider, model=model, count=1)
        with self.database.engine.begin() as conn:
            conn.execute(statement.on_conflict_do_update(index_elements=[rejection_buckets.c[name]
                for name in ("hour", "owner_id", "provider", "model")], set_={"count": rejection_buckets.c.count + 1}))

    def purge(self, run_days=30, aggregate_days=90):
        from datetime import timedelta
        with self.database.engine.begin() as conn:
            projected = select(metric_runs.c.run_id).where(metric_runs.c.run_id == runs.c.id).exists()
            conn.execute(delete(runs).where(runs.c.created_at < func.now() - timedelta(days=run_days), projected))
            has_runs = select(runs.c.id).where(runs.c.evaluation_id == evaluations.c.id).exists()
            conn.execute(delete(evaluations).where(evaluations.c.created_at < func.now() - timedelta(days=run_days), ~has_runs))
            conn.execute(delete(metric_buckets).where(metric_buckets.c.hour < func.now() - timedelta(days=aggregate_days)))
            conn.execute(delete(rejection_buckets).where(rejection_buckets.c.hour < func.now() - timedelta(days=aggregate_days)))
