from pathlib import Path
import struct
import tempfile
import unittest
from conquer_studio.wdf import WDFArchive, WDFFormatError

def make_wdf(path: Path, *, magic=b"PFDW", count=1, index_offset=15, payload=b"hello"):
    # Header + payload + one 16-byte index record.
    header = struct.pack("<4sII", magic, count, index_offset)
    entry = struct.pack("<IIII", 0x1234ABCD, 12, len(payload), 0)
    path.write_bytes(header + payload + entry)

class WDFTests(unittest.TestCase):
    def test_parse_and_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "test.wdf"
            make_wdf(source)
            archive = WDFArchive.open(source)
            self.assertEqual(len(archive.entries), 1)
            self.assertEqual(archive.read_entry(archive.entries[0]), b"hello")
            output = root / "out"
            manifest = archive.extract(output)
            self.assertEqual(manifest["entry_count"], 1)
            self.assertEqual((output / "1234ABCD.bin").read_bytes(), b"hello")

    def test_reject_bad_magic(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.wdf"
            make_wdf(p, magic=b"NOPE")
            with self.assertRaises(WDFFormatError):
                WDFArchive.open(p)

    def test_reject_out_of_bounds_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.wdf"
            p.write_bytes(struct.pack("<4sII", b"PFDW", 9, 12))
            with self.assertRaises(WDFFormatError):
                WDFArchive.open(p)

    def test_reject_payload_overlapping_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.wdf"
            p.write_bytes(struct.pack("<4sII", b"PFDW", 1, 12) +
                          struct.pack("<IIII", 1, 12, 4, 0))
            with self.assertRaises(WDFFormatError):
                WDFArchive.open(p)

if __name__ == "__main__":
    unittest.main()
