#!/usr/bin/env python3
"""Experimental PHY4 candidate-buffer probe for Conquer Online C3 files.

This tool is read-only. It reports a candidate 40-byte vertex record observed
in selected 6609+ samples. It does NOT claim a complete C3 decoder and does
not export meshes or execute game files.
"""
from __future__ import annotations
import argparse
import json
import math
import struct
from pathlib import Path


def u32(data: bytes, pos: int) -> int:
    if pos < 0 or pos + 4 > len(data):
        raise ValueError("u32 outside file")
    return struct.unpack_from("<I", data, pos)[0]


def f32(data: bytes, pos: int) -> float:
    return struct.unpack_from("<f", data, pos)[0]


def probe(path: Path) -> dict:
    data = path.read_bytes()
    result = {"file": str(path), "size": len(data), "signature_ok":
              data.startswith(b"MAXFILE C3 00001"), "candidate": False}
    if not result["signature_ok"] or data[16:20] != b"PHY4":
        result["reason"] = "Expected MAXFILE C3 00001 with root PHY4"
        return result

    section_length = u32(data, 20)
    name_length = u32(data, 24)
    name_start = 28
    name = data[name_start:name_start + name_length].split(b"\0", 1)[0]
    payload = name_start + name_length
    section_end = 24 + section_length
    if section_end > len(data) or payload + 12 > section_end:
        result["reason"] = "Root PHY4 length/name exceeds file bounds"
        return result

    record_type, vertex_count, flags = struct.unpack_from("<III", data, payload)
    stride = 40
    vertex_start = payload + 12
    vertex_end = vertex_start + vertex_count * stride
    if vertex_count < 1 or vertex_count > 200000 or vertex_end > section_end:
        result["reason"] = "Candidate 40-byte record stream does not fit section"
        result.update({"name": name.decode("ascii", "replace"),
                       "record_type": record_type, "vertex_count": vertex_count,
                       "flags": flags, "candidate_stride": stride,
                       "vertex_start": vertex_start, "candidate_vertex_end": vertex_end,
                       "section_end": section_end})
        return result

    positions, uvs = [], []
    for i in range(vertex_count):
        base = vertex_start + i * stride
        xyz = struct.unpack_from("<3f", data, base)
        uv = struct.unpack_from("<2f", data, base + 12)
        positions.append(xyz)
        uvs.append(uv)

    finite_positions = all(all(math.isfinite(v) and abs(v) < 100000 for v in p)
                           for p in positions)
    finite_uvs = all(all(math.isfinite(v) and abs(v) < 10000 for v in uv)
                     for uv in uvs)
    bounds = [[min(p[a] for p in positions), max(p[a] for p in positions)]
              for a in range(3)]
    uv_bounds = [[min(uv[a] for uv in uvs), max(uv[a] for uv in uvs)]
                 for a in range(2)]

    remaining = section_end - vertex_end
    index_candidate = {"recognized": False, "remaining_bytes": remaining}
    if remaining >= 8:
        index_count, reserved = struct.unpack_from("<II", data, vertex_end)
        bytes_needed = index_count * 2
        if (0 < index_count <= 10000000 and reserved == 0 and
                bytes_needed <= remaining - 8):
            indices = struct.unpack_from(f"<{index_count}H", data, vertex_end + 8)
            valid = all(index < vertex_count for index in indices)
            index_candidate.update({
                "recognized": valid,
                "count": index_count,
                "reserved": reserved,
                "all_indices_below_vertex_count": valid,
                "index_min": min(indices) if indices else None,
                "index_max": max(indices) if indices else None,
                "multiple_of_three": index_count % 3 == 0,
            })

    result.update({
        "candidate": finite_positions and finite_uvs,
        "name": name.decode("ascii", "replace"),
        "record_type": record_type,
        "vertex_count": vertex_count,
        "flags": flags,
        "candidate_stride": stride,
        "vertex_start": vertex_start,
        "candidate_vertex_end": vertex_end,
        "section_end": section_end,
        "remaining_after_candidate_vertices": remaining,
        "finite_xyz": finite_positions,
        "finite_uv": finite_uvs,
        "xyz_bounds": bounds,
        "uv_bounds": uv_bounds,
        "first_xyz": positions[:3],
        "first_uv": uvs[:3],
        "candidate_index_buffer": index_candidate,
        "limitations": [
            "40-byte stride is an observed candidate, not a fully decoded vertex schema.",
            "Fields beyond XYZ and candidate UV offsets are not semantically decoded.",
            "Index-buffer recognition is heuristic; topology and submesh boundaries are unverified.",
            "Only the root PHY4 section is probed.",
        ],
    })
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    reports = [probe(path) for path in args.paths]
    output = json.dumps(reports, indent=2, ensure_ascii=False)
    if args.json:
        args.json.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
