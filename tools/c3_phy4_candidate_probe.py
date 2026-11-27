#!/usr/bin/env python3
"""Experimental PHY4 candidate-buffer probe for Conquer Online C3 files.

Read-only probe of root and nested PHY4 sections. It reports a candidate
40-byte vertex record observed in selected client samples. It does NOT claim
a complete C3 decoder and does not export meshes or execute game files.
"""
from __future__ import annotations
import argparse
import json
import math
import struct
from pathlib import Path


def read_u32(data: bytes, pos: int) -> int:
    if pos < 0 or pos + 4 > len(data):
        raise ValueError("u32 outside file")
    return struct.unpack_from("<I", data, pos)[0]


def probe_section(data: bytes, tag_pos: int) -> dict:
    length = read_u32(data, tag_pos + 4)
    name_length = read_u32(data, tag_pos + 8)
    name_start = tag_pos + 12
    name = data[name_start:name_start + name_length].split(b"\0", 1)[0]
    payload = name_start + name_length
    section_end = tag_pos + 8 + length
    out = {"offset": tag_pos, "name": name.decode("ascii", "replace"),
           "section_length": length, "section_end": section_end}
    if name_length > 128 or section_end > len(data) or payload + 12 > section_end:
        out["reason"] = "Section header/name outside safe bounds"
        return out

    record_type, vertex_count, flags = struct.unpack_from("<III", data, payload)
    stride = 40
    vertex_start = payload + 12
    vertex_end = vertex_start + vertex_count * stride
    out.update({"record_type": record_type, "vertex_count": vertex_count,
                "flags": flags, "candidate_stride": stride,
                "vertex_start": vertex_start, "candidate_vertex_end": vertex_end})
    if vertex_count < 1 or vertex_count > 200000 or vertex_end > section_end:
        out["candidate"] = False
        out["reason"] = "Candidate 40-byte record stream does not fit section"
        return out

    positions, uvs = [], []
    for i in range(vertex_count):
        base = vertex_start + i * stride
        positions.append(struct.unpack_from("<3f", data, base))
        uvs.append(struct.unpack_from("<2f", data, base + 12))
    finite_xyz = all(all(math.isfinite(v) and abs(v) < 100000 for v in p)
                     for p in positions)
    finite_uv = all(all(math.isfinite(v) and abs(v) < 10000 for v in uv)
                    for uv in uvs)
    remaining = section_end - vertex_end
    index_candidate = {"recognized": False, "remaining_bytes": remaining}
    if remaining >= 8:
        index_count, reserved = struct.unpack_from("<II", data, vertex_end)
        if (0 < index_count <= 10000000 and reserved == 0 and
                index_count * 2 <= remaining - 8):
            indices = struct.unpack_from(f"<{index_count}H", data, vertex_end + 8)
            valid = all(index < vertex_count for index in indices)
            index_candidate.update({
                "recognized": valid, "count": index_count, "reserved": reserved,
                "all_indices_below_vertex_count": valid,
                "index_min": min(indices) if indices else None,
                "index_max": max(indices) if indices else None,
                "multiple_of_three": index_count % 3 == 0,
                "triangle_list_candidate": valid and index_count % 3 == 0,
                "topology_status": (
                    "count_is_multiple_of_three_only_not_proof_of_triangle_list"
                    if valid and index_count % 3 == 0
                    else "not_a_triangle_list_candidate_by_count_heuristic"
                ),
            })
    out.update({
        "candidate": finite_xyz and finite_uv,
        "finite_xyz": finite_xyz, "finite_uv": finite_uv,
        "xyz_bounds": [[min(p[a] for p in positions), max(p[a] for p in positions)]
                       for a in range(3)],
        "uv_bounds": [[min(uv[a] for uv in uvs), max(uv[a] for uv in uvs)]
                      for a in range(2)],
        "first_xyz": positions[:3], "first_uv": uvs[:3],
        "remaining_after_candidate_vertices": remaining,
        "candidate_index_buffer": index_candidate,
        "limitations": [
            "40-byte stride is an observed candidate, not a fully decoded vertex schema.",
            "Fields beyond XYZ and candidate UV offsets are not semantically decoded.",
            "Index-buffer recognition is heuristic; topology and submesh boundaries are unverified.",
        ],
    })
    return out


def probe(path: Path) -> dict:
    data = path.read_bytes()
    result = {"file": str(path), "size": len(data),
              "signature_ok": data.startswith(b"MAXFILE C3 00001"),
              "phy4_sections": []}
    if not result["signature_ok"]:
        result["reason"] = "Invalid MAXFILE C3 00001 signature"
        return result
    positions = []
    start = 16
    while True:
        pos = data.find(b"PHY4", start)
        if pos < 0:
            break
        if pos + 12 <= len(data):
            positions.append(pos)
        start = pos + 4
    result["phy4_sections"] = [probe_section(data, pos) for pos in positions]
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
