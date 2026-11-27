import unittest
from tools.wdf_audit import classify

class WDFSignatureTests(unittest.TestCase):
    def test_known_signatures(self):
        self.assertEqual(classify(b"MAXFILE C3 00001"), "C3")
        self.assertEqual(classify(b"DDS "), "DDS")
        self.assertEqual(classify(b"\x89PNG\r\n\x1a\n"), "PNG")
        self.assertEqual(classify(b"\xff\xd8\xff\xe0"), "JPEG")
        self.assertEqual(classify(b"BM"), "BMP")

    def test_unknown_signature(self):
        self.assertEqual(classify(b"not a known asset"), "UNKNOWN")

if __name__ == "__main__":
    unittest.main()
