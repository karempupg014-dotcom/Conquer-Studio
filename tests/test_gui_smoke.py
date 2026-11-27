"""Windows/PySide6 smoke test for the desktop texture viewer."""
import os
import struct
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from conquer_studio.dds import inspect_dds
    from conquer_studio.gui import ConquerStudioWindow
except ImportError:
    QApplication = None
    inspect_dds = None
    ConquerStudioWindow = None


def tiny_bc1_dds():
    data = bytearray(136)
    data[:4] = b"DDS "
    struct.pack_into("<7I", data, 4, 124, 0x81007, 4, 4, 8, 0, 1)
    struct.pack_into("<II", data, 76, 32, 0x4)
    data[84:88] = b"DXT1"
    struct.pack_into("<HHI", data, 128, 0xF800, 0x07E0, 0)
    return bytes(data)


@unittest.skipIf(QApplication is None, "PySide6 desktop dependency is not installed")
class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_window_starts_and_renders_a_texture(self):
        window = ConquerStudioWindow()
        data = tiny_bc1_dds()
        meta = inspect_dds(data)
        window.selected_data = data
        window.selected_meta = meta
        window.selected_name = "smoke-test"
        window.show_texture(data, meta, "smoke-test")
        self.assertEqual(window.windowTitle(), "Conquer Studio")
        self.assertIsNotNone(window.preview.pixmap())
        self.assertFalse(window.preview.pixmap().isNull())
        self.assertIn("BC1", window.details.toPlainText())
        window.close()


if __name__ == "__main__":
    unittest.main()
