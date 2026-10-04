import io
import pickle
import tempfile
import unittest
from pathlib import Path

from sum_contracts.models import Metadata, ServiceError, validate_progress
from sum_indexer.embeddings import validate_vectors
from sum_indexer.extractors import ExtractorRegistry, TextExtractor
from sum_storage.objects import LocalStorage


class ContractsTests(unittest.TestCase):
    def test_metadata_preserves_academic_scope(self):
        metadata = Metadata.parse(
            {
                "titulo": "Plan de estudios",
                "tipo_documento": "plan_estudios",
                "prioridad": "alta",
                "version_curricular": "2023",
                "periodos_aplicables": ["2026-II"],
                "relaciones": ["modifica:RR-001"],
            }
        )
        self.assertEqual(metadata.version_curricular, "2023")
        self.assertEqual(metadata.periodos_aplicables, ("2026-II",))
        self.assertEqual(Metadata.parse(metadata.to_dict()), metadata)

    def test_invalid_metadata_is_rejected(self):
        for extra in [
            {"prioridad": "urgent"},
            {"idioma": "de"},
            {"tipo_documento": "PDF"},
            {"relaciones": "RR"},
            {"fecha_emision": "ayer"},
            {"vigente_desde": "2027-01-01", "vigente_hasta": "2026-01-01"},
            {"owner_id": "other-user"},
        ]:
            with self.subTest(extra=extra), self.assertRaises(ServiceError):
                Metadata.parse({"titulo": "Documento", "tipo_documento": "otro", **extra})

    def test_errors_survive_multiprocessing_serialization(self):
        original = ServiceError("ARCHIVO_INVALIDO", "El archivo no se puede leer.")
        restored = pickle.loads(pickle.dumps(original))
        self.assertEqual(restored.code, original.code)
        self.assertEqual(str(restored), original.message)

    def test_progress_disallows_negative_and_unknown_counters(self):
        valid = {
            "operation_id": "p1",
            "stage": "extrayendo",
            "message": "Página procesada.",
            "counts": {"paginas": 1},
        }
        self.assertEqual(validate_progress(valid), valid)
        for counts in [{"paginas": -1}, {"paginas": True}, {"secreto": 2}]:
            with self.assertRaises(ServiceError):
                validate_progress({**valid, "counts": counts})

    def test_vectors_reject_missing_nan_wrong_dimensions_and_zero(self):
        for vectors in [[], [[1.0, 2.0]], [[float("nan"), 0.0, 1.0]], [[0.0, 0.0, 0.0]]]:
            with self.assertRaises(ServiceError):
                validate_vectors(vectors, 1, 3)
        result = validate_vectors([[3.0, 4.0, 0.0]], 1, 3)
        self.assertAlmostEqual(result[0][0], 0.6)

    def test_registry_can_add_formats_without_changing_the_pipeline(self):
        registry = ExtractorRegistry({"text/custom": TextExtractor})
        self.assertIsInstance(registry.resolve("text/custom"), TextExtractor)
        with self.assertRaises(ServiceError):
            registry.resolve("application/unknown")


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.storage = LocalStorage(Path(self.directory.name))

    def test_local_storage_roundtrip_and_path_escape_protection(self):
        self.storage.put("derived/job/text.txt", io.BytesIO("Español académico".encode()))
        self.assertEqual(self.storage.read("derived/job/text.txt").decode(), "Español académico")
        for key in ["../escape", "/tmp/escape", "derived/../../escape", "..\\escape"]:
            with self.assertRaises(ValueError):
                self.storage.read(key)

    def test_failed_write_preserves_existing_object(self):
        class BrokenStream:
            def read(self, *args):
                raise OSError("Interrupted upload")

        self.storage.put("originals/source", io.BytesIO(b"original"))
        with self.assertRaises(OSError):
            self.storage.put("originals/source", BrokenStream())
        self.assertEqual(self.storage.read("originals/source"), b"original")
        self.assertEqual(list(Path(self.directory.name).rglob("*.tmp")), [])
