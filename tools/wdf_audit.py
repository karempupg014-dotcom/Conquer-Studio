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
    total_bytes: Counter[str] = Counter()
    for entry in archive.entries:
        kind = classify(archive.read_entry(entry)[:16])
        counts[kind] += 1
        total_bytes[kind] += entry.size
        examples.setdefault(kind, [])
        if len(examples[kind]) < 5:
            examples[kind].append(f"{entry.file_id:08X}")
    return {
        "archive": path.name,
        "entry_count": len(archive.entries),
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
