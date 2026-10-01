import struct

from pocket.qr import make_matrix, render_ascii, render_png


def test_matrix_is_square():
    matrix = make_matrix("https://example.com")
    n = len(matrix)
    assert n >= 21
    assert all(len(row) == n for row in matrix)


def test_ascii_shape_and_blocks():
    matrix = make_matrix("hi")
    text = render_ascii(matrix, quiet=2)
    lines = text.splitlines()
    assert len(lines) == (len(matrix) + 4 + 1) // 2
    assert max(len(line) for line in lines) == len(matrix) + 4
    assert "\u2588" in text


def test_png_header_and_size():
    matrix = make_matrix("hi")
    raw = render_png(matrix, scale=4, quiet=2)
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", raw[16:24])
    side = (len(matrix) + 4) * 4
    assert (width, height) == (side, side)
