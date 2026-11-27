"""Batch export of supported DDS textures from WDF archives."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .dds import (
    DDSFormatError,
    convert_bc1_dds_to_png,
    convert_bc2_dds_to_png,
    convert_bc3_dds_to_png,
    inspect_dds,
)
from .wdf import WDFArchive

CONVERTERS = {
    "BC1": convert_bc1_dds_to_png,
    "BC1_UNORM": convert_bc1_dds_to_png,
    "BC1_SRGB": convert_bc1_dds_to_png,
    "BC2": convert_bc2_dds_to_png,
    "BC2_UNORM": convert_bc2_dds_to_png,
    "BC2_SRGB": convert_bc2_dds_to_png,
    "BC3": convert_bc3_dds_to_png,
    "BC3_UNORM": convert_bc3_dds_to_png,
    "BC3_SRGB": convert_bc3_dds_to_png,
}


def export_wdf_textures(archive_path: Path, destination: Path) -> dict:
    """Export supported top-mip textures as HASHID.png without overwriting."""
    archive = WDFArchive.open(Path(archive_path))
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "texture-export-manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"Refusing to overwrite {manifest_path}")

    planned = []
    names = set()
    for entry in archive.entries:
        name = f"{entry.file_id:08X}.png"
        if name in names:
            raise ValueError(f"Duplicate WDF entry ID: {entry.file_id:08X}")
        names.add(name)
        target = destination / name
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite {target}")
        planned.append((entry, target))

    records = []
    counts: Counter[str] = Counter()
    for entry, target in planned:
        payload = archive.read_entry(entry)
        record = {"id": f"{entry.file_id:08X}", "source_size": entry.size}
        if not payload.startswith(b"DDS "):
            record["status"] = "not_dds"
            counts["not_dds"] += 1
            records.append(record)
            continue
        try:
            meta = inspect_dds(payload)
            converter = CONVERTERS.get(meta["format"])
            if converter is None:
                record.update({"status": "unsupported_format", "format": meta["format"]})
                counts["unsupported_format"] += 1
            elif not meta["base_level_fits"]:
                record.update({"status": "truncated_base_level", "format": meta["format"]})
                counts["truncated_base_level"] += 1
            else:
                width, height = converter(payload, str(target))
                record.update({
                    "status": "exported", "file": target.name,
                    "format": meta["format"], "width": width, "height": height,
                })
                counts["exported"] += 1
        except DDSFormatError as exc:
            record.update({"status": "invalid_dds", "error": str(exc)})
            counts["invalid_dds"] += 1
        records.append(record)

    result = {
        "archive": archive.path.name,
        "entry_count": len(archive.entries),
        "counts": dict(counts),
        "files": records,
        "note": "WDF IDs are hashes, not recovered original filenames. Only the top mip is exported.",
    }
    manifest_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
