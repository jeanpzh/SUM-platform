"""Typed SQLAlchemy Core relations for the administrative AI subsystem."""
from sqlalchemy import BigInteger, Date, DateTime, Float, Integer, String, Uuid, column, table
from sqlalchemy.dialects.postgresql import JSONB


def relation(name, fields):
    return table(name, *(column(name, kind) for name, kind in fields.items()), schema="application")


runs = relation("ai_runs", dict(id=Uuid, owner_id=String, idempotency_key=String, fingerprint=String,
    request=JSONB, status=String, stage=String, sequence=BigInteger, result=JSONB, error_code=String,
    created_at=DateTime(timezone=True), updated_at=DateTime(timezone=True), finished_at=DateTime(timezone=True),
    evaluation_id=Uuid, evaluation_context=JSONB))
events = relation("ai_events", dict(id=BigInteger, run_id=Uuid, sequence=BigInteger, operation_id=String,
    kind=String, stage=String, duration_ms=Float, code=String, payload=JSONB, created_at=DateTime(timezone=True)))
artifacts = relation("ai_artifacts", dict(run_id=Uuid, kind=String, data=JSONB, created_at=DateTime(timezone=True)))
usage = relation("ai_usage", dict(run_id=Uuid, operation_id=String, input_tokens=Integer,
    output_tokens=Integer, estimated_cost_usd=Float, pricing_date=Date))
outbox = relation("outbox", dict(id=Uuid, run_id=Uuid, event_name=String, payload=JSONB, available_at=DateTime(timezone=True)))
evaluations = relation("ai_evaluations", dict(id=Uuid, owner_id=String, idempotency_key=String,
    fingerprint=String, dataset_id=String, dataset_version=String, provider=String, model=String,
    created_at=DateTime(timezone=True)))
metric_runs = relation("ai_metric_runs", dict(run_id=Uuid, projected_at=DateTime(timezone=True)))
metric_buckets = relation("ai_metric_buckets", dict(hour=DateTime(timezone=True), owner_id=String,
    provider=String, model=String, status=String, corpus_key=String, generation_ids=JSONB,
    traffic=String, stage=String, data=JSONB))
rejection_buckets = relation("ai_rejection_buckets", dict(hour=DateTime(timezone=True), owner_id=String,
    provider=String, model=String, count=BigInteger))
