#!/usr/bin/env python3
"""Identify common asset signatures inside WDF archives without extracting files."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conquer_studio.wdf import WDFArchive
from conquer_studio.dds import (
    inspect_dds, DDSFormatError, decode_bc1_rgba, decode_bc2_rgba, decode_bc3_rgba,
)

def classify(data: bytes) -> str:
    if data.startswith(b"MAXFILE C3"):
        return "C3"
    if data.startswith(b"DDS "):
        return "DDS"
    if data.startswith(bytes([0x89]) + b"PNG\r\n\x1a\n"):
        return "PNG"
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if data.startswith(b"BM"):
        return "BMP"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "GIF"
    return "UNKNOWN"

def audit(path: Path) -> dict:
    archive = WDFArchive.open(path)
    counts: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    total_bytes: Counter[str] = Counter()
    dds_formats: Counter[str] = Counter()
    dds_invalid = 0
    dds_samples = []
    decode_functions = {
        "BC1": decode_bc1_rgba, "BC1_UNORM": decode_bc1_rgba, "BC1_SRGB": decode_bc1_rgba,
        "BC2": decode_bc2_rgba, "BC2_UNORM": decode_bc2_rgba, "BC2_SRGB": decode_bc2_rgba,
        "BC3": decode_bc3_rgba, "BC3_UNORM": decode_bc3_rgba, "BC3_SRGB": decode_bc3_rgba,
    }
    decoded_families = set()
    decode_samples = []
    for entry in archive.entries:
        payload = archive.read_entry(entry)
        kind = classify(payload[:16])
        if kind == "DDS":
            try:
                meta = inspect_dds(payload)
                dds_formats[meta["format"]] += 1
                if not meta["base_level_fits"]:
                    dds_invalid += 1
                if len(dds_samples) < 5:
                    dds_samples.append({"id": f"{entry.file_id:08X}", **meta})
                decoder = decode_functions.get(meta["format"])
                family = meta["format"][:3] if meta["format"].startswith("BC") else meta["format"]
                if decoder and family not in decoded_families and meta["base_level_fits"]:
                    width, height, rgba = decoder(payload)
                    decoded_families.add(family)
                    decode_samples.append({
                        "id": f"{entry.file_id:08X}", "format": meta["format"],
                        "width": width, "height": height,
                        "decoded_rgba_bytes": len(rgba),
                    })
            except DDSFormatError:
                dds_invalid += 1
        counts[kind] += 1
        total_bytes[kind] += entry.size
        examples.setdefault(kind, [])
        if len(examples[kind]) < 5:
            examples[kind].append(f"{entry.file_id:08X}")
    return {
        "archive": path.name,
        "entry_count": len(archive.entries),
        "dds_format_counts": dict(dds_formats),
        "dds_invalid_headers_or_short_payloads": dds_invalid,
        "dds_samples": dds_samples,
        "dds_decode_samples": decode_samples,
        "types": [
            {"type": kind, "count": counts[kind], "payload_bytes": total_bytes[kind],
             "sample_ids": examples[kind]}
            for kind in sorted(counts)
        ],
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args()
    results = [audit(path) for path in args.archives]
    print(json.dumps(results, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
