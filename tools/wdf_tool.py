#!/usr/bin/env python3
"""Inspect or safely extract Conquer Online PFDW WDF archives."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conquer_studio.wdf import WDFArchive

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="Print archive index as JSON")
    inspect.add_argument("archive", type=Path)
    extract = sub.add_parser("extract", help="Extract entries as HASH.bin files")
    extract.add_argument("archive", type=Path)
    extract.add_argument("destination", type=Path)
    args = parser.parse_args()
    archive = WDFArchive.open(args.archive)
    if args.command == "inspect":
        print(json.dumps(archive.manifest(), indent=2))
    else:
        manifest = archive.extract(args.destination)
        print(f"Extracted {manifest['entry_count']} entries to {args.destination}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
