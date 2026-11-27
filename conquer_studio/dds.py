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

def _rgb565(value: int) -> tuple[int, int, int]:
    """Expand one RGB565 endpoint to 8-bit RGB."""
    r = (value >> 11) & 0x1F
    g = (value >> 5) & 0x3F
    b = value & 0x1F
    return ((r * 255 + 15) // 31, (g * 255 + 31) // 63, (b * 255 + 15) // 31)


def decode_bc1_rgba(data: bytes) -> tuple[int, int, bytes]:
    """Decode the top BC1/DXT1 mip level into tightly packed RGBA bytes."""
    meta = inspect_dds(data)
    if meta["format"] not in ("BC1", "BC1_UNORM", "BC1_SRGB"):
        raise DDSFormatError(f"BC1 decoder does not support {meta['format']}")
    if not meta["base_level_fits"]:
        raise DDSFormatError("DDS BC1 base-level payload is truncated")

    width, height = meta["width"], meta["height"]
    output = bytearray(width * height * 4)
    offset = meta["data_offset"]
    blocks_x = (width + 3) // 4
    blocks_y = (height + 3) // 4

    for by in range(blocks_y):
        for bx in range(blocks_x):
            c0, c1, indices = struct.unpack_from("<HHI", data, offset)
            offset += 8
            p0, p1 = _rgb565(c0), _rgb565(c1)
            if c0 > c1:
                colors = (
                    (*p0, 255), (*p1, 255),
                    (*tuple((2 * p0[i] + p1[i]) // 3 for i in range(3)), 255),
                    (*tuple((p0[i] + 2 * p1[i]) // 3 for i in range(3)), 255),
                )
            else:
                colors = (
                    (*p0, 255), (*p1, 255),
                    (*tuple((p0[i] + p1[i]) // 2 for i in range(3)), 255),
                    (0, 0, 0, 0),
                )
            for py in range(4):
                y = by * 4 + py
                if y >= height:
                    continue
                for px in range(4):
                    x = bx * 4 + px
                    if x >= width:
                        continue
                    selector = (indices >> (2 * (py * 4 + px))) & 0x3
                    dst = (y * width + x) * 4
                    output[dst:dst + 4] = bytes(colors[selector])

    return width, height, bytes(output)


def encode_rgba_png(width: int, height: int, rgba: bytes) -> bytes:
    """Encode tightly packed RGBA pixels as a standards-compliant PNG."""
    import binascii
    import zlib

    if width <= 0 or height <= 0 or len(rgba) != width * height * 4:
        raise ValueError("Invalid RGBA image dimensions or buffer length")

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)

    scanlines = b"".join(
        b"\x00" + rgba[y * width * 4:(y + 1) * width * 4]
        for y in range(height)
    )
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(scanlines, 9))
        + chunk(b"IEND", b"")
    )


def convert_bc1_dds_to_png(data: bytes, destination: str) -> tuple[int, int]:
    """Convert a BC1/DXT1 DDS top mip to PNG; returns (width, height)."""
    width, height, rgba = decode_bc1_rgba(data)
    from pathlib import Path
    Path(destination).write_bytes(encode_rgba_png(width, height, rgba))
    return width, height

def _decode_color_block(block: bytes, force_four_color: bool = True) -> tuple[tuple[int, int, int, int], ...]:
    c0, c1, indices = struct.unpack("<HHI", block)
    p0, p1 = _rgb565(c0), _rgb565(c1)
    color2 = tuple((2 * p0[i] + p1[i]) // 3 for i in range(3))
    color3 = tuple((p0[i] + 2 * p1[i]) // 3 for i in range(3))
    if force_four_color or c0 > c1:
        colors = ((*p0, 255), (*p1, 255), (*color2, 255), (*color3, 255))
    else:
        midpoint = tuple((p0[i] + p1[i]) // 2 for i in range(3))
        colors = ((*p0, 255), (*p1, 255), (*midpoint, 255), (0, 0, 0, 0))
    return tuple(colors[(indices >> (2 * i)) & 3] for i in range(16))


def _decode_alpha_block_bc3(block: bytes) -> tuple[int, ...]:
    a0, a1 = block[0], block[1]
    selectors = int.from_bytes(block[2:8], "little")
    if a0 > a1:
        palette = [a0, a1] + [
            ((7 - i) * a0 + i * a1 + 3) // 7 for i in range(1, 7)
        ]
    else:
        palette = [a0, a1] + [
            ((5 - i) * a0 + i * a1 + 2) // 5 for i in range(1, 5)
        ] + [0, 255]
    return tuple(palette[(selectors >> (3 * i)) & 7] for i in range(16))


def _decode_bc_rgba(data: bytes, family: str) -> tuple[int, int, bytes]:
    meta = inspect_dds(data)
    accepted = {
        "BC2": ("BC2", "BC2_UNORM", "BC2_SRGB"),
        "BC3": ("BC3", "BC3_UNORM", "BC3_SRGB"),
    }
    if meta["format"] not in accepted[family]:
        raise DDSFormatError(f"{family} decoder does not support {meta['format']}")
    if not meta["base_level_fits"]:
        raise DDSFormatError(f"DDS {family} base-level payload is truncated")

    width, height = meta["width"], meta["height"]
    output = bytearray(width * height * 4)
    offset = meta["data_offset"]
    blocks_x, blocks_y = (width + 3) // 4, (height + 3) // 4
    for by in range(blocks_y):
        for bx in range(blocks_x):
            block = data[offset:offset + 16]
            offset += 16
            if family == "BC2":
                alpha_bits = int.from_bytes(block[:8], "little")
                alphas = tuple(((alpha_bits >> (4 * i)) & 0xF) * 17 for i in range(16))
                colors = _decode_color_block(block[8:16], force_four_color=True)
            else:
                alphas = _decode_alpha_block_bc3(block[:8])
                colors = _decode_color_block(block[8:16], force_four_color=True)

            for py in range(4):
                y = by * 4 + py
                if y >= height:
                    continue
                for px in range(4):
                    x = bx * 4 + px
                    if x >= width:
                        continue
                    i = py * 4 + px
                    r, g, b, _ = colors[i]
                    dst = (y * width + x) * 4
                    output[dst:dst + 4] = bytes((r, g, b, alphas[i]))
    return width, height, bytes(output)


def decode_bc2_rgba(data: bytes) -> tuple[int, int, bytes]:
    """Decode the top BC2/DXT3 mip level into tightly packed RGBA bytes."""
    return _decode_bc_rgba(data, "BC2")


def decode_bc3_rgba(data: bytes) -> tuple[int, int, bytes]:
    """Decode the top BC3/DXT5 mip level into tightly packed RGBA bytes."""
    return _decode_bc_rgba(data, "BC3")


def convert_bc2_dds_to_png(data: bytes, destination: str) -> tuple[int, int]:
    """Convert a BC2/DXT3 DDS top mip to PNG; returns (width, height)."""
    width, height, rgba = decode_bc2_rgba(data)
    from pathlib import Path
    Path(destination).write_bytes(encode_rgba_png(width, height, rgba))
    return width, height


def convert_bc3_dds_to_png(data: bytes, destination: str) -> tuple[int, int]:
    """Convert a BC3/DXT5 DDS top mip to PNG; returns (width, height)."""
    width, height, rgba = decode_bc3_rgba(data)
    from pathlib import Path
    Path(destination).write_bytes(encode_rgba_png(width, height, rgba))
    return width, height

