"""Small SQLAlchemy Core adapter shared by the independent service repositories."""

from __future__ import annotations

import re
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection, Engine

_POSITIONAL = re.compile(r"%s")


class SqlConnection:
    """SQLAlchemy connection exposing mapping results and legacy positional binds."""

    def __init__(self, connection: Connection):
        self._connection = connection

    def execute(self, statement: str, parameters: Any = ()):
        keys: list[str] = []
        sql = _POSITIONAL.sub(lambda _: self._next_key(keys), statement)
        clause = text(sql)

        def prepare(values):
            nonlocal clause
            if isinstance(values, Mapping):
                result = dict(values)
            else:
                result = {key: value for key, value in zip(keys, values, strict=True)}
            for key, value in result.items():
                if isinstance(value, (dict, list)):
                    clause = clause.bindparams(bindparam(key, type_=JSONB))
            return result

        if (
            isinstance(parameters, list)
            and parameters
            and isinstance(parameters[0], (Mapping, tuple, list))
        ):
            values = [prepare(item) for item in parameters]
        else:
            values = prepare(parameters)
        return self._connection.execute(clause, values).mappings()

    @staticmethod
    def _next_key(keys: list[str]) -> str:
        key = f"p{len(keys)}"
        keys.append(key)
        return f":{key}"


class SqlDatabase:
    """Owns one SQLAlchemy Engine and bounds its per-process connection pool."""

    def __init__(self, url: str, pool_size: int, statement_timeout_ms: int):
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url.removeprefix("postgres://")
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
        self.engine: Engine = create_engine(
            url,
            pool_size=pool_size,
            max_overflow=0,
            pool_pre_ping=True,
            pool_timeout=3,
            connect_args={"connect_timeout": 3, "options": f"-c statement_timeout={statement_timeout_ms}"},
        )

    def open(self) -> None:
        with self.engine.connect():
            pass

    def close(self) -> None:
        self.engine.dispose()

    @contextmanager
    def connection(self):
        with self.engine.begin() as connection:
            yield SqlConnection(connection)
