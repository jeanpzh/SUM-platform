"""Run against the composed backend's real database role:
    docker compose exec -T backend python - < tests/integration/test_postgres_read_models.py
Fixtures have a private owner and never enqueue indexing or alter user documents.
"""

import os
import unittest
from uuid import uuid4

from sum_backend.repository import PostgresJobs
from sum_contracts.models import ServiceError


class ReadModelTests(unittest.TestCase):
    def setUp(self):
        self.repo = PostgresJobs(os.environ["DATABASE_URL"])
        self.owner = "read-model-test-" + str(uuid4())
        self.doc = str(uuid4())
        with self.repo.database.connection() as conn:
            conn.execute(
                "INSERT INTO application.documents(id,owner_id,current_version_id) VALUES(%s,%s,%s)",
                (self.doc, self.owner, uuid4()),
            )
        self.job, self.version = self.version_fixture("Prueba %_literal")

    def tearDown(self):
        with self.repo.database.connection() as conn:
            for table in ["indexing_stage_attempts", "indexing_events", "outbox"]:
                conn.execute(
                    f"DELETE FROM application.{table} WHERE job_id IN (SELECT id FROM application.indexing_jobs WHERE owner_id=%s)",
                    (self.owner,),
                )
            conn.execute("DELETE FROM application.publications WHERE document_id=%s", (self.doc,))
            conn.execute("DELETE FROM application.indexing_jobs WHERE owner_id=%s", (self.owner,))
            conn.execute(
                "DELETE FROM application.document_versions WHERE document_id=%s", (self.doc,)
            )
            conn.execute("DELETE FROM application.documents WHERE id=%s", (self.doc,))
        self.repo.close()

    def version_fixture(self, title):
        job, version = str(uuid4()), str(uuid4())
        with self.repo.database.connection() as conn:
            conn.execute(
                "INSERT INTO application.document_versions(id,document_id,metadata,object_key,mime_type,sha256,size_bytes) VALUES(%s,%s,%s,%s,'application/pdf',%s,10)",
                (
                    version,
                    self.doc,
                    {"titulo": title, "tipo_documento": "otro"},
                    "test/" + version,
                    "a" * 64,
                ),
            )
            conn.execute(
                "INSERT INTO application.indexing_jobs(id,document_id,version_id,owner_id,idempotency_key,fingerprint,priority) VALUES(%s,%s,%s,%s,%s,'test',0)",
                (job, self.doc, version, self.owner, job),
            )
            conn.execute(
                "UPDATE application.documents SET current_version_id=%s WHERE id=%s",
                (version, self.doc),
            )
        return job, version

    def manifest(self, job, version):
        return {
            "generation_id": job,
            "document_id": self.doc,
            "version_id": version,
            "chunks": 1,
            "profile": {"model": "test", "revision": "fixed", "dimension": 3, "max_tokens": 512},
            "pipeline_version": "test-v1",
            "text_key": "test/text",
        }

    def start(self, attempt):
        return self.repo.timing(
            self.job, {"attempt_id": attempt, "stage": "validando", "action": "start"}
        )

    def end(self, attempt, duration=123.456):
        return self.repo.timing(
            self.job,
            {
                "attempt_id": attempt,
                "stage": "validando",
                "action": "end",
                "duration_ms": duration,
                "outcome": "completado",
            },
        )

    def test_timings_are_idempotent_and_survive_a_new_repository(self):
        attempt = str(uuid4())
        started = self.start(attempt)
        self.assertEqual(self.start(attempt)["secuencia"], started["secuencia"])
        ended = self.end(attempt)
        self.assertEqual(self.end(attempt, 999)["secuencia"], ended["secuencia"])
        other = PostgresJobs(os.environ["DATABASE_URL"])
        try:
            timings = other.get(self.job, self.owner)["tiempos"]
        finally:
            other.close()
        self.assertEqual(timings["activo_ms"], 123.456)
        self.assertEqual(len(timings["intentos"]), 1)
        self.assertIsNotNone(timings["intentos"][0]["fin"])
        self.assertGreaterEqual(timings["cola_inicial_ms"], 0)
        for invalid in [-1, float("nan"), float("inf"), True]:
            with self.assertRaises(ServiceError):
                self.end(attempt, invalid)

    def test_crashed_attempt_stays_unknown_when_a_retry_starts(self):
        old, retry = str(uuid4()), str(uuid4())
        self.start(old)
        self.start(retry)
        self.end(retry, 10)
        self.end(old, 999)
        times = self.repo.get(self.job, self.owner)["tiempos"]
        self.assertEqual(times["activo_ms"], 10)
        self.assertEqual(times["intentos"][0]["resultado"], "interrumpido")
        self.assertIsNone(times["intentos"][0]["duracion_ms"])

    def test_catalogue_is_owner_scoped_and_search_wildcards_are_literal(self):
        self.assertEqual(self.repo.library.list(self.owner)["total"], 0)
        self.repo.complete(self.job, self.manifest(self.job, self.version))
        found = self.repo.library.list(self.owner, "%_literal", limit=1)
        self.assertEqual(found["total"], 1)
        self.assertEqual(found["documentos"][0]["version_id"], self.version)
        self.assertEqual(self.repo.library.list("another-owner")["total"], 0)
        self.assertEqual(self.repo.library.list(self.owner, offset=1)["documentos"], [])
        with self.assertRaises(ServiceError) as denied:
            self.repo.library.chunks(self.doc, "another-owner")
        self.assertEqual(denied.exception.status, 404)

    def test_previous_publication_remains_visible_until_new_version_completes(self):
        self.repo.complete(self.job, self.manifest(self.job, self.version))
        new_job, new_version = self.version_fixture("Versión nueva")
        self.assertEqual(
            self.repo.library.list(self.owner)["documentos"][0]["version_id"], self.version
        )
        self.repo.complete(new_job, self.manifest(new_job, new_version))
        latest = self.repo.library.list(self.owner)
        self.assertEqual(latest["total"], 1)
        self.assertEqual(latest["documentos"][0]["version_id"], new_version)
        with self.assertRaises(ServiceError) as changed:
            self.repo.library.chunks(self.doc, self.owner, version_id=self.version)
        self.assertEqual(changed.exception.code, "VERSION_CAMBIADA")


if __name__ == "__main__":
    unittest.main(verbosity=2)
