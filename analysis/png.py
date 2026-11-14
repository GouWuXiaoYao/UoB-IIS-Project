"""A minimal PNG canvas: enough to draw honest figures without matplotlib.

PNG is a signature, an IHDR chunk, one zlib-compressed IDAT and an IEND; there is
no reason to install a plotting library for a couple of bar charts. Text is
rendered with a built-in 5x7 bitmap font (uppercase only), which is legible at
scale 2 and is the reason the figures look plain rather than pretty.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

Color = tuple[int, int, int]

WHITE: Color = (255, 255, 255)
BLACK: Color = (26, 26, 26)
GREY: Color = (140, 140, 140)
LIGHT: Color = (226, 226, 226)
BLUE: Color = (60, 110, 165)
ORANGE: Color = (200, 110, 40)
GREEN: Color = (40, 120, 90)

# 5 wide x 7 tall, rows separated by "/". Only the characters the figures use.
_FONT: dict[str, str] = {
    " ": "00000/00000/00000/00000/00000/00000/00000",
    "A": "01110/10001/10001/11111/10001/10001/10001",
    "B": "11110/10001/10001/11110/10001/10001/11110",
    "C": "01110/10001/10000/10000/10000/10001/01110",
    "D": "11110/10001/10001/10001/10001/10001/11110",
    "E": "11111/10000/10000/11110/10000/10000/11111",
    "F": "11111/10000/10000/11110/10000/10000/10000",
    "G": "01110/10001/10000/10111/10001/10001/01111",
    "H": "10001/10001/10001/11111/10001/10001/10001",
    "I": "01110/00100/00100/00100/00100/00100/01110",
    "J": "00111/00010/00010/00010/00010/10010/01100",
    "K": "10001/10010/10100/11000/10100/10010/10001",
    "L": "10000/10000/10000/10000/10000/10000/11111",
    "M": "10001/11011/10101/10101/10001/10001/10001",
    "N": "10001/11001/10101/10011/10001/10001/10001",
    "O": "01110/10001/10001/10001/10001/10001/01110",
    "P": "11110/10001/10001/11110/10000/10000/10000",
    "Q": "01110/10001/10001/10001/10101/10010/01101",
    "R": "11110/10001/10001/11110/10100/10010/10001",
    "S": "01111/10000/10000/01110/00001/00001/11110",
    "T": "11111/00100/00100/00100/00100/00100/00100",
    "U": "10001/10001/10001/10001/10001/10001/01110",
    "V": "10001/10001/10001/10001/10001/01010/00100",
    "W": "10001/10001/10001/10101/10101/11011/10001",
    "X": "10001/10001/01010/00100/01010/10001/10001",
    "Y": "10001/10001/01010/00100/00100/00100/00100",
    "Z": "11111/00001/00010/00100/01000/10000/11111",
    "0": "01110/10001/10011/10101/11001/10001/01110",
    "1": "00100/01100/00100/00100/00100/00100/01110",
    "2": "01110/10001/00001/00010/00100/01000/11111",
    "3": "11110/00001/00001/01110/00001/00001/11110",
    "4": "00010/00110/01010/10010/11111/00010/00010",
    "5": "11111/10000/11110/00001/00001/10001/01110",
    "6": "00110/01000/10000/11110/10001/10001/01110",
    "7": "11111/00001/00010/00100/01000/01000/01000",
    "8": "01110/10001/10001/01110/10001/10001/01110",
    "9": "01110/10001/10001/01111/00001/00010/01100",
    ".": "00000/00000/00000/00000/00000/01100/01100",
    ",": "00000/00000/00000/00000/01100/01100/11000",
    ":": "00000/01100/01100/00000/01100/01100/00000",
    ";": "00000/01100/01100/00000/01100/01100/11000",
    "-": "00000/00000/00000/11111/00000/00000/00000",
    "+": "00000/00100/00100/11111/00100/00100/00000",
    "=": "00000/00000/11111/00000/11111/00000/00000",
    "%": "11001/11010/00010/00100/01000/01011/10011",
    "(": "00010/00100/01000/01000/01000/00100/00010",
    ")": "01000/00100/00010/00010/00010/00100/01000",
    "/": "00001/00010/00010/00100/01000/01000/10000",
    "<": "00010/00100/01000/10000/01000/00100/00010",
    ">": "01000/00100/00010/00001/00010/00100/01000",
    "_": "00000/00000/00000/00000/00000/00000/11111",
    "#": "01010/01010/11111/01010/11111/01010/01010",
    "*": "00000/10101/01110/11111/01110/10101/00000",
    "?": "01110/10001/00001/00010/00100/00000/00100",
    "!": "00100/00100/00100/00100/00100/00000/00100",
    "'": "00100/00100/00000/00000/00000/00000/00000",
    '"': "01010/01010/00000/00000/00000/00000/00000",
    "|": "00100/00100/00100/00100/00100/00100/00100",
}

GLYPH_W = 5
GLYPH_H = 7


class Canvas:
    def __init__(self, width: int, height: int, background: Color = WHITE) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("canvas needs a positive size")
        self.width = width
        self.height = height
        self.pixels = bytearray(bytes(background) * (width * height))

    # -- primitives ---------------------------------------------------------
    def set_pixel(self, x: float, y: float, color: Color) -> None:
        # Coordinates arrive from layout arithmetic, so rounding happens here once
        # rather than at every call site.
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < self.width and 0 <= yi < self.height:
            i = (yi * self.width + xi) * 3
            self.pixels[i : i + 3] = bytes(color)

    def fill_rect(self, x: float, y: float, w: float, h: float, color: Color) -> None:
        xi, yi = int(round(x)), int(round(y))
        wi, hi = int(round(w)), int(round(h))
        for yy in range(max(0, yi), min(self.height, yi + hi)):
            row = (yy * self.width) * 3
            start = row + max(0, xi) * 3
            stop = row + min(self.width, xi + wi) * 3
            if stop > start:
                self.pixels[start:stop] = bytes(color) * ((stop - start) // 3)

    def line(self, x0: float, y0: float, x1: float, y1: float, color: Color, width: int = 1) -> None:
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if width <= 1:
                self.set_pixel(x0, y0, color)
            else:
                self.fill_rect(x0 - width // 2, y0 - width // 2, width, width, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def dashed(self, x0: int, y0: int, x1: int, y1: int, color: Color, dash: int = 4) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0))
        for i in range(0, steps, dash * 2):
            frac0, frac1 = i / steps, min(1.0, (i + dash) / steps)
            self.line(
                round(x0 + (x1 - x0) * frac0),
                round(y0 + (y1 - y0) * frac0),
                round(x0 + (x1 - x0) * frac1),
                round(y0 + (y1 - y0) * frac1),
                color,
            )

    def box(self, x: int, y: int, w: int, h: int, color: Color) -> None:
        self.fill_rect(x, y, w, 1, color)
        self.fill_rect(x, y + h - 1, w, 1, color)
        self.fill_rect(x, y, 1, h, color)
        self.fill_rect(x + w - 1, y, 1, h, color)

    # -- text ---------------------------------------------------------------
    @staticmethod
    def text_width(text: str, scale: int = 2) -> int:
        return len(text) * (GLYPH_W + 1) * scale - scale

    def text(self, x: int, y: int, text: str, color: Color = BLACK, scale: int = 2) -> None:
        cursor = x
        for raw in text:
            ch = raw.upper() if raw.isalpha() else raw
            glyph = _FONT.get(ch, _FONT["?"])
            rows = glyph.split("/")
            for ry, bits in enumerate(rows):
                for rx, bit in enumerate(bits):
                    if bit == "1":
                        self.fill_rect(
                            cursor + rx * scale, y + ry * scale, scale, scale, color
                        )
            cursor += (GLYPH_W + 1) * scale

    def text_center(self, cx: int, y: int, text: str, color: Color = BLACK, scale: int = 2) -> None:
        self.text(cx - self.text_width(text, scale) // 2, y, text, color, scale)

    # -- output -------------------------------------------------------------
    def png_bytes(self) -> bytes:
        raw = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            raw.append(0)  # filter type 0 == "None"
            raw += self.pixels[y * stride : (y + 1) * stride]

        def chunk(tag: bytes, payload: bytes) -> bytes:
            return (
                struct.pack(">I", len(payload))
                + tag
                + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
            )

        ihdr = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b"")
        )

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.png_bytes())
        return target
