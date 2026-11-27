import struct
import tempfile
import unittest
from pathlib import Path

from tools.c3_phy4_skinning_audit import audit


class C3SkinningAuditTests(unittest.TestCase):
    def test_reports_candidate_id_and_weight_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample.c3"
            records = bytearray()
            for index in range(3):
                records.extend(struct.pack(
                    "<3f2fIII2f",
                    float(index), 1.0, 2.0,
                    0.25, 0.75,
                    7, 2 + index, 3 + index,
                    0.4, 0.6,
                ))
            sample.write_bytes(records)

            result = audit(sample, start=0, count=3)
            diagnostics = result["field_diagnostics"]
            self.assertEqual(diagnostics["distinct_id_values"], 4)
            self.assertEqual(diagnostics["distinct_ordered_id_pairs"], 3)
            self.assertEqual(diagnostics["weight_pairs_summing_to_one"], 3)
            self.assertEqual(
                diagnostics["assessment"],
                "consistent_with_two_normalized_influences",
            )

    def test_does_not_call_out_of_range_weights_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample.c3"
            sample.write_bytes(struct.pack(
                "<3f2fIII2f", 0.0, 0.0, 0.0, 0.0, 0.0,
                0, 1, 2, 1.2, -0.2,
            ))
            result = audit(sample, start=0, count=1)
            diagnostics = result["field_diagnostics"]
            self.assertEqual(diagnostics["weight_pairs_summing_to_one"], 1)
            self.assertEqual(diagnostics["weight_pairs_with_both_values_in_0_to_1"], 0)
            self.assertEqual(diagnostics["assessment"], "inconclusive_candidate_fields")


if __name__ == "__main__":
    unittest.main()
