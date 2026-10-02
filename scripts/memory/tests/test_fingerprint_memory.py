"""Fixture-only tests; no DB, no model, no runtime side effects."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "fingerprint_memory", Path(__file__).resolve().parents[1] / "fingerprint_memory.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(memory_id="M001"):
    value = {column: None for column in module.LOGICAL_COLUMNS + module.VECTOR_COLUMNS}
    value.update(memory_id=memory_id, user_id="U01",
                 timestamp="2026-09-01T12:00:00.000000",
                 textual_summary="Mesa y espacio lateral", metadata='{"a": 1, "b": 2}',
                 importance="0.5", confidence="1", embedding="[0.1,0.2]",
                 episodic_embedding="[0.3,0.4]")
    return value


class FingerprintTests(unittest.TestCase):
    def test_order_independent(self):
        first, second = row(), row("M002")
        self.assertEqual(module.fingerprint_rows([first, second]),
                         module.fingerprint_rows([second, first]))

    def test_metadata_decimal_precision_preserved(self):
        first, second = row(), row()
        first["metadata"] = '{"number": 0.123456789012345678901}'
        second["metadata"] = '{"number": 0.123456789012345678902}'
        self.assertNotEqual(module.fingerprint_rows([first]), module.fingerprint_rows([second]))

    def test_null_is_distinct_from_empty(self):
        first, second = row(), row()
        second["goal"] = ""
        self.assertNotEqual(module.fingerprint_rows([first])["logical_sha256"],
                            module.fingerprint_rows([second])["logical_sha256"])

    def test_embedding_change_separate(self):
        first, second = row(), row()
        second["embedding"] = "[0.2,0.1]"
        a, b = module.fingerprint_rows([first]), module.fingerprint_rows([second])
        self.assertEqual(a["logical_sha256"], b["logical_sha256"])
        self.assertNotEqual(a["embeddings_sha256"], b["embeddings_sha256"])

    def test_content_change_separate(self):
        first, second = row(), row()
        second["outcome"] = "correcto"
        a, b = module.fingerprint_rows([first]), module.fingerprint_rows([second])
        self.assertNotEqual(a["logical_sha256"], b["logical_sha256"])
        self.assertEqual(a["embeddings_sha256"], b["embeddings_sha256"])

    def test_stored_timestamp_protected(self):
        first, second = row(), row()
        second["timestamp"] = "2026-09-02T12:00:00.000000"
        self.assertNotEqual(module.fingerprint_rows([first]), module.fingerprint_rows([second]))

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            module.fingerprint_rows([row(), row()])

    def test_missing_column_rejected(self):
        value = row()
        del value["metadata"]
        with self.assertRaises(KeyError):
            module.fingerprint_rows([value])

    def test_empty_deterministic_and_count(self):
        value = module.fingerprint_rows([])
        self.assertEqual(value, module.fingerprint_rows([]))
        self.assertEqual(value["row_count"], 0)
        self.assertEqual(len(value["logical_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
