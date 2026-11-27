"""Optional PySide6 desktop interface for browsing Conquer textures."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import (
        QApplication, QFileDialog, QLabel, QLineEdit, QListWidget,
        QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
        QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QSplitter,
    )
except ImportError as exc:  # pragma: no cover - depends on optional desktop extra
    raise SystemExit(
        "The desktop interface requires PySide6. Install it with: "
        "python -m pip install -e '.[gui]'"
    ) from exc

from .dds import (
    DDSFormatError, decode_bc1_rgba, decode_bc2_rgba, decode_bc3_rgba,
    convert_bc1_dds_to_png, convert_bc2_dds_to_png, convert_bc3_dds_to_png,
    inspect_dds,
)
from .texture_export import export_wdf_textures
from .wdf import WDFArchive

DECODERS = {
    "BC1": decode_bc1_rgba, "BC1_UNORM": decode_bc1_rgba, "BC1_SRGB": decode_bc1_rgba,
    "BC2": decode_bc2_rgba, "BC2_UNORM": decode_bc2_rgba, "BC2_SRGB": decode_bc2_rgba,
    "BC3": decode_bc3_rgba, "BC3_UNORM": decode_bc3_rgba, "BC3_SRGB": decode_bc3_rgba,
}
CONVERTERS = {
    "BC1": convert_bc1_dds_to_png, "BC1_UNORM": convert_bc1_dds_to_png,
    "BC1_SRGB": convert_bc1_dds_to_png, "BC2": convert_bc2_dds_to_png,
    "BC2_UNORM": convert_bc2_dds_to_png, "BC2_SRGB": convert_bc2_dds_to_png,
    "BC3": convert_bc3_dds_to_png, "BC3_UNORM": convert_bc3_dds_to_png,
    "BC3_SRGB": convert_bc3_dds_to_png,
}


class ConquerStudioWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Conquer Studio")
        self.resize(1420, 880)
        self.archive: WDFArchive | None = None
        self.texture_entries = []
        self.selected_data: bytes | None = None
        self.selected_meta: dict | None = None
        self.selected_name = ""

        root = QWidget()
        layout = QVBoxLayout(root)
        toolbar = QHBoxLayout()
        for label, callback in (
            ("فتح WDF", self.open_wdf),
            ("فتح DDS", self.open_dds),
            ("تصدير الخامة", self.export_selected),
            ("تصدير كل خامات WDF", self.export_all),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.filter_box = QLineEdit()
        self.filter_box.setPlaceholderText("ابحث باسم الخامة أو ID...")
        self.filter_box.textChanged.connect(self.filter_items)
        left_layout.addWidget(self.filter_box)
        self.texture_list = QListWidget()
        self.texture_list.currentItemChanged.connect(self.select_texture)
        left_layout.addWidget(self.texture_list)
        splitter.addWidget(left)

        self.preview = QLabel("افتح ملف WDF أو DDS لعرض الخامات")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(480, 420)
        self.preview.setStyleSheet("background:#171b22;color:#aab4c3;border:1px solid #303846;")
        splitter.addWidget(self.preview)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("معلومات الخامة ستظهر هنا")
        self.details.setMinimumWidth(280)
        splitter.addWidget(self.details)
        splitter.setSizes([300, 800, 320])
        layout.addWidget(splitter, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage("جاهز — لم يتم تعديل ملفات اللعبة الأصلية")

        self.setStyleSheet("""
            QMainWindow, QWidget { background:#202630; color:#e7edf5; }
            QPushButton { background:#354253; border:1px solid #4b5b70; padding:8px 12px; border-radius:5px; }
            QPushButton:hover { background:#465970; }
            QLineEdit, QListWidget, QPlainTextEdit { background:#171d26; color:#e7edf5; border:1px solid #394555; padding:6px; }
        """)

    def open_wdf(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "فتح أرشيف WDF", "", "WDF Archives (*.wdf);;All files (*)")
        if not filename:
            return
        try:
            archive = WDFArchive.open(Path(filename))
            entries = []
            skipped = 0
            for entry in archive.entries:
                payload = archive.read_entry(entry)
                if not payload.startswith(b"DDS "):
                    skipped += 1
                    continue
                try:
                    meta = inspect_dds(payload)
                except DDSFormatError:
                    skipped += 1
                    continue
                if meta["format"] not in DECODERS or not meta["base_level_fits"]:
                    skipped += 1
                    continue
                entries.append((entry, meta))
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "تعذر فتح WDF", str(exc))
            return

        self.archive = archive
        self.texture_entries = entries
        self.selected_data = None
        self.selected_meta = None
        self.texture_list.clear()
        id_counts = {}
        for entry, _meta in entries:
            id_counts[entry.file_id] = id_counts.get(entry.file_id, 0) + 1
        for entry_index, (entry, meta) in enumerate(entries):
            duplicate_note = "  |  مكرر" if id_counts[entry.file_id] > 1 else ""
            label = (
                f"{entry.file_id:08X}  |  {meta['format']}  |  "
                f"{meta['width']}×{meta['height']}{duplicate_note}"
            )
            item = QListWidgetItem(label)
            # Store the archive entry's position, not its hash ID: IDs may repeat.
            item.setData(Qt.ItemDataRole.UserRole, entry_index)
            self.texture_list.addItem(item)
        self.details.clear()
        self.preview.setText("اختر خامة من القائمة")
        self.statusBar().showMessage(
            f"{Path(filename).name}: {len(entries)} خامة قابلة للعرض، {skipped} عنصر غير مدعوم أو غير DDS"
        )

    def open_dds(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "فتح خامة DDS", "", "DDS Textures (*.dds);;All files (*)")
        if not filename:
            return
        try:
            data = Path(filename).read_bytes()
            meta = inspect_dds(data)
            if meta["format"] not in DECODERS or not meta["base_level_fits"]:
                raise DDSFormatError(f"صيغة غير مدعومة أو بيانات ناقصة: {meta['format']}")
            self.archive = None
            self.texture_entries = []
            self.texture_list.clear()
            self.selected_data = data
            self.selected_meta = meta
            self.selected_name = Path(filename).name
            self.show_texture(data, meta, self.selected_name)
        except (OSError, DDSFormatError) as exc:
            QMessageBox.critical(self, "تعذر فتح DDS", str(exc))

    def filter_items(self, text: str) -> None:
        needle = text.casefold().strip()
        for index in range(self.texture_list.count()):
            item = self.texture_list.item(index)
            item.setHidden(needle not in item.text().casefold())

    def select_texture(self, current: QListWidgetItem | None, previous: QListWidgetItem | None = None) -> None:
        if current is None or self.archive is None:
            return
        entry_index = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(entry_index, int) or not 0 <= entry_index < len(self.texture_entries):
            return
        entry, meta = self.texture_entries[entry_index]
        file_id = entry.file_id
        try:
            data = self.archive.read_entry(entry)
            self.selected_data = data
            self.selected_meta = meta
            self.selected_name = f"{file_id:08X}"
            self.show_texture(data, meta, self.selected_name)
        except (OSError, DDSFormatError, ValueError) as exc:
            QMessageBox.warning(self, "خطأ في الخامة", str(exc))

    def show_texture(self, data: bytes, meta: dict, name: str) -> None:
        decoder = DECODERS[meta["format"]]
        width, height, rgba = decoder(data)
        image = QImage(rgba, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()
        pixmap = QPixmap.fromImage(image)
        self.preview.setPixmap(pixmap.scaled(
            self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        self.details.setPlainText(
            f"اسم/ID: {name}\n"
            f"الصيغة: {meta['format']}\n"
            f"الأبعاد: {width} × {height}\n"
            f"Mipmaps: {meta['mipmaps']}\n"
            f"حجم البيانات: {meta['payload_bytes']} bytes\n"
            f"بداية بيانات الصورة: {meta['data_offset']}\n"
            "المعاينة: المستوى الأول فقط"
        )
        self.statusBar().showMessage(f"تم عرض {name} — {width}×{height}")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.selected_data is not None and self.selected_meta is not None:
            self.show_texture(self.selected_data, self.selected_meta, self.selected_name)

    def export_selected(self) -> None:
        if self.selected_data is None or self.selected_meta is None:
            QMessageBox.information(self, "تصدير", "اختار خامة الأول.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "حفظ الخامة كصورة", f"{self.selected_name}.png", "PNG Image (*.png)")
        if not filename:
            return
        if Path(filename).exists():
            QMessageBox.warning(self, "التصدير", "الملف موجود بالفعل. اختار اسمًا آخر لحماية الملف القديم.")
            return
        try:
            converter = CONVERTERS[self.selected_meta["format"]]
            converter(self.selected_data, filename)
            self.statusBar().showMessage(f"تم التصدير: {filename}")
        except (OSError, DDSFormatError, ValueError) as exc:
            QMessageBox.critical(self, "فشل التصدير", str(exc))

    def export_all(self) -> None:
        if self.archive is None:
            QMessageBox.information(self, "تصدير", "افتح أرشيف WDF الأول.")
            return
        folder = QFileDialog.getExistingDirectory(self, "اختيار مجلد حفظ الخامات")
        if not folder:
            return
        try:
            result = export_wdf_textures(self.archive.path, Path(folder))
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "فشل التصدير", str(exc))
            return
        counts = "\n".join(f"{key}: {value}" for key, value in sorted(result["counts"].items()))
        QMessageBox.information(self, "اكتمل التصدير", f"عدد العناصر: {result['entry_count']}\n{counts}")


def main() -> int:
    app = QApplication(sys.argv)
    window = ConquerStudioWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
