#!/usr/bin/env python3
"""Identify common asset signatures inside WDF archives without extracting files."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conquer_studio.wdf import WDFArchive\nfrom conquer_studio.dds import inspect_dds, DDSFormatError

def classify(data: bytes) -> str:
    if data.startswith(b"MAXFILE C3 00001"):
        return "C3"
    if data.startswith(b"DDS "):
        return "DDS"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
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
    total_bytes: Counter[str] = Counter()\n    dds_formats: Counter[str] = Counter()\n    dds_invalid = 0\n    dds_samples = []
    for entry in archive.entries:
        payload = archive.read_entry(entry)\n        kind = classify(payload[:16])\n        if kind == "DDS":\n            try:\n                meta = inspect_dds(payload)\n                dds_formats[meta["format"]] += 1\n                if not meta["base_level_fits"]:\n                    dds_invalid += 1\n                if len(dds_samples) < 5:\n                    dds_samples.append({"id": f"{entry.file_id:08X}", **meta})\n            except DDSFormatError:\n                dds_invalid += 1
        counts[kind] += 1
        total_bytes[kind] += entry.size
        examples.setdefault(kind, [])
        if len(examples[kind]) < 5:
            examples[kind].append(f"{entry.file_id:08X}")
    return {
        "archive": path.name,
        "entry_count": len(archive.entries),\n        "dds_format_counts": dict(dds_formats),\n        "dds_invalid_headers_or_short_payloads": dds_invalid,\n        "dds_samples": dds_samples,
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
