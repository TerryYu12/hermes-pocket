"""QR generation (vendored qrcodegen) plus ASCII / PNG rendering. Stdlib only."""
from __future__ import annotations

import struct
import zlib

from .vendor.qrcodegen import QrCode


def make_matrix(text: str) -> list[list[bool]]:
    """Encode text into a QR matrix (list of rows of bool; True = dark module)."""
    qr = QrCode.encode_text(text, QrCode.Ecc.MEDIUM)
    n = qr.get_size()
    return [[qr.get_module(x, y) for x in range(n)] for y in range(n)]


def render_ascii(matrix: list[list[bool]], quiet: int = 2, invert: bool = False) -> str:
    """Render as half-block characters (two vertical modules per text row)."""
    n = len(matrix)
    total = n + 2 * quiet

    def dark(x: int, y: int) -> bool:
        inside = quiet <= x < quiet + n and quiet <= y < quiet + n
        value = bool(inside and matrix[y - quiet][x - quiet])
        return (not value) if invert else value

    lines: list[str] = []
    y = 0
    while y < total:
        row: list[str] = []
        for x in range(total):
            top = dark(x, y)
            bottom = dark(x, y + 1) if y + 1 < total else False
            if top and bottom:
                row.append("\u2588")  # full block
            elif top:
                row.append("\u2580")  # upper half
            elif bottom:
                row.append("\u2584")  # lower half
            else:
                row.append(" ")
        lines.append("".join(row))
        y += 2
    return "\n".join(lines)


def render_png(matrix: list[list[bool]], scale: int = 8, quiet: int = 4, invert: bool = False) -> bytes:
    """Render as an 8-bit grayscale PNG (dark modules black), stdlib only."""
    n = len(matrix)
    side = (n + 2 * quiet) * scale
    raw = bytearray()
    for y in range(side):
        raw.append(0)  # filter type: None
        my = y // scale - quiet
        for x in range(side):
            mx = x // scale - quiet
            dark = 0 <= mx < n and 0 <= my < n and matrix[my][mx]
            if invert:
                dark = not dark
            raw.append(0 if dark else 255)
    ihdr = struct.pack(">IIBBBBB", side, side, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )
