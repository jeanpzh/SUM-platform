"""Shared strict base for student projections and deterministic results."""

from pydantic import BaseModel, ConfigDict


class StudentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
