"""Minimal dependency-free PDF writer (vector paths + Helvetica text).

Coordinates are millimetres with the origin at the bottom-left of the page.
Text uses the standard 14 fonts with WinAnsiEncoding, which covers German umlauts.
"""

from __future__ import annotations

import math
import zlib

PT = 72 / 25.4  # points per millimetre

_HELV = [
    278,
    278,
    355,
    556,
    556,
    889,
    667,
    191,
    333,
    333,
    389,
    584,
    278,
    333,
    278,
    278,
    556,
    556,
    556,
    556,
    556,
    556,
    556,
    556,
    556,
    556,
    278,
    278,
    584,
    584,
    584,
    556,
    1015,
    667,
    667,
    722,
    722,
    667,
    611,
    778,
    722,
    278,
    500,
    667,
    556,
    833,
    722,
    778,
    667,
    778,
    722,
    667,
    611,
    722,
    667,
    944,
    667,
    667,
    611,
    278,
    278,
    278,
    469,
    556,
    333,
    556,
    556,
    500,
    556,
    556,
    278,
    556,
    556,
    222,
    222,
    500,
    222,
    833,
    556,
    556,
    556,
    556,
    333,
    500,
    278,
    556,
    500,
    722,
    500,
    500,
    500,
    334,
    260,
    334,
    584,
]


def text_width(s: str, size_pt: float, bold: bool = False) -> float:
    """Approximate width of `s` in millimetres."""
    w = 0
    for ch in s:
        o = ord(ch)
        w += _HELV[o - 32] if 32 <= o < 127 else 556
    return w / 1000 * size_pt * (1.06 if bold else 1.0) / PT


def _esc(s: str) -> bytes:
    b = s.encode("cp1252", errors="replace")
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _n(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


class Canvas:
    def __init__(self, w_mm: float, h_mm: float):
        self.w, self.h = w_mm, h_mm
        self.ops: list[str] = []

    # -- state
    def save(self):
        self.ops.append("q")

    def restore(self):
        self.ops.append("Q")

    def stroke_color(self, r, g, b):
        self.ops.append(f"{_n(r)} {_n(g)} {_n(b)} RG")

    def fill_color(self, r, g, b):
        self.ops.append(f"{_n(r)} {_n(g)} {_n(b)} rg")

    def line_width(self, mm: float):
        self.ops.append(f"{_n(mm * PT)} w")

    def dash(self, on_mm: float = 0, off_mm: float = 0):
        if on_mm <= 0:
            self.ops.append("[] 0 d")
        else:
            self.ops.append(f"[{_n(on_mm * PT)} {_n(off_mm * PT)}] 0 d")

    def round_caps(self):
        self.ops.append("1 J 1 j")

    def butt_caps(self):
        self.ops.append("0 J 0 j")

    def clip_rect(self, x, y, w, h):
        self.ops.append(f"{_n(x * PT)} {_n(y * PT)} {_n(w * PT)} {_n(h * PT)} re W n")

    # -- paths
    def move(self, x, y):
        self.ops.append(f"{_n(x * PT)} {_n(y * PT)} m")

    def line(self, x, y):
        self.ops.append(f"{_n(x * PT)} {_n(y * PT)} l")

    def curve(self, x1, y1, x2, y2, x3, y3):
        self.ops.append(" ".join(_n(v * PT) for v in (x1, y1, x2, y2, x3, y3)) + " c")

    def close(self):
        self.ops.append("h")

    def stroke(self):
        self.ops.append("S")

    def fill(self, evenodd: bool = False):
        self.ops.append("f*" if evenodd else "f")

    def fill_stroke(self):
        self.ops.append("B")

    def polyline(self, pts, closed: bool = False):
        if len(pts) < 2:
            return
        self.move(*pts[0])
        for p in pts[1:]:
            self.line(*p)
        if closed:
            self.close()

    def rect(self, x, y, w, h):
        self.ops.append(f"{_n(x * PT)} {_n(y * PT)} {_n(w * PT)} {_n(h * PT)} re")

    def round_rect(self, x, y, w, h, r):
        r = max(0.0, min(r, w / 2, h / 2))
        if r <= 0:
            self.rect(x, y, w, h)
            return
        k = 0.5523 * r
        self.move(x + r, y)
        self.line(x + w - r, y)
        self.curve(x + w - r + k, y, x + w, y + r - k, x + w, y + r)
        self.line(x + w, y + h - r)
        self.curve(x + w, y + h - r + k, x + w - r + k, y + h, x + w - r, y + h)
        self.line(x + r, y + h)
        self.curve(x + r - k, y + h, x, y + h - r + k, x, y + h - r)
        self.line(x, y + r)
        self.curve(x, y + r - k, x + r - k, y, x + r, y)
        self.close()

    def circle(self, cx, cy, r):
        k = 0.5523 * r
        self.move(cx + r, cy)
        self.curve(cx + r, cy + k, cx + k, cy + r, cx, cy + r)
        self.curve(cx - k, cy + r, cx - r, cy + k, cx - r, cy)
        self.curve(cx - r, cy - k, cx - k, cy - r, cx, cy - r)
        self.curve(cx + k, cy - r, cx + r, cy - k, cx + r, cy)
        self.close()

    # -- text
    def text(self, x, y, s: str, size: float = 9, bold: bool = False, anchor: str = "left", color=(0, 0, 0), angle: float = 0.0):
        if not s:
            return
        w = text_width(s, size, bold)
        dx = {"left": 0, "center": -w / 2, "right": -w}[anchor]
        font = "/F2" if bold else "/F1"
        c, sn = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        ox, oy = x + dx * c, y + dx * sn
        self.ops.append(
            f"BT {font} {_n(size)} Tf {_n(color[0])} {_n(color[1])} {_n(color[2])} rg "
            f"{_n(c)} {_n(sn)} {_n(-sn)} {_n(c)} {_n(ox * PT)} {_n(oy * PT)} Tm ("
        )
        self.ops[-1] = self.ops[-1].encode("latin-1") + _esc(s) + b") Tj ET"

    def content(self) -> bytes:
        out = []
        for op in self.ops:
            out.append(op if isinstance(op, bytes) else op.encode("latin-1"))
        return b"\n".join(out)


class Document:
    def __init__(self, title: str = ""):
        self.pages: list[Canvas] = []
        self.title = title

    def add_page(self, w_mm: float, h_mm: float) -> Canvas:
        c = Canvas(w_mm, h_mm)
        self.pages.append(c)
        return c

    def tobytes(self) -> bytes:
        objs: list[bytes] = []

        def add(b: bytes) -> int:
            objs.append(b)
            return len(objs)

        catalog = add(b"")
        pages = add(b"")
        f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        kids = []
        for pg in self.pages:
            data = zlib.compress(pg.content())
            cs = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream")
            kids.append(
                add(
                    f"<< /Type /Page /Parent {pages} 0 R /MediaBox [0 0 {_n(pg.w * PT)} {_n(pg.h * PT)}] "
                    f"/Resources << /Font << /F1 {f1} 0 R /F2 {f2} 0 R >> >> /Contents {cs} 0 R >>".encode()
                )
            )
        objs[catalog - 1] = f"<< /Type /Catalog /Pages {pages} 0 R /ViewerPreferences << /PrintScaling /None >> >>".encode()
        objs[pages - 1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>".encode()
        info = add(b"<< /Title (" + _esc(self.title) + b") /Producer (neonplan) >>")
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, o in enumerate(objs, start=1):
            offsets.append(len(out))
            out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
        for off in offsets:
            out += f"{off:010d} 00000 n \n".encode()
        out += f"trailer\n<< /Size {len(objs) + 1} /Root {catalog} 0 R /Info {info} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        return bytes(out)
