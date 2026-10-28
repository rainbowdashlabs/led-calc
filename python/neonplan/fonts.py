"""Load fonts and turn text into geometry (mm).

Two kinds of fonts:
- Outline fonts (TTF/OTF): every glyph is an area (polygon with holes).
- Hershey fonts (.jhf): every glyph consists of polylines (single-stroke font).
"""

from __future__ import annotations

import io
import itertools
import math
from dataclasses import dataclass, field
from typing import ClassVar

import numpy as np
import shapely
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from shapely import affinity
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon
from shapely.ops import unary_union

# --------------------------------------------------------------------------- Outline fonts


class _FlattenPen(BasePen):
    """Flatten glyph contours into polylines (curves are subdivided)."""

    def __init__(self, glyph_set, step: float):
        super().__init__(glyph_set)
        self.step = step
        self.contours: list[list[tuple[float, float]]] = []
        self._cur: list[tuple[float, float]] | None = None

    def _moveTo(self, p):
        self._cur = [p]

    def _lineTo(self, p):
        self._cur.append(p)

    def _n(self, pts) -> int:
        length = sum(math.dist(a, b) for a, b in itertools.pairwise(pts))
        return max(2, min(64, math.ceil(length / self.step)))

    def _curveToOne(self, p1, p2, p3):
        p0 = self._cur[-1]
        n = self._n([p0, p1, p2, p3])
        for i in range(1, n + 1):
            t = i / n
            mt = 1 - t
            self._cur.append(
                (
                    mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0],
                    mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1],
                )
            )

    def _qCurveToOne(self, p1, p2):
        p0 = self._cur[-1]
        n = self._n([p0, p1, p2])
        for i in range(1, n + 1):
            t = i / n
            mt = 1 - t
            self._cur.append(
                (
                    mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                    mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1],
                )
            )

    def _closePath(self):
        if self._cur and len(self._cur) >= 3:
            self.contours.append(self._cur)
        self._cur = None

    def _endPath(self):  # open contours practically never occur in fonts
        self._cur = None


def _winding_number(pt, ring: np.ndarray) -> int:
    """Winding number of a point with respect to a (possibly self-intersecting) ring."""
    x, y = pt
    a = ring
    b = np.roll(ring, -1, axis=0)
    upward = (a[:, 1] <= y) & (b[:, 1] > y)
    downward = (a[:, 1] > y) & (b[:, 1] <= y)
    cross = (b[:, 0] - a[:, 0]) * (y - a[:, 1]) - (x - a[:, 0]) * (b[:, 1] - a[:, 1])
    return int(np.sum(upward & (cross > 0)) - np.sum(downward & (cross < 0)))


def contours_to_shape(contours) -> Polygon | MultiPolygon:
    """Fill contours using the nonzero rule (like font rasterisers do)."""
    rings = [np.asarray(c, dtype=float) for c in contours if len(c) >= 3]
    if not rings:
        return Polygon()
    if len(rings) == 1:
        return shapely.make_valid(Polygon(rings[0])).buffer(0)
    noded = unary_union([LineString(np.vstack([r, r[:1]])) for r in rings])
    faces = shapely.get_parts(shapely.polygonize(shapely.get_parts(noded)))
    filled = []
    for face in faces:
        if face.area <= 1e-9:
            continue
        p = face.point_on_surface()
        if sum(_winding_number((p.x, p.y), r) for r in rings) != 0:
            filled.append(face)
    return unary_union(filled).buffer(0) if filled else Polygon()


@dataclass
class OutlineFont:
    font: TTFont
    cap_height: float  # in font units
    upm: int
    _cache: dict = field(default_factory=dict)

    @classmethod
    def from_bytes(cls, data: bytes, weight: float | None = None) -> OutlineFont:
        font = TTFont(io.BytesIO(data), lazy=False)
        if "fvar" in font:
            # variable font: pin every axis, the weight to the requested value
            from fontTools.varLib import instancer

            pins = {}
            for ax in font["fvar"].axes:
                v = ax.defaultValue
                if ax.axisTag == "wght" and weight is not None:
                    v = min(max(float(weight), ax.minValue), ax.maxValue)
                pins[ax.axisTag] = v
            font = instancer.instantiateVariableFont(font, pins)
        upm = font["head"].unitsPerEm
        cap = 0
        os2 = font.get("OS/2")
        if os2 is not None and getattr(os2, "sCapHeight", 0):
            cap = os2.sCapHeight
        obj = cls(font, 0, upm)
        if cap <= 0:
            h = obj.glyph_shape("H")
            cap = h.bounds[3] if not h.is_empty else upm * 0.7
        obj.cap_height = cap
        return obj

    def has_char(self, ch: str) -> bool:
        return ord(ch) in self.font.getBestCmap()

    def advance(self, ch: str) -> float:
        name = self.font.getBestCmap().get(ord(ch))
        if name is None:
            return self.upm * 0.3
        return self.font["hmtx"][name][0]

    def glyph_shape(self, ch: str):
        if ch in self._cache:
            return self._cache[ch]
        cmap = self.font.getBestCmap()
        name = cmap.get(ord(ch))
        if name is None:
            shape = Polygon()
        else:
            gs = self.font.getGlyphSet()
            pen = _FlattenPen(gs, step=self.upm / 400)
            gs[name].draw(pen)
            shape = contours_to_shape(pen.contours)
        self._cache[ch] = shape
        return shape


# --------------------------------------------------------------------------- Hershey fonts


@dataclass
class HersheyFont:
    glyphs: dict  # char -> (left, right, [ [(x,y),...], ... ])
    cap_height: float = 21.0

    @classmethod
    def from_bytes(cls, data: bytes) -> HersheyFont:
        text = data.decode("ascii", errors="replace")
        lines = [ln.rstrip("\r\n") for ln in text.splitlines() if ln.strip()]
        glyphs = {}
        for idx, line in enumerate(lines):
            ch = chr(32 + idx)
            body = line[8:]
            left = ord(body[0]) - ord("R")
            right = ord(body[1]) - ord("R")
            coords = body[2:]
            strokes, cur = [], []
            for i in range(0, len(coords) - 1, 2):
                pair = coords[i : i + 2]
                if pair == " R":
                    if len(cur) >= 2:
                        strokes.append(cur)
                    cur = []
                    continue
                x = ord(pair[0]) - ord("R")
                y = ord(pair[1]) - ord("R")
                cur.append((x - left, 9 - y))  # baseline at y=9 (Hershey y axis points down)
            if len(cur) >= 2:
                strokes.append(cur)
            glyphs[ch] = (left, right, strokes)
        font = cls(glyphs)
        if "H" in glyphs and glyphs["H"][2]:
            ys = [p[1] for s in glyphs["H"][2] for p in s]
            font.cap_height = max(ys) - min(0, min(ys))
        return font

    # Hershey has no umlauts - compose them from the base letter plus two dots.
    _COMPOSE: ClassVar[dict[str, str]] = {"ä": "a", "ö": "o", "ü": "u", "Ä": "A", "Ö": "O", "Ü": "U"}

    def has_char(self, ch: str) -> bool:
        return ch in self.glyphs or ch in self._COMPOSE or ch == "ß"

    def advance(self, ch: str) -> float:
        if ch == "ß":
            return self.advance("s") * 2
        ch = self._COMPOSE.get(ch, ch)
        g = self.glyphs.get(ch)
        return (g[1] - g[0]) if g else 16

    def glyph_lines(self, ch: str) -> list[list[tuple[float, float]]]:
        if ch == "ß":
            s = self.glyph_lines("s")
            adv = self.advance("s")
            return s + [[(x + adv, y) for x, y in st] for st in s]
        base = self._COMPOSE.get(ch)
        if base:
            strokes = list(self.glyphs[base][2])
            xs = [p[0] for s in strokes for p in s]
            ys = [p[1] for s in strokes for p in s]
            cx = (min(xs) + max(xs)) / 2
            top = max(ys) + 3
            for dx in (-3, 3):
                strokes.append([(cx + dx - 0.5, top), (cx + dx + 0.5, top)])
            return strokes
        g = self.glyphs.get(ch)
        return g[2] if g else []


# --------------------------------------------------------------------------- Layout


@dataclass
class GlyphPlacement:
    char: str
    line: int
    word: int
    geometry: object  # Polygon/MultiPolygon (outline) or MultiLineString (Hershey), in mm


@dataclass
class TextLayout:
    kind: str  # "outline" | "hershey"
    glyphs: list[GlyphPlacement]
    missing: list[str]

    @property
    def geometry(self):
        geoms = [g.geometry for g in self.glyphs if not g.geometry.is_empty]
        if not geoms:
            return Polygon() if self.kind == "outline" else MultiLineString()
        if self.kind == "outline":
            return unary_union(geoms)
        return MultiLineString([ls for g in geoms for ls in shapely.get_parts(g)])


def load_font(data: bytes, kind: str, weight: float | None = None):
    return HersheyFont.from_bytes(data) if kind == "hershey" else OutlineFont.from_bytes(data, weight)


def weight_range(data: bytes):
    """(min, max) of the weight axis of a variable font, or None."""
    font = TTFont(io.BytesIO(data), lazy=True)
    if "fvar" not in font:
        return None
    for ax in font["fvar"].axes:
        if ax.axisTag == "wght":
            return ax.minValue, ax.maxValue
    return None


def layout_text(
    font,
    kind: str,
    text: str,
    cap_height_mm: float,
    tracking_mm: float = 0.0,
    line_spacing: float = 1.6,
    align: str = "center",
    width_scale: float = 1.0,
) -> TextLayout:
    """Lay out the text so that capital letters are cap_height_mm tall.

    `width_scale` stretches (>1) or condenses (<1) every glyph horizontally.
    """
    scale = cap_height_mm / font.cap_height
    sx = scale * width_scale
    lines = text.replace("\r", "").split("\n")
    placed: list[GlyphPlacement] = []
    missing: list[str] = []
    widths = []
    rows = []
    word = 0
    for line in lines:
        x = 0.0
        row = []
        word += 1
        for ch in line:
            if ch == " ":
                x += font.advance(" ") * sx + tracking_mm
                word += 1
                continue
            if not font.has_char(ch):
                if ch not in missing:
                    missing.append(ch)
                continue
            row.append((ch, x, word))
            x += font.advance(ch) * sx + tracking_mm
        widths.append(max(0.0, x - tracking_mm))
        rows.append(row)
    max_w = max(widths) if widths else 0.0
    for li, row in enumerate(rows):
        if align == "center":
            dx = (max_w - widths[li]) / 2
        elif align == "right":
            dx = max_w - widths[li]
        else:
            dx = 0.0
        dy = -li * cap_height_mm * line_spacing
        for ch, x, wi in row:
            if kind == "hershey":
                strokes = font.glyph_lines(ch)
                geom = (
                    MultiLineString([[(px * sx + x + dx, py * scale + dy) for px, py in s] for s in strokes])
                    if strokes
                    else MultiLineString()
                )
            else:
                shape = font.glyph_shape(ch)
                geom = affinity.affine_transform(shape, [sx, 0, 0, scale, x + dx, dy]) if not shape.is_empty else Polygon()
            placed.append(GlyphPlacement(ch, li, wi, geom))
    return TextLayout(kind, placed, missing)
