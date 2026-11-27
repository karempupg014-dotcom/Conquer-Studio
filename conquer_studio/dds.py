"""Read-only DDS header parser and payload validator."""
from __future__ import annotations
import struct

FOURCC_FORMATS = {
    "DXT1": ("BC1", 8), "DXT2": ("BC2", 16), "DXT3": ("BC2", 16),
    "DXT4": ("BC3", 16), "DXT5": ("BC3", 16), "ATI1": ("BC4", 8),
    "BC4U": ("BC4", 8), "BC4S": ("BC4S", 8), "ATI2": ("BC5", 16),
    "BC5U": ("BC5", 16), "BC5S": ("BC5S", 16),
}
DXGI_FORMATS = {
    28: ("RGBA8_UNORM", 4), 29: ("RGBA8_SRGB", 4),
    71: ("BC1_UNORM", 0), 72: ("BC1_SRGB", 0),
    74: ("BC2_UNORM", 0), 75: ("BC2_SRGB", 0),
    77: ("BC3_UNORM", 0), 78: ("BC3_SRGB", 0),
    80: ("BC4_UNORM", 0), 81: ("BC4_SNORM", 0),
    83: ("BC5_UNORM", 0), 84: ("BC5_SNORM", 0),
    87: ("BGRA8_UNORM", 4), 91: ("BGRA8_SRGB", 4),
}

class DDSFormatError(ValueError):
    """Malformed or truncated DDS data."""

def inspect_dds(data: bytes) -> dict:
    if len(data) < 128 or data[:4] != b"DDS ":
        raise DDSFormatError("Missing or truncated DDS header")
    header_size, flags, height, width, pitch, depth, mip_count = struct.unpack_from("<7I", data, 4)
    pf_size, pf_flags = struct.unpack_from("<2I", data, 76)
    fourcc = data[84:88].decode("ascii", "replace")
    rgb_bits = struct.unpack_from("<I", data, 88)[0]
    if header_size != 124 or pf_size != 32 or width == 0 or height == 0:
        raise DDSFormatError("Invalid DDS header dimensions or structure")
    if width > 32768 or height > 32768:
        raise DDSFormatError("DDS dimensions exceed safety limit")
    mip_count = max(1, mip_count)
    if mip_count > 32:
        raise DDSFormatError("DDS mip count exceeds safety limit")
    fmt = "UNKNOWN"
    block_bytes = None
    bytes_per_pixel = None
    data_offset = 128
    if pf_flags & 0x4:
        if fourcc == "DX10":
            if len(data) < 148:
                raise DDSFormatError("Truncated DDS DX10 extension")
            dxgi, dimension, misc, array_size, misc2 = struct.unpack_from("<5I", data, 128)
            if array_size == 0 or array_size > 2048:
                raise DDSFormatError("Invalid DDS DX10 array size")
            fmt, bpp = DXGI_FORMATS.get(dxgi, (f"DXGI_{dxgi}", None))
            if bpp:
                bytes_per_pixel = bpp
            elif dxgi in (71,72,74,75,77,78,80,81,83,84):
                block_bytes = 8 if dxgi in (71,72,80,81) else 16
            data_offset = 148
        else:
            fmt, block_bytes = FOURCC_FORMATS.get(fourcc, (f"FOURCC_{fourcc}", None))
    elif pf_flags & 0x40 and rgb_bits in (16, 24, 32):
        fmt, bytes_per_pixel = f"RGB{rgb_bits}", rgb_bits // 8
    else:
        fmt = "UNSUPPORTED_PIXEL_FORMAT"
    expected_base = None
    if block_bytes:
        expected_base = max(1, (width + 3)//4) * max(1, (height + 3)//4) * block_bytes
    elif bytes_per_pixel:
        expected_base = width * height * bytes_per_pixel
    available = len(data) - data_offset
    valid_payload = expected_base is None or available >= expected_base
    return {
        "header_valid": True, "width": width, "height": height,
        "mipmaps": mip_count, "fourcc": fourcc, "format": fmt,
        "data_offset": data_offset, "payload_bytes": available,
        "expected_base_level_bytes": expected_base,
        "base_level_fits": valid_payload,
        "dx10": fourcc == "DX10",
    }
