#!/usr/bin/env python3
"""Read-only audit of candidate PHY4 vertex skinning fields.

The observed 40-byte record is interpreted conservatively:
  +0..11  candidate XYZ (3 little-endian float32)
  +12..19 candidate UV (2 little-endian float32)
  +20..23 unknown uint32
  +24..27 candidate influence/bone ID A (uint32)
  +28..31 candidate influence/bone ID B (uint32)
  +32..39 candidate weights A/B (2 float32)

This script reports distributions only. It does not assign bone semantics,
decode skeletons, build triangles, or export meshes.
"""
from __future__ import annotations
import argparse
import json
import math
import struct
from collections import Counter
from pathlib import Path


def summarize(values):
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "unique": len(set(values)),
        "min": min(values),
        "max": max(values),
        "first16": values[:16],
    }


def audit(path: Path, start: int, count: int, stride: int = 40) -> dict:
    data = path.read_bytes()
    end = start + count * stride
    if start < 0 or count < 1 or stride < 40 or end > len(data):
        raise ValueError("Candidate record range is outside file or invalid")

    xyz = [[], [], []]
    uv = [[], []]
    unknown20, ids_a, ids_b, weights_a, weights_b = [], [], [], [], []
    finite_xyz = finite_uv = finite_weights = 0
    weight_sum_ok = 0
    for i in range(count):
        off = start + i * stride
        p = struct.unpack_from("<3f", data, off)
        t = struct.unpack_from("<2f", data, off + 12)
        unk = struct.unpack_from("<I", data, off + 20)[0]
        ida = struct.unpack_from("<I", data, off + 24)[0]
        idb = struct.unpack_from("<I", data, off + 28)[0]
        wa, wb = struct.unpack_from("<2f", data, off + 32)
        for axis in range(3):
            xyz[axis].append(p[axis])
        for axis in range(2):
            uv[axis].append(t[axis])
        unknown20.append(unk)
        ids_a.append(ida)
        ids_b.append(idb)
        weights_a.append(wa)
        weights_b.append(wb)
        finite_xyz += all(math.isfinite(v) for v in p)
        finite_uv += all(math.isfinite(v) for v in t)
        finite_weights += math.isfinite(wa) and math.isfinite(wb)
        weight_sum_ok += math.isfinite(wa) and math.isfinite(wb) and abs((wa + wb) - 1.0) <= 1e-5

    trailing = len(data) - end
    finite_weight_pairs = [(a, b) for a, b in zip(weights_a, weights_b) if math.isfinite(a) and math.isfinite(b)]
    id_pairs = list(zip(ids_a, ids_b))
    id_values = [value for pair in id_pairs for value in pair]
    valid_weight_pairs = [(a, b) for a, b in finite_weight_pairs if -1e-6 <= a <= 1.000001 and -1e-6 <= b <= 1.000001]
    normalized_pairs = sum(abs((a + b) - 1.0) <= 1e-5 for a, b in finite_weight_pairs)
    id_frequency = Counter(id_values)
    pair_frequency = Counter(id_pairs)
    report = {
        "file": str(path),
        "file_size": len(data),
        "candidate": {"start": start, "count": count, "stride": stride, "end": end},
        "position_float_ranges": [
            {"min": min(v), "max": max(v), "finite": sum(math.isfinite(x) for x in v)}
            for v in xyz
        ],
        "uv_float_ranges": [
            {"min": min(v), "max": max(v), "finite": sum(math.isfinite(x) for x in v)}
            for v in uv
        ],
        "unknown_u32_at_plus20": summarize(unknown20),
        "candidate_id_a_u32_at_plus24": summarize(ids_a),
        "candidate_id_b_u32_at_plus28": summarize(ids_b),
        "candidate_weight_a_at_plus32": {
            "min": min(weights_a), "max": max(weights_a),
            "finite": sum(math.isfinite(x) for x in weights_a),
        },
        "candidate_weight_b_at_plus36": {
            "min": min(weights_b), "max": max(weights_b),
            "finite": sum(math.isfinite(x) for x in weights_b),
        },
        "checks": {
            "records_with_finite_xyz": finite_xyz,
            "records_with_finite_uv": finite_uv,
            "records_with_finite_weights": finite_weights,
            "weight_pairs_summing_to_one_tolerance_1e-5": weight_sum_ok,
            "candidate_id_a_zero_count": ids_a.count(0),
            "candidate_id_b_zero_count": ids_b.count(0),
        },
        "field_diagnostics": {
            "candidate_id_frequency": [
                {"id": value, "records": occurrences}
                for value, occurrences in sorted(id_frequency.items())
            ],
            "candidate_id_pair_frequency": [
                {"ids": [pair[0], pair[1]], "records": occurrences}
                for pair, occurrences in sorted(pair_frequency.items())
            ],
            "candidate_id_frequency_top32": [
                {"id": value, "records": occurrences}
                for value, occurrences in id_frequency.most_common(32)
            ],
            "candidate_id_pair_frequency_top32": [
                {"ids": [pair[0], pair[1]], "records": occurrences}
                for pair, occurrences in pair_frequency.most_common(32)
            ],
            "distinct_id_values": len(set(id_values)),
            "distinct_ordered_id_pairs": len(set(id_pairs)),
            "records_with_same_two_ids": sum(a == b for a, b in id_pairs),
            "finite_weight_pairs": len(finite_weight_pairs),
            "weight_pairs_with_both_values_in_0_to_1": len(valid_weight_pairs),
            "weight_pairs_summing_to_one": normalized_pairs,
            "assessment": "consistent_with_two_normalized_influences" if finite_weight_pairs and len(valid_weight_pairs) == len(finite_weight_pairs) and normalized_pairs == len(finite_weight_pairs) else "inconclusive_candidate_fields",
            "warning": "Statistical evidence only; IDs are not proven bone indices."
        },
        "post_record": {"offset": end, "trailing_bytes": trailing},
        "limitations": [
            "The 40-byte record layout remains a hypothesis.",
            "The two uint32 fields are candidate IDs, not confirmed bone indices.",
            "Weight sums do not prove skinning semantics or identify the skeleton table.",
            "No index topology, submesh, material, or export is decoded.",
        ],
    }

    if trailing >= 8:
        count16, reserved = struct.unpack_from("<II", data, end)
        seq_end = end + 8 + count16 * 2
        post = {"first_u32": count16, "second_u32": reserved,
                "candidate_u16_sequence_fits_file": seq_end <= len(data)}
        if 0 < count16 <= 10_000_000 and seq_end <= len(data):
            indices = struct.unpack_from("<" + "H" * count16, data, end + 8)
            post.update({
                "min": min(indices), "max": max(indices),
                "unique": len(set(indices)),
                "divisible_by_3": count16 % 3 == 0,
                "values_below_candidate_vertex_count": sum(x < count for x in indices),
                "sequence_end": seq_end,
                "bytes_after_sequence": len(data) - seq_end,
            })
        report["post_record"]["candidate_u16_block"] = post

    markers = {}
    for marker in (b"2SID", b"PHY4", b"MOTI", b"PTC3", b"PTCL", b"SHAP", b"CAME"):
        offsets, pos = [], 0
        while True:
            pos = data.find(marker, pos)
            if pos < 0:
                break
            offsets.append(pos)
            pos += 1
        markers[marker.decode("ascii")] = offsets
    report["marker_offsets"] = markers
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", type=Path)
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--count", type=int, required=True)
    ap.add_argument("--stride", type=int, default=40)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    result = audit(args.file, args.start, args.count, args.stride)
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.json:
        args.json.write_text(output + "\\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
