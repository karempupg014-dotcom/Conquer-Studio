#!/usr/bin/env python3
"""Read-only audit of candidate 40-byte PHY4 records and following bytes.

This is a diagnostic tool, not a C3 decoder. Supply a sample path, candidate
record start, and candidate record count. It reports field ranges and a
conservative interpretation of the first post-record uint16 sequence.
"""
from __future__ import annotations
import argparse
import math
import struct
from pathlib import Path


def audit(path: Path, start: int, count: int, stride: int = 40) -> None:
    data = path.read_bytes()
    end = start + count * stride
    print(f"file={path} size={len(data)}")
    print(f"candidate_records start={start} count={count} stride={stride} end={end}")
    if start < 0 or end > len(data):
        raise SystemExit("candidate record range is outside file")

    fields = []
    for i in range(count):
        off = start + i * stride
        fields.append(struct.unpack_from("<10f", data, off))
    for field in range(10):
        vals = [r[field] for r in fields]
        finite = [v for v in vals if math.isfinite(v)]
        print(f"float@+{field*4:02d}: finite={len(finite)}/{count} "
              f"min={min(finite) if finite else None} "
              f"max={max(finite) if finite else None}")

    weight_sums = [r[8] + r[9] for r in fields]
    within = sum(abs(s - 1.0) <= 1e-5 for s in weight_sums)
    print(f"candidate_weight_sum_near_1={within}/{count} (tolerance 1e-5)")

    print("integer pairs at +20 and +24:")
    for off in (20, 24, 28):
        vals = [struct.unpack_from("<I", data, start + i*stride + off)[0]
                for i in range(count)]
        print(f"  u32@+{off}: unique={len(set(vals))} min={min(vals)} max={max(vals)} "
              f"first8={vals[:8]}")

    print(f"post_record_offset={end} trailing_bytes={len(data)-end}")
    if end + 8 <= len(data):
        candidate_count, reserved = struct.unpack_from("<II", data, end)
        print(f"post_record_u32_pair=({candidate_count}, {reserved})")
        seq_end = end + 8 + candidate_count * 2
        if candidate_count > 0 and seq_end <= len(data):
            idx = struct.unpack_from("<" + "H"*candidate_count, data, end+8)
            print(f"candidate_u16_sequence count={candidate_count} "
                  f"max={max(idx)} unique={len(set(idx))} "
                  f"divisible_by_3={candidate_count % 3 == 0} "
                  f"end={seq_end} trailing_after_sequence={len(data)-seq_end}")
        else:
            print("candidate_u16_sequence=not safely bounded; not decoded")

    for marker in (b"2SID", b"PHY4", b"MOTI", b"PTC3", b"PTCL", b"SHAP", b"CAME"):
        offsets = []
        pos = 0
        while True:
            pos = data.find(marker, pos)
            if pos < 0:
                break
            offsets.append(pos)
            pos += 1
        print(f"marker {marker.decode('ascii')}: {offsets}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--count", type=int, required=True)
    ap.add_argument("--stride", type=int, default=40)
    args = ap.parse_args()
    audit(args.file, args.start, args.count, args.stride)


if __name__ == "__main__":
    main()
