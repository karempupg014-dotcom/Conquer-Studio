import struct
import unittest

from tools.c3_phy4_candidate_probe import probe_section


def make_section(vertex_count=3, indices=(0, 1, 2), declared_length=None):
    name = b"v_body"
    header = struct.pack("<I", len(name)) + name
    header += struct.pack("<III", 1, vertex_count, 0)
    vertices = b"".join(
        struct.pack("<3f2fIII2f", float(i), 0.0, 0.0, 0.0, 1.0,
                    0, 1, 2, 0.5, 0.5)
        for i in range(vertex_count)
    )
    index_data = struct.pack("<II", len(indices), 0)
    if indices:
        index_data += struct.pack("<" + "H" * len(indices), *indices)
    payload = header + vertices + index_data
    length = len(payload) if declared_length is None else declared_length
    return b"PHY4" + struct.pack("<I", length) + payload


class C3Phy4CandidateProbeTests(unittest.TestCase):
    def test_marks_multiple_of_three_as_candidate_only(self):
        data = make_section()
        result = probe_section(data, 0)
        self.assertTrue(result["candidate"])
        index_info = result["candidate_index_buffer"]
        self.assertTrue(index_info["recognized"])
        self.assertTrue(index_info["triangle_list_candidate"])
        self.assertEqual(
            index_info["topology_status"],
            "count_is_multiple_of_three_only_not_proof_of_triangle_list",
        )

    def test_non_multiple_of_three_is_not_triangle_list_candidate(self):
        data = make_section(indices=(0, 1))
        result = probe_section(data, 0)
        index_info = result["candidate_index_buffer"]
        self.assertTrue(index_info["recognized"])
        self.assertFalse(index_info["triangle_list_candidate"])

    def test_rejects_vertex_stream_that_exceeds_section(self):
        data = make_section(vertex_count=3, declared_length=22)
        result = probe_section(data, 0)
        self.assertFalse(result["candidate"])
        self.assertIn("does not fit section", result["reason"])


if __name__ == "__main__":
    unittest.main()
