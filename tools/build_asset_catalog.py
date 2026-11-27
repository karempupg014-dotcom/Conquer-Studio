#!/usr/bin/env python3
"""Build a read-only JSON catalog of Conquer Online assets."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conquer_studio.catalog import scan_assets, write_catalog

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Game/Patch directory to scan")
    parser.add_argument("--output", type=Path, default=Path("asset-catalog.json"))
    parser.add_argument("--hashes", action="store_true", help="Calculate SHA-256 for every indexed asset (slower)")
    args = parser.parse_args()
    catalog = scan_assets(args.root, include_hashes=args.hashes)
    write_catalog(catalog, args.output)
    print(f"Indexed {catalog['asset_count']} assets; skipped {catalog['skipped_count']} files.")
    for kind, count in sorted(catalog["format_counts"].items()):
        print(f"  {kind}: {count}")
    print(f"Catalog: {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
