"""Non-destructive asset catalog builder."""
from __future__ import annotations
import hashlib
import json
import os
import struct
from pathlib import Path
from .formats import inspect_file

ALLOWED_SUFFIXES = {".c3", ".dds", ".dmap", ".wdf", ".bmp", ".png", ".jpg", ".jpeg", ".tga", ".spr", ".ani"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", "bin", "obj"}

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def scan_assets(root: Path, *, include_hashes: bool = False) -> dict:
    """Scan known asset extensions; never follows symlinks or executes files."""
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    assets, skipped = [], 0
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (Path(current) / d).is_symlink())
        for name in sorted(names):
            path = Path(current) / name
            if path.is_symlink() or path.suffix.lower() not in ALLOWED_SUFFIXES:
                skipped += 1
                continue
            try:
                row = {"path": path.relative_to(root).as_posix(), **inspect_file(path)}
                if include_hashes:
                    row["sha256"] = _sha256(path)
                assets.append(row)
            except (OSError, ValueError, struct.error):
                skipped += 1
    counts = {}
    for row in assets:
        counts[row["format"]] = counts.get(row["format"], 0) + 1
    return {"schema_version": 1, "root_name": root.name, "asset_count": len(assets),
            "skipped_count": skipped, "format_counts": counts, "assets": assets}

def write_catalog(catalog: dict, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
