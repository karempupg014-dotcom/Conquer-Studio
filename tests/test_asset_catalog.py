from pathlib import Path
import struct
import tempfile
import unittest
from conquer_studio.catalog import scan_assets
from conquer_studio.formats import inspect_file, C3_SIGNATURE

class AssetCatalogTests(unittest.TestCase):
    def test_c3_signature_and_tag_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.c3"
            p.write_bytes(C3_SIGNATURE + b"PHY4" + b"MOTI" + b"PHY4")
            result = inspect_file(p)
            self.assertEqual(result["format"], "c3")
            self.assertEqual(result["details"]["tag_counts"]["PHY4"], 2)

    def test_dds_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.dds"
            header = bytearray(128)
            header[:4] = b"DDS "
            struct.pack_into("<7I", header, 4, 124, 0x1007, 64, 128, 0, 0, 1)
            struct.pack_into("<I", header, 76, 32)
            p.write_bytes(header)
            result = inspect_file(p)
            self.assertEqual(result["format"], "dds")
            self.assertTrue(result["details"]["header_valid"])
            self.assertEqual(result["details"]["width"], 128)

    def test_catalog_skips_text_and_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "model.c3").write_bytes(C3_SIGNATURE)
            (root / "private.txt").write_text("do not index")
            (root / "client.exe").write_bytes(b"MZ")
            result = scan_assets(root)
            self.assertEqual(result["asset_count"], 1)
            self.assertEqual(result["assets"][0]["path"], "model.c3")
            self.assertEqual(result["skipped_count"], 2)

if __name__ == "__main__":
    unittest.main()
