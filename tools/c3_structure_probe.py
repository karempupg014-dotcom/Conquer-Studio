#!/usr/bin/env python3
"""Conservative structural scanner for Conquer Online MAXFILE C3 samples.

Read-only probe: reports observed outer headers and bounded section markers.
It does not decode PHY4 vertex/index buffers and does not execute game files.
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path

KNOWN = {b"PHY4", b"PHY3", b"PHY ", b"MOTI", b"PTC3", b"PTCL", b"SHAP", b"CAME"}


def read_u32(data: bytes, offset: int):
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def scan(path: Path):
    data = path.read_bytes()
    result = {
        "file": str(path),
        "size": len(data),
        "signature_ok": data.startswith(b"MAXFILE C3 00001"),
        "root_type": data[16:20].decode("ascii", "replace") if len(data) >= 20 else None,
        "root_length_u32_at_20": read_u32(data, 20),
        "markers": [],
        "limitations": [
            "Marker offsets and length fields are observations, not a full semantic decode.",
            "PHY4 vertex/index layout and MOTI animation semantics remain unverified.",
        ],
    }
    i = 16
    while i + 12 <= len(data):
        tag = None
        header = None
        style = None
        if data[i:i + 4] == b"2SID" and data[i + 4:i + 8] in KNOWN:
            tag, header, style = data[i + 4:i + 8], i + 8, "2SID"
        elif data[i:i + 4] == b"\0\0\0\0" and data[i + 4:i + 8] in KNOWN:
            tag, header, style = data[i + 4:i + 8], i + 8, "zero-prefixed"
        if tag is not None:
            length = read_u32(data, header)
            count_or_flags = read_u32(data, header + 4)
            raw_name = data[header + 8:header + 24].split(b"\0", 1)[0]
            candidate_name = (
                raw_name.decode("ascii", "replace")
                if raw_name and all(32 <= byte < 127 for byte in raw_name)
                else None
            )
            end = header + length if length is not None else None
            result["markers"].append({
                "offset": i,
                "tag": tag.decode("ascii", "replace"),
                "style": style,
                "length_field_offset": header,
                "length": length,
                "count_or_flags": count_or_flags,
                "candidate_name": candidate_name,
                "candidate_end": end,
                "length_within_file": end is not None and end <= len(data),
            })
            i += 8
        else:
            i += 1
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--json", type=Path, help="also write a JSON report")
    args = parser.parse_args()
    reports = [scan(path) for path in args.paths]
    output = json.dumps(reports, indent=2, ensure_ascii=False)
    if args.json:
        args.json.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
