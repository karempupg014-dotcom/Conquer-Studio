import json
import tempfile
import unittest
from pathlib import Path

from tools.c3_phy4_compare_audits import compare


class C3Phy4CompareTests(unittest.TestCase):
    def test_compares_shared_ids_and_pairs_without_claiming_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "monster.json"
            second = root / "mount.json"
            first.write_text(json.dumps({
                "file": "monster.c3",
                "candidate": {"count": 10},
                "field_diagnostics": {
                    "candidate_id_frequency": [
                        {"id": 1, "records": 8}, {"id": 2, "records": 2}
                    ],
                    "candidate_id_pair_frequency": [
                        {"ids": [1, 2], "records": 2}
                    ],
                    "assessment": "consistent_with_two_normalized_influences",
                },
            }), encoding="utf-8")
            second.write_text(json.dumps({
                "file": "mount.c3",
                "candidate": {"count": 7},
                "field_diagnostics": {
                    "candidate_id_frequency": [
                        {"id": 2, "records": 4}, {"id": 3, "records": 3}
                    ],
                    "candidate_id_pair_frequency": [
                        {"ids": [1, 2], "records": 1}, {"ids": [2, 3], "records": 3}
                    ],
                    "assessment": "inconclusive_candidate_fields",
                },
            }), encoding="utf-8")

            result = compare([first, second])
            item = result["comparisons"][0]
            self.assertEqual(item["shared_candidate_ids"], [2])
            self.assertEqual(item["shared_ordered_id_pairs"], [[1, 2]])
            self.assertIn("do not prove", item["interpretation"])

    def test_rejects_reports_without_complete_id_distributions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = [root / "a.json", root / "b.json"]
            for path in paths:
                path.write_text(json.dumps({
                    "candidate": {"count": 1},
                    "field_diagnostics": {},
                }), encoding="utf-8")
            with self.assertRaises(ValueError):
                compare(paths)


if __name__ == "__main__":
    unittest.main()
