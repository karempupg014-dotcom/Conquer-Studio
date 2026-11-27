"""Windows/PySide6 smoke test for the desktop texture viewer."""
import os
import struct
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QListWidgetItem
    from conquer_studio.dds import inspect_dds
    from conquer_studio.gui import ConquerStudioWindow
    from conquer_studio.wdf import WDFArchive
except ImportError:
    QApplication = None
    inspect_dds = None
    ConquerStudioWindow = None
    WDFArchive = None
    Qt = None
    QListWidgetItem = None


def tiny_bc1_dds(color=0xF800):
    data = bytearray(136)
    data[:4] = b"DDS "
    struct.pack_into("<7I", data, 4, 124, 0x81007, 4, 4, 8, 0, 1)
    struct.pack_into("<II", data, 76, 32, 0x4)
    data[84:88] = b"DXT1"
    struct.pack_into("<HHI", data, 128, color, 0x07E0, 0)
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

    def test_duplicate_wdf_ids_select_the_exact_entry(self):
        first = tiny_bc1_dds(0xF800)
        second = tiny_bc1_dds(0x001F)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicates.wdf"
            first_offset = 12
            second_offset = first_offset + len(first)
            index_offset = second_offset + len(second)
            path.write_bytes(
                struct.pack("<4sII", b"PFDW", 2, index_offset)
                + first + second
                + struct.pack("<IIII", 0x1234, first_offset, len(first), 0)
                + struct.pack("<IIII", 0x1234, second_offset, len(second), 0)
            )
            archive = WDFArchive.open(path)
            window = ConquerStudioWindow()
            window.archive = archive
            window.texture_entries = [
                (entry, inspect_dds(payload))
                for entry, payload in zip(archive.entries, (first, second))
            ]
            item = QListWidgetItem("duplicate second entry")
            item.setData(Qt.ItemDataRole.UserRole, 1)
            window.select_texture(item)
            self.assertEqual(window.selected_data, second)
            window.close()

    def test_open_catalog_and_filter_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps({
                "root_name": "Game",
                "assets": [
                    {"path": "c3/monster/1.c3", "format": "c3", "size": 123},
                    {"path": "texture/grass.dds", "format": "dds", "size": 456},
                    {"path": None, "format": "invalid"}
                ]
            }), encoding="utf-8")
            window = ConquerStudioWindow()
            with patch("conquer_studio.gui.QFileDialog.getOpenFileName", return_value=(str(path), "JSON")):
                window.open_catalog()
            self.assertEqual(window.catalog_list.count(), 2)
            self.assertEqual(window.catalog_root_name, "Game")
            window.filter_items("grass")
            self.assertTrue(window.catalog_list.item(0).isHidden())
            self.assertFalse(window.catalog_list.item(1).isHidden())
            window.catalog_list.setCurrentRow(0)
            self.assertIn("c3/monster/1.c3", window.details.toPlainText())
            window.close()


if __name__ == "__main__":
    unittest.main()
