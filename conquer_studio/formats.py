"""Safe, read-only format identification for Conquer Online assets."""
from __future__ import annotations
from pathlib import Path
from .dds import DDSFormatError, inspect_dds

C3_SIGNATURE = b"MAXFILE C3 00001"
C3_TAGS = (b"PHY4", b"PHY3", b"PHY ", b"MOTI", b"PTC3", b"PTCL", b"SHAP", b"CAME")

def inspect_file(path: Path) -> dict:
    size = path.stat().st_size
    suffix = path.suffix.lower()
    result = {"format": "unknown", "size": size, "details": {}}
    with path.open("rb") as stream:
        head = stream.read(148)
        if head.startswith(C3_SIGNATURE):
            result["format"] = "c3"
            counts = {tag.decode("ascii"): 0 for tag in C3_TAGS}
            stream.seek(0)
            overlap = b""
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                data = overlap + chunk
                for tag in C3_TAGS:
                    counts[tag.decode("ascii")] += data.count(tag)
                overlap = data[-3:]
            result["details"] = {"signature": "MAXFILE C3 00001", "tag_counts": counts}
        elif head[:4] == b"DDS ":
            result["format"] = "dds"
            try:
                stream.seek(0)
                result["details"] = inspect_dds(stream.read())
            except DDSFormatError as exc:
                result["details"] = {"header_valid": False, "reason": str(exc)}
        elif suffix == ".dmap":
            result["format"] = "dmap_candidate"
            result["details"] = {"note": "Extension recognized; binary layout not decoded yet."}
        elif suffix == ".wdf":
            result["format"] = "wdf_candidate"
            result["details"] = {"note": "Use the WDF archive reader for container inspection."}
        elif suffix == ".c3":
            result["format"] = "c3_candidate"
            result["details"] = {"signature_valid": False, "first_bytes_hex": head[:16].hex()}
    return result
