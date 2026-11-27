#!/usr/bin/env python3
"""Convert supported BC-compressed DDS textures to PNG."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conquer_studio.dds import (
    DDSFormatError,
    convert_bc1_dds_to_png,
    convert_bc2_dds_to_png,
    convert_bc3_dds_to_png,
    inspect_dds,
)


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="input DDS file")
    parser.add_argument("destination", type=Path, help="output PNG file")
    parser.add_argument("--force", action="store_true", help="allow replacing an existing PNG")
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"input file does not exist: {args.source}")
    if args.destination.exists() and not args.force:
        parser.error(f"output already exists (use --force to replace): {args.destination}")

    try:
        data = args.source.read_bytes()
        metadata = inspect_dds(data)
        converter = CONVERTERS.get(metadata["format"])
        if converter is None:
            raise DDSFormatError(
                f"unsupported conversion format: {metadata['format']} "
                "(currently BC1, BC2 and BC3)"
            )
        args.destination.parent.mkdir(parents=True, exist_ok=True)
        width, height = converter(data, str(args.destination))
    except (OSError, DDSFormatError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Converted {args.source} -> {args.destination} ({width}x{height}, {metadata['format']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
