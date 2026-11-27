import struct
import tempfile
import unittest
from pathlib import Path
from conquer_studio.dds import (
    DDSFormatError, inspect_dds, decode_bc1_rgba, decode_bc2_rgba,
    decode_bc3_rgba, encode_rgba_png, convert_bc1_dds_to_png,
    convert_bc2_dds_to_png, convert_bc3_dds_to_png,
)

def make_dds(width=128, height=64, fourcc=b"DXT1", payload_size=4096):
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


    def test_decode_bc1_red_block(self):
        data = bytearray(make_dds(width=4, height=4, payload_size=8))
        struct.pack_into("<HHI", data, 128, 0xF800, 0x07E0, 0)
        width, height, rgba = decode_bc1_rgba(bytes(data))
        self.assertEqual((width, height), (4, 4))
        self.assertEqual(rgba[:4], bytes((255, 0, 0, 255)))
        self.assertEqual(len(rgba), 4 * 4 * 4)

    def test_bc1_png_export(self):
        data = bytearray(make_dds(width=4, height=4, payload_size=8))
        struct.pack_into("<HHI", data, 128, 0xF800, 0x07E0, 0)
        png = encode_rgba_png(4, 4, decode_bc1_rgba(bytes(data))[2])
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "texture.png"
            self.assertEqual(convert_bc1_dds_to_png(bytes(data), str(target)), (4, 4))
            self.assertTrue(target.read_bytes().startswith(b"\\x89PNG\\r\\n\\x1a\\n"))

    def test_bc1_rejects_other_formats(self):
        data = make_dds(width=4, height=4, fourcc=b"DXT5", payload_size=16)
        with self.assertRaises(DDSFormatError):
            decode_bc1_rgba(data)


    def test_decode_bc2_explicit_alpha(self):
        data = bytearray(make_dds(width=4, height=4, fourcc=b"DXT3", payload_size=16))
        data[128:136] = bytes([0xFF]) * 8
        struct.pack_into("<HHI", data, 136, 0xF800, 0x07E0, 0)
        width, height, rgba = decode_bc2_rgba(bytes(data))
        self.assertEqual((width, height), (4, 4))
        self.assertEqual(rgba[:4], bytes((255, 0, 0, 255)))

    def test_decode_bc3_interpolated_alpha(self):
        data = bytearray(make_dds(width=4, height=4, fourcc=b"DXT5", payload_size=16))
        data[128:136] = bytes((255, 0, 0, 0, 0, 0, 0, 0))
        struct.pack_into("<HHI", data, 136, 0xF800, 0x07E0, 0)
        width, height, rgba = decode_bc3_rgba(bytes(data))
        self.assertEqual((width, height), (4, 4))
        self.assertEqual(rgba[:4], bytes((255, 0, 0, 255)))

    def test_bc2_bc3_png_export_and_real_signature(self):
        self.assertTrue(encode_rgba_png(1, 1, bytes((1, 2, 3, 4))).startswith(
            bytes((137, 80, 78, 71, 13, 10, 26, 10))
        ))
        for fourcc, converter in ((b"DXT3", convert_bc2_dds_to_png),
                                  (b"DXT5", convert_bc3_dds_to_png)):
            data = make_dds(width=4, height=4, fourcc=fourcc, payload_size=16)
            with tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / "texture.png"
                self.assertEqual(converter(data, str(target)), (4, 4))
                self.assertTrue(target.read_bytes().startswith(
                    bytes((137, 80, 78, 71, 13, 10, 26, 10))
                ))

    def test_bc2_bc3_reject_wrong_format(self):
        with self.assertRaises(DDSFormatError):
            decode_bc2_rgba(make_dds(width=4, height=4, fourcc=b"DXT1", payload_size=8))
        with self.assertRaises(DDSFormatError):
            decode_bc3_rgba(make_dds(width=4, height=4, fourcc=b"DXT1", payload_size=8))

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
