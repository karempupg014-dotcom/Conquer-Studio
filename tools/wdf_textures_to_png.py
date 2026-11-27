#!/usr/bin/env python3
"""Export BC1/BC2/BC3 textures from a Conquer Online WDF archive."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conquer_studio.texture_export import export_wdf_textures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="input WDF archive")
    parser.add_argument("destination", type=Path, help="output folder")
    args = parser.parse_args()
    if not args.archive.is_file():
        parser.error(f"WDF archive does not exist: {args.archive}")
    try:
        result = export_wdf_textures(args.archive, args.destination)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Archive: {result['archive']}")
    print(f"Entries: {result['entry_count']}")
    for status, count in sorted(result["counts"].items()):
        print(f"{status}: {count}")
    print(f"Manifest: {args.destination / 'texture-export-manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
