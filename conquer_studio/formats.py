"""Safe, read-only format identification for Conquer Online assets."""
from __future__ import annotations
import struct
from pathlib import Path

C3_SIGNATURE = b"MAXFILE C3 00001"
C3_TAGS = (b"PHY4", b"PHY3", b"PHY ", b"MOTI", b"PTC3", b"PTCL", b"SHAP", b"CAME")

def inspect_file(path: Path) -> dict:
    size = path.stat().st_size
    suffix = path.suffix.lower()
    result = {"format": "unknown", "size": size, "details": {}}
    with path.open("rb") as stream:
        head = stream.read(128)
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
            if len(head) >= 128:
                hs, flags, height, width, pitch, depth, mipmaps = struct.unpack_from("<7I", head, 4)
                pf_size = struct.unpack_from("<I", head, 76)[0]
                result["details"] = {"header_size": hs, "flags": flags, "width": width,
                    "height": height, "pitch_or_linear_size": pitch, "depth": depth,
                    "mipmaps": mipmaps, "pixel_format_size": pf_size,
                    "header_valid": hs == 124 and pf_size == 32 and width > 0 and height > 0}
            else:
                result["details"] = {"header_valid": False, "reason": "Truncated DDS header"}
        elif suffix == ".dmap":
            result["format"] = "dmap_candidate"
            result["details"] = {"note": "Extension recognized; binary layout not decoded yet."}
        elif suffix == ".wdf":
            result["format"] = "wdf_candidate"
            result["details"] = {"note": "Extension recognized; archive layout not decoded yet."}
        elif suffix == ".c3":
            result["format"] = "c3_candidate"
            result["details"] = {"signature_valid": False, "first_bytes_hex": head[:16].hex()}
    return result
