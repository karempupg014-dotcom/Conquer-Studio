import struct
import unittest
from conquer_studio.dds import DDSFormatError, inspect_dds

def make_dds(width=128, height=64, fourcc=b"DXT1", payload_size=1024):
    header = bytearray(128 + payload_size)
    header[:4] = b"DDS "
    struct.pack_into("<7I", header, 4, 124, 0x81007, height, width, payload_size, 0, 1)
    struct.pack_into("<II", header, 76, 32, 0x4)
    header[84:88] = fourcc
    return bytes(header)

class DDSTests(unittest.TestCase):
    def test_dxt1_dimensions_and_payload(self):
        result = inspect_dds(make_dds())
        self.assertEqual(result["format"], "BC1")
        self.assertEqual(result["width"], 128)
        self.assertTrue(result["base_level_fits"])

    def test_reject_truncated_header(self):
        with self.assertRaises(DDSFormatError):
            inspect_dds(b"DDS " + bytes(20))

    def test_reject_invalid_dimensions(self):
        with self.assertRaises(DDSFormatError):
            inspect_dds(make_dds(width=0))

    def test_detect_short_payload(self):
        result = inspect_dds(make_dds(payload_size=1))
        self.assertFalse(result["base_level_fits"])

if __name__ == "__main__":
    unittest.main()
