import struct
import tempfile
import unittest
from pathlib import Path

from conquer_studio.texture_export import export_wdf_textures


def make_dds(fourcc=b"DXT1"):
    data = bytearray(136)
    data[:4] = b"DDS "
    struct.pack_into("<7I", data, 4, 124, 0x81007, 4, 4, 8, 0, 1)
    struct.pack_into("<II", data, 76, 32, 0x4)
    data[84:88] = fourcc
    struct.pack_into("<HHI", data, 128, 0xF800, 0x07E0, 0)
    return bytes(data)


def make_wdf(path: Path, payloads):
    header_size = 12
    offset = header_size
    entries = []
    body = bytearray()
    for file_id, payload in payloads:
        entries.append(struct.pack("<IIII", file_id, offset, len(payload), 0))
        body.extend(payload)
        offset += len(payload)
    index_offset = offset
    path.write_bytes(
        struct.pack("<4sII", b"PFDW", len(entries), index_offset)
        + body + b"".join(entries)
    )


class TextureExportTests(unittest.TestCase):
    def test_export_supported_texture_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "sample.wdf"
            make_wdf(archive, [(0xAABBCCDD, make_dds()), (0x12345678, b"not a texture")])
            output = root / "textures"
            result = export_wdf_textures(archive, output)
            self.assertEqual(result["counts"]["exported"], 1)
            self.assertEqual(result["counts"]["not_dds"], 1)
            png = (output / "AABBCCDD.png").read_bytes()
            self.assertTrue(png.startswith(bytes((137, 80, 78, 71, 13, 10, 26, 10))))
            self.assertTrue((output / "texture-export-manifest.json").is_file())

    def test_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "sample.wdf"
            make_wdf(archive, [(0xAABBCCDD, make_dds())])
            output = root / "textures"
            output.mkdir()
            (output / "AABBCCDD.png").write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                export_wdf_textures(archive, output)
            self.assertEqual((output / "AABBCCDD.png").read_bytes(), b"keep")

    def test_refuse_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "sample.wdf"
            make_wdf(archive, [(1, make_dds()), (1, make_dds())])
            with self.assertRaises(ValueError):
                export_wdf_textures(archive, root / "textures")


if __name__ == "__main__":
    unittest.main()
