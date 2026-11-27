#!/usr/bin/env python3
"""Compare read-only PHY4 candidate-field audit JSON reports.

ID overlap is descriptive only: it does not prove shared skeletons, bone indices,
or compatible coordinate spaces.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_report(path: Path) -> dict:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read audit report {path}: {exc}") from exc
    candidate = report.get("candidate")
    diagnostics = report.get("field_diagnostics")
    if not isinstance(candidate, dict) or not isinstance(diagnostics, dict):
        raise ValueError(f"{path} is not a supported PHY4 audit report")
    frequencies = diagnostics.get("candidate_id_frequency")
    pair_frequencies = diagnostics.get("candidate_id_pair_frequency")
    if not isinstance(frequencies, list) or not isinstance(pair_frequencies, list):
        raise ValueError(f"{path} lacks complete candidate ID distributions; regenerate it")
    ids = set()
    pairs = set()
    for item in frequencies:
        if (not isinstance(item, dict) or
                not isinstance(item.get("id"), int) or
                not isinstance(item.get("records"), int) or item["records"] < 0):
            raise ValueError(f"{path} contains an invalid ID frequency entry")
        ids.add(item["id"])
    for item in pair_frequencies:
        pair = item.get("ids") if isinstance(item, dict) else None
        if (not isinstance(pair, list) or len(pair) != 2 or
                not all(isinstance(value, int) for value in pair)):
            raise ValueError(f"{path} contains an invalid ID-pair entry")
        pairs.add(tuple(pair))
    return {
        "label": str(report.get("file") or path),
        "count": candidate.get("count"),
        "ids": ids,
        "pairs": pairs,
        "assessment": diagnostics.get("assessment", "unknown"),
    }


def compare(paths: list[Path]) -> dict:
    if len(paths) < 2:
        raise ValueError("Provide at least two audit JSON reports")
    reports = [load_report(path) for path in paths]
    comparisons = []
    for left_index in range(len(reports)):
        for right_index in range(left_index + 1, len(reports)):
            left, right = reports[left_index], reports[right_index]
            shared_ids = sorted(left["ids"] & right["ids"])
            shared_pairs = sorted(left["pairs"] & right["pairs"])
            comparisons.append({
                "left": left["label"],
                "right": right["label"],
                "left_candidate_records": left["count"],
                "right_candidate_records": right["count"],
                "shared_candidate_id_count": len(shared_ids),
                "shared_candidate_ids": shared_ids,
                "shared_ordered_id_pair_count": len(shared_pairs),
                "shared_ordered_id_pairs": [list(pair) for pair in shared_pairs],
                "left_weight_assessment": left["assessment"],
                "right_weight_assessment": right["assessment"],
                "interpretation": "Descriptive overlap only; no skeleton or bone-index equivalence is established.",
            })
    return {
        "report_count": len(reports),
        "reports": [
            {"label": item["label"], "candidate_records": item["count"],
             "distinct_candidate_ids": len(item["ids"]),
             "distinct_ordered_id_pairs": len(item["pairs"]),
             "weight_assessment": item["assessment"]}
            for item in reports
        ],
        "comparisons": comparisons,
        "limitations": [
            "Only candidate IDs and ordered pairs are compared.",
            "Matching numeric IDs do not prove matching bones or skeletons.",
            "Different meshes may use local palettes, remapping, or unrelated ID namespaces.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--json", type=Path, help="write comparison JSON")
    args = parser.parse_args()
    result = compare(args.reports)
    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.json:
        args.json.write_text(output + "\\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
