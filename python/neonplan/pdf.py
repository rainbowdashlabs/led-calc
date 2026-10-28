"""Printable templates: overview + cut list, 1:1 front laying plan, 1:1 mirrored back routing.

The 1:1 plans are tiled over A4/A3 sheets. Neighbouring sheets overlap by OVERLAP mm; the
overlap is shaded as glue area and carries registration crosses that appear on both sheets.
"""

from __future__ import annotations

import math

import numpy as np

from .i18n import _
from .pdfwriter import Document, text_width

PAPER = {"A4": (210.0, 297.0), "A3": (297.0, 420.0)}
MARGIN = 10.0  # printer-safe margin
OVERLAP = 12.0  # glue overlap between neighbouring sheets
BORDER = 8.0  # extra space around the plate in the 1:1 plans

PINK = (0.93, 0.18, 0.55)
PINK_LIGHT = (1.0, 0.82, 0.91)
ORANGE = (0.92, 0.5, 0.05)
GREEN = (0.1, 0.6, 0.25)
BLUE = (0.1, 0.5, 0.85)
RED = (0.85, 0.1, 0.1)
GREY = (0.55, 0.55, 0.58)
LIGHT = (0.88, 0.88, 0.9)
BLACK = (0, 0, 0)


def REASON(key):
    return {
        "feed": _("Einspeisung", "feed"),
        "same_glyph": _("im selben Buchstaben", "same letter"),
        "next_glyph": _("nächster Buchstabe", "next letter"),
        "next_word": _("nächstes Wort", "next word"),
        "next_line": _("nächste Zeile", "next line"),
        "roll": _("Rollenwechsel (Kabel)", "new roll (cable)"),
    }[key]


def ROLE(key):
    return {"contour": _("Kontur", "outline"), "line": _("Linie", "line"), "dot": _("Punkt", "dot"), "frame": _("Rahmen", "frame")}[key]


def _mm(v: float) -> str:
    return f"{v:,.0f} mm".replace(",", ".")


def _hole_kind(h) -> str:
    outs = [u for u in h["uses"] if u[1] == "out"]
    ins = [u for u in h["uses"] if u[1] == "in"]
    if outs and ins:
        return "both"
    return "out" if outs else "in"


class _View:
    """Maps plan coordinates (mm) to the plan as printed (optionally mirrored)."""

    def __init__(self, plan, mirrored: bool):
        self.W = plan["plate"]["w"]
        self.mirrored = mirrored

    def x(self, x):
        return self.W - x if self.mirrored else x

    def pts(self, pts):
        return [(self.x(p[0]), p[1]) for p in pts]


# --------------------------------------------------------------------------- drawing of plan content


def _draw_plate(c, plan, ox, oy, s=1.0, width=0.6):
    W, H, r = plan["plate"]["w"], plan["plate"]["h"], plan["plate"]["corner"]
    c.stroke_color(*BLACK)
    c.line_width(width)
    c.dash()
    c.round_rect(ox, oy, W * s, H * s, r * s)
    c.stroke()


def _tr(pts, ox, oy, s):
    return [(ox + x * s, oy + y * s) for x, y in pts]


def _draw_letters(c, plan, view, ox, oy, s=1.0, fill=True):
    c.dash()
    for rings in plan["letters"]:
        for ring in rings:
            c.polyline(_tr(view.pts(ring), ox, oy, s), closed=True)
        if fill:
            c.fill_color(0.95, 0.95, 0.96)
            c.stroke_color(*GREY)
            c.line_width(0.2)
            c.ops.append("B*")
        else:
            c.stroke_color(*LIGHT)
            c.line_width(0.25)
            c.stroke()
    c.stroke_color(*GREY)
    c.line_width(0.25)
    for st in plan["strokes"]:
        c.polyline(_tr(view.pts(st), ox, oy, s))
        c.stroke()


def _arrow(c, x, y, dx, dy, size):
    n = math.hypot(dx, dy) or 1
    dx, dy = dx / n, dy / n
    px, py = -dy, dx
    c.move(x - dx * size + px * size * 0.6, y - dy * size + py * size * 0.6)
    c.line(x, y)
    c.line(x - dx * size - px * size * 0.6, y - dy * size - py * size * 0.6)
    c.stroke()


def _draw_pieces_front(c, plan, ox, oy, s=1.0, detail=True):
    w = plan["params"]["strip_width"]
    c.round_caps()
    for p in plan["pieces"]:
        pts = _tr(p["pts"], ox, oy, s)
        c.stroke_color(*PINK_LIGHT)
        c.line_width(w * s)
        c.polyline(pts, p["closed"])
        c.stroke()
    for p in plan["pieces"]:
        pts = _tr(p["pts"], ox, oy, s)
        c.stroke_color(*PINK)
        c.line_width(max(0.25, 0.35 * s))
        c.polyline(pts, p["closed"])
        c.stroke()
        if detail:
            # direction chevrons every ~60 mm
            arr = np.asarray(p["pts"])
            seg = np.linalg.norm(np.diff(arr, axis=0), axis=1)
            cum = np.concatenate([[0], np.cumsum(seg)])
            total = cum[-1]
            for t in np.arange(30, total - 15, 60):
                j = int(np.searchsorted(cum, t))
                j = min(max(j, 1), len(arr) - 1)
                a, b = arr[j - 1], arr[j]
                f = (t - cum[j - 1]) / max(seg[j - 1], 1e-9)
                x, y = a + (b - a) * f
                c.line_width(0.35)
                _arrow(c, ox + x * s, oy + y * s, b[0] - a[0], b[1] - a[1], w * 0.45 * s)
            # end bar for open pieces
            if not p["closed"] and len(arr) >= 2:
                e, d = arr[-1], arr[-1] - arr[-2]
                n = d / (np.linalg.norm(d) or 1)
                q = np.array([-n[1], n[0]]) * w * 0.8
                c.line_width(0.5)
                c.move(ox + (e[0] + q[0]) * s, oy + (e[1] + q[1]) * s)
                c.line(ox + (e[0] - q[0]) * s, oy + (e[1] - q[1]) * s)
                c.stroke()
    c.butt_caps()


def _label_bubble(c, x, y, txt, size=7, fill=(1, 1, 1), stroke=BLACK, color=BLACK):
    w = max(text_width(txt, size, True) + 1.6, size * 0.5)
    h = size * 0.5
    c.fill_color(*fill)
    c.stroke_color(*stroke)
    c.line_width(0.25)
    c.dash()
    c.round_rect(x - w / 2, y - h / 2, w, h, h / 2)
    c.fill_stroke()
    c.text(x, y - size * 0.125, txt, size, True, "center", color)


def _draw_holes(c, plan, view, ox, oy, s=1.0, labels=True):
    r = plan["params"]["hole_diameter"] / 2
    for h in plan["holes"]:
        x, y = ox + view.x(h["x"]) * s, oy + h["y"] * s
        kind = _hole_kind(h)
        col = {"out": ORANGE, "in": GREEN, "both": ORANGE}[kind]
        c.dash()
        c.fill_color(1, 1, 1)
        c.stroke_color(*col)
        c.line_width(0.5)
        c.circle(x, y, r * s)
        c.fill_stroke()
        c.stroke_color(*BLACK)
        c.line_width(0.15)
        c.move(x - r * s * 1.3, y)
        c.line(x + r * s * 1.3, y)
        c.move(x, y - r * s * 1.3)
        c.line(x, y + r * s * 1.3)
        c.stroke()
        if labels:
            txt = {
                "out": _("nach hinten", "to the back"),
                "in": _("nach vorne", "to the front"),
                "both": _("hin & zurück", "back & forth"),
            }[kind]
            c.text(x + r * s + 1, y + 0.6, f"B{h['no']}", 6.5, True, "left", col)
            c.text(x + r * s + 1, y - 2.2, txt, 5.5, False, "left", col)


def _draw_problems(c, plan, ox, oy, s=1.0, labels=True):
    w = plan["params"]["strip_width"]
    c.dash()
    for p in plan["pieces"]:
        for v in p["violations"]:
            c.stroke_color(*RED)
            c.line_width(0.4)
            c.circle(ox + v["x"] * s, oy + v["y"] * s, w * 1.3 * s)
            c.stroke()
            if labels:
                c.text(ox + v["x"] * s + w * 1.4 * s, oy + v["y"] * s, f"R {v['radius']:.0f}", 5.5, True, "left", RED)
        for v in p.get("smoothed", []):
            c.stroke_color(*BLUE)
            c.line_width(0.3)
            c.dash(1, 1)
            c.circle(ox + v["x"] * s, oy + v["y"] * s, w * 1.3 * s)
            c.stroke()
            c.dash()
            if labels:
                c.text(
                    ox + v["x"] * s + w * 1.4 * s,
                    oy + v["y"] * s,
                    _(f"geglättet {v['dev']:.0f} mm", f"smoothed {v['dev']:.0f} mm"),
                    5.5,
                    False,
                    "left",
                    BLUE,
                )
    for m in plan["markers"]:
        c.stroke_color(0.75, 0.2, 0.75)
        c.line_width(0.4)
        c.circle(ox + m["x"] * s, oy + m["y"] * s, w * 1.5 * s)
        c.stroke()
        if labels:
            c.text(
                ox + m["x"] * s, oy + m["y"] * s - w * 1.5 * s - 2.5, _("zu schmal", "too narrow"), 5.5, True, "center", (0.75, 0.2, 0.75)
            )
    for o in plan["omitted"]:
        c.stroke_color(*GREY)
        c.line_width(0.3)
        c.dash(1, 1)
        c.circle(ox + o["x"] * s, oy + o["y"] * s, w * s)
        c.stroke()
        c.dash()
        if labels:
            c.text(ox + o["x"] * s, oy + o["y"] * s + w * s + 1, _("ohne LED", "no LED"), 5, False, "center", GREY)


def _draw_piece_labels(c, plan, view, ox, oy, s=1.0, size=7):
    for p in plan["pieces"]:
        x, y = p["pts"][0]
        _label_bubble(
            c, ox + view.x(x) * s, oy + y * s, str(p["no"]), size, fill=(1, 0.93, 0.6) if p["role"] == "dot" else (1, 1, 1), stroke=PINK
        )


def _path_mid(pts):
    """Point and direction (degrees) in the middle of a polyline (by length)."""
    a = np.asarray(pts, dtype=float)
    seg = np.linalg.norm(np.diff(a, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    t = cum[-1] / 2
    j = min(max(int(np.searchsorted(cum, t)), 1), len(a) - 1)
    f = (t - cum[j - 1]) / max(seg[j - 1], 1e-9)
    p = a[j - 1] + (a[j] - a[j - 1]) * f
    d = a[j] - a[j - 1]
    return p, math.degrees(math.atan2(d[1], d[0]))


def _draw_links(c, plan, view, ox, oy, s=1.0, back=False, labels=True):
    w = plan["params"]["strip_width"]
    for link in plan["links"]:
        raw = link.get("path") or [link["a"], link["b"]]
        pts = [(ox + view.x(x) * s, oy + y * s) for x, y in raw]
        if link["kind"] == "strip":
            c.stroke_color(*(ORANGE if back else (0.98, 0.75, 0.45)))
            c.line_width((w if back else 0.6) * (s if back else 1))
            c.dash() if back else c.dash(2.5, 1.5)
        else:
            c.stroke_color(*BLUE)
            c.line_width(0.6 if back else 0.4)
            c.dash(3, 1.5)
        c.round_caps()
        c.polyline(pts)
        c.stroke()
        c.butt_caps()
        c.dash()
        if back and labels and len(pts) >= 2:
            (mx, my), ang = _path_mid(pts)
            if ang > 90:
                ang -= 180
            if ang < -90:
                ang += 180
            kind = _("Streifen", "strip") if link["kind"] == "strip" else _("Kabel", "cable")
            txt = f"{kind} {_mm(link['length'])}  ({link['from'] or _('Einsp.', 'feed')} > {link['to']})"
            col = ORANGE if link["kind"] == "strip" else BLUE
            nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
            c.text(mx + nx * (w * 0.6 + 1.2), my + ny * (w * 0.6 + 1.2), txt, 6, True, "center", col, angle=ang)
    if back:
        for x in plan.get("back_crossings", []):
            c.stroke_color(*RED)
            c.line_width(0.5)
            c.circle(ox + view.x(x["x"]) * s, oy + x["y"] * s, w * 1.5 * s)
            c.stroke()
            if labels:
                c.text(ox + view.x(x["x"]) * s, oy + x["y"] * s + w * 1.5 * s + 1, _("Kreuzung", "crossing"), 5.5, True, "center", RED)


def _draw_cut(c, plan, view, ox, oy, s=1.0, labels=True):
    """Channels (to cut / mill) and bridges (to leave standing)."""
    cut = plan.get("cut")
    if not cut:
        return
    c.dash()
    for rings in cut["channels"]:
        for ring in rings:
            c.polyline([(ox + view.x(x) * s, oy + y * s) for x, y in ring], closed=True)
        c.fill_color(0.2, 0.2, 0.22)
        c.ops.append("f*")
    c.stroke_color(*BLACK)
    c.line_width(0.25)
    for rings in cut["channels"]:
        for ring in rings:
            c.polyline([(ox + view.x(x) * s, oy + y * s) for x, y in ring], closed=True)
            c.stroke()
    for rings in cut["bridges"]:
        for ring in rings:
            c.polyline([(ox + view.x(x) * s, oy + y * s) for x, y in ring], closed=True)
        c.fill_color(0.55, 0.9, 0.6)
        c.stroke_color(*GREEN)
        c.line_width(0.3)
        c.ops.append("B*")
        if labels:
            ring = np.asarray(rings[0])
            cx, cy = ring.mean(axis=0)
            c.text(ox + view.x(cx) * s, oy + cy * s + plan["params"]["strip_width"] * s, _("Steg", "bridge"), 5.5, True, "center", GREEN)


def _draw_feed(c, plan, view, ox, oy, s=1.0, back=False):
    x, y = ox + view.x(plan["feed"]["x"]) * s, oy + plan["feed"]["y"] * s
    c.fill_color(*GREEN)
    c.circle(x, y, 3 * max(s, 0.4))
    c.fill()
    c.text(
        x,
        y - 6 * max(s, 0.5),
        _("Einspeisung / Netzteil", "feed / power supply") if back else _("Einspeisung", "feed"),
        6.5,
        True,
        "center",
        GREEN,
    )


def _registration_marks(c, plan, tiles, view):
    """Crosses in every overlap region (plan coordinates) so they show up on both sheets."""
    (x0, y0, x1, y1), cols, rows, sx, sy, _pw, _ph = tiles
    c.stroke_color(*BLACK)
    c.line_width(0.2)
    c.dash()
    marks = []
    for ci in range(1, cols):
        xm = x0 + ci * sx + OVERLAP / 2
        for yy in np.arange(y0 + 25, y1 - 10, 70):
            marks.append((xm, yy))
    for ri in range(1, rows):
        ym = y1 - ri * sy - OVERLAP / 2
        for xx in np.arange(x0 + 25, x1 - 10, 70):
            marks.append((xx, ym))
    for x, y in marks:
        c.circle(x, y, 2.2)
        c.move(x - 4, y)
        c.line(x + 4, y)
        c.move(x, y - 4)
        c.line(x, y + 4)
        c.stroke()


def _grid(c, x0, y0, x1, y1, step=50):
    c.stroke_color(0.9, 0.92, 0.95)
    c.line_width(0.15)
    c.dash()
    for x in np.arange(math.floor(x0 / step) * step, x1 + step, step):
        c.move(x, y0)
        c.line(x, y1)
    for y in np.arange(math.floor(y0 / step) * step, y1 + step, step):
        c.move(x0, y)
        c.line(x1, y)
    c.stroke()


# --------------------------------------------------------------------------- tiling


def _tiling(plan, paper):
    W, H = plan["plate"]["w"], plan["plate"]["h"]
    region = (-BORDER, -BORDER, W + BORDER, H + BORDER)
    RW, RH = region[2] - region[0], region[3] - region[1]
    best = None
    for pw_, ph_ in (PAPER[paper], PAPER[paper][::-1]):
        pw, ph = pw_ - 2 * MARGIN, ph_ - 2 * MARGIN - 8  # 8 mm for the sheet header
        sx, sy = pw - OVERLAP, ph - OVERLAP
        cols = max(1, math.ceil((RW - OVERLAP) / sx))
        rows = max(1, math.ceil((RH - OVERLAP) / sy))
        cand = (cols * rows, (pw_, ph_), (region, cols, rows, sx, sy, pw, ph))
        if best is None or cand[0] < best[0]:
            best = cand
    return best[1], best[2]


def _sheet_name(r, c):
    return f"{chr(ord('A') + r)}{c + 1}"


def _tiled_pages(doc, plan, paper, back: bool):
    (PW, PH), tiles = _tiling(plan, paper)
    (x0, y0, x1, y1), cols, rows, sx, sy, pw, ph = tiles
    view = _View(plan, back)
    title = (
        _("RÜCKSEITE – Routing (gespiegelt, Ansicht von hinten)", "BACK – routing (mirrored, seen from behind)")
        if back
        else _("VORDERSEITE – Verlegeplan 1:1", "FRONT – laying plan 1:1")
    )
    for r in range(rows):
        for ci in range(cols):
            c = doc.add_page(PW, PH)
            # plan origin offset on this sheet: tile (r, ci) shows plan x in [tx0, tx0+pw], y in [ty1-ph, ty1]
            tx0 = x0 + ci * sx
            ty1 = y1 - r * sy
            ox = MARGIN - tx0
            oy = MARGIN + ph - ty1
            c.save()
            c.clip_rect(MARGIN, MARGIN, pw, ph)
            # glue areas: left and top overlap of this sheet are glued onto the neighbours
            c.fill_color(0.93, 0.96, 1.0)
            if ci > 0:
                c.rect(MARGIN, MARGIN, OVERLAP, ph)
                c.fill()
            if r > 0:
                c.rect(MARGIN, MARGIN + ph - OVERLAP, pw, OVERLAP)
                c.fill()
            c.save()
            c.ops.append(f"1 0 0 1 {ox * 72 / 25.4:.3f} {oy * 72 / 25.4:.3f} cm")
            _grid(c, x0, y0, x1, y1)
            _draw_plate(c, plan, 0, 0)
            if back:
                _draw_letters(c, plan, view, 0, 0, fill=False)
                c.stroke_color(*LIGHT)
                c.line_width(plan["params"]["strip_width"])
                c.round_caps()
                for p in plan["pieces"]:
                    c.polyline(view.pts(p["pts"]), p["closed"])
                    c.stroke()
                c.butt_caps()
                _draw_links(c, plan, view, 0, 0, back=True)
                _draw_holes(c, plan, view, 0, 0)
                _draw_feed(c, plan, view, 0, 0, back=True)
                _draw_piece_labels(c, plan, view, 0, 0)
            else:
                _draw_letters(c, plan, view, 0, 0)
                _draw_cut(c, plan, view, 0, 0)
                _draw_links(c, plan, view, 0, 0, back=False)
                _draw_pieces_front(c, plan, 0, 0)
                _draw_holes(c, plan, view, 0, 0)
                _draw_problems(c, plan, 0, 0)
                _draw_feed(c, plan, view, 0, 0)
                _draw_piece_labels(c, plan, view, 0, 0)
            _registration_marks(c, plan, tiles, view)
            c.restore()
            # glue-area hints (sheet coordinates)
            if ci > 0:
                c.text(
                    MARGIN + OVERLAP / 2,
                    MARGIN + ph / 2,
                    _(
                        f"Klebefläche – unter/auf Blatt {_sheet_name(r, ci - 1)} legen",
                        f"glue area – put under/over sheet {_sheet_name(r, ci - 1)}",
                    ),
                    6,
                    False,
                    "center",
                    BLUE,
                    angle=90,
                )
            if r > 0:
                c.text(
                    MARGIN + pw / 2,
                    MARGIN + ph - OVERLAP / 2 - 1,
                    _(
                        f"Klebefläche – unter/auf Blatt {_sheet_name(r - 1, ci)} legen",
                        f"glue area – put under/over sheet {_sheet_name(r - 1, ci)}",
                    ),
                    6,
                    False,
                    "center",
                    BLUE,
                )
            c.restore()
            # cut lines along the edges that get trimmed (left / top of sheets that overlap)
            c.stroke_color(*GREY)
            c.line_width(0.2)
            c.dash(2, 1.5)
            c.rect(MARGIN, MARGIN, pw, ph)
            c.stroke()
            c.dash()
            if ci > 0:
                c.text(MARGIN - 1.5, MARGIN + ph - 3, _("schneiden", "cut"), 5.5, False, "right", GREY, angle=90)
            if r > 0:
                c.text(MARGIN + 2, MARGIN + ph + 1.2, _("schneiden", "cut"), 5.5, False, "left", GREY)
            # header
            c.text(MARGIN, PH - MARGIN - 1, title, 9, True, "left", BLACK)
            c.text(
                PW - MARGIN,
                PH - MARGIN - 1,
                _(
                    f"Blatt {_sheet_name(r, ci)}  (Zeile {r + 1}/{rows}, Spalte {ci + 1}/{cols})",
                    f"Sheet {_sheet_name(r, ci)}  (row {r + 1}/{rows}, column {ci + 1}/{cols})",
                ),
                9,
                True,
                "right",
                BLACK,
            )
            sub = _(
                f"„{plan['params']['text'][:40]}“ · Platte {plan['plate']['w']:.0f} × {plan['plate']['h']:.0f} mm · "
                "Maßstab 1:1 – mit 100 % / tatsächlicher Größe drucken",
                f'"{plan["params"]["text"][:40]}" · plate {plan["plate"]["w"]:.0f} × {plan["plate"]["h"]:.0f} mm · '
                "scale 1:1 – print at 100 % / actual size",
            )
            c.text(MARGIN, PH - MARGIN - 5, sub.replace("\n", " "), 6.5, False, "left", GREY)
            # scale check bar (100 mm)
            _scale_bar(c, PW - MARGIN - 105, MARGIN + 3)
    return rows * cols


def _scale_bar(c, x, y):
    c.fill_color(1, 1, 1)
    c.rect(x - 2, y - 2, 109, 8.5)
    c.fill()
    c.stroke_color(*BLACK)
    c.line_width(0.3)
    c.dash()
    c.move(x, y)
    c.line(x + 100, y)
    for i in range(0, 101, 10):
        c.move(x + i, y)
        c.line(x + i, y + (2.5 if i % 50 == 0 else 1.5))
    c.stroke()
    c.text(x + 50, y + 3, _("Prüfmaß: muss genau 100 mm messen", "check scale: must measure exactly 100 mm"), 5.5, False, "center", BLACK)


# --------------------------------------------------------------------------- overview


class _Flow:
    """Simple top-to-bottom text flow with automatic page breaks."""

    def __init__(self, doc, paper):
        self.doc = doc
        self.PW, self.PH = PAPER[paper]
        self.new_page()

    def new_page(self):
        self.c = self.doc.add_page(self.PW, self.PH)
        self.y = self.PH - MARGIN - 4

    def need(self, h):
        if self.y - h < MARGIN + 4:
            self.new_page()

    def text(self, s, size=8.5, bold=False, color=BLACK, indent=0.0, gap=1.4):
        lh = size * 0.3528 * gap
        maxw = self.PW - 2 * MARGIN - indent
        for line in _wrap(s, size, bold, maxw):
            self.need(lh)
            self.c.text(MARGIN + indent, self.y - size * 0.3528, line, size, bold, "left", color)
            self.y -= lh

    def space(self, mm):
        self.y -= mm

    def table(self, headers, rows, widths, aligns, size=7.5, colors=None):
        lh = size * 0.3528 * 1.5
        x0 = MARGIN

        def row(vals, bold=False, color=BLACK):
            self.need(lh)
            x = x0
            for v, w, a in zip(vals, widths, aligns, strict=False):
                tx = {"left": x, "right": x + w - 1, "center": x + w / 2}[a]
                self.c.text(tx, self.y - size * 0.3528, str(v), size, bold, a, color)
                x += w
            self.y -= lh

        row(headers, True, GREY)
        self.c.stroke_color(*LIGHT)
        self.c.line_width(0.2)
        self.c.move(x0, self.y + lh * 0.25)
        self.c.line(x0 + sum(widths), self.y + lh * 0.25)
        self.c.stroke()
        for i, r in enumerate(rows):
            row(r, False, (colors[i] if colors else BLACK))


def _wrap(s, size, bold, maxw):
    words = s.split(" ")
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if text_width(t, size, bold) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _overview(doc, plan, paper, sheet_counts):
    P = plan["params"]
    S = plan["summary"]
    f = _Flow(doc, paper)
    c = f.c
    f.text(_("LED-Neon Leuchtschrift – Übersicht & Zuschnitt", "LED neon sign – overview & cut list"), 15, True)
    f.space(1)
    f.text(f"Text: „{P['text'].replace(chr(10), ' / ')}“", 10)
    mode = (
        _("Kontur (doppelt, an den Außenrändern)", "outline (double, along the edges)")
        if P["mode"] == "contour"
        else _("Form (einfach, Mittellinie)", "shape (single, centre line)")
    )
    conn = (
        _("Streifen durchgehend, Übergänge hinter der Platte", "continuous strip, transitions behind the plate")
        if P["connection"] == "strip"
        else _("Einzelstücke, hinter der Platte verkabelt", "separate pieces, wired behind the plate")
    )
    f.text(_(f"Verlegung: {mode} · {conn}", f"Laying: {mode} · {conn}"), 8.5, color=GREY)
    f.text(
        _(
            f"Streifen {P['strip_width']:g} mm · Mindest-Biegeradius {P['bend_radius']:g} mm · Schnittraster {P['cut_unit']:g} mm · "
            f"Großbuchstaben {P['cap_height']:g} mm · Platte {plan['plate']['w']:.0f} × {plan['plate']['h']:.0f} × "
            f"{P['plate_thickness']:g} mm",
            f"Strip {P['strip_width']:g} mm · min. bend radius {P['bend_radius']:g} mm · cut pitch {P['cut_unit']:g} mm · "
            f"capitals {P['cap_height']:g} mm · plate {plan['plate']['w']:.0f} × {plan['plate']['h']:.0f} × {P['plate_thickness']:g} mm",
        ),
        8.5,
        color=GREY,
    )
    f.space(2)

    # overview drawing (scaled to fit)
    W, H = plan["plate"]["w"], plan["plate"]["h"]
    avail_w = f.PW - 2 * MARGIN - 16
    avail_h = min(f.y - MARGIN - 120, (f.PH - 2 * MARGIN) * 0.42)
    s = min(avail_w / W, avail_h / H)
    ox = MARGIN + 10 + (avail_w - W * s) / 2
    oy = f.y - 6 - H * s
    view = _View(plan, False)
    _draw_plate(c, plan, ox, oy, s, 0.4)
    _draw_letters(c, plan, view, ox, oy, s)
    _draw_links(c, plan, view, ox, oy, s)
    _draw_pieces_front(c, plan, ox, oy, s, detail=False)
    _draw_holes(c, plan, view, ox, oy, s, labels=False)
    _draw_problems(c, plan, ox, oy, s, labels=False)
    _draw_feed(c, plan, view, ox, oy, s)
    _draw_piece_labels(c, plan, view, ox, oy, s, size=6)
    # dimensions
    _dim_h(c, ox, ox + W * s, oy + H * s + 3, f"{W:.0f} mm")
    _dim_v(c, oy, oy + H * s, ox - 4, f"{H:.0f} mm")
    lb = plan.get("bounds")
    if lb:
        _dim_h(
            c,
            ox + lb["x0"] * s,
            ox + lb["x1"] * s,
            oy - 4,
            _(f"Schrift {lb['x1'] - lb['x0']:.0f} mm", f"lettering {lb['x1'] - lb['x0']:.0f} mm"),
            PINK,
        )
    f.y = oy - 10

    f.text(_("Ergebnis", "Result"), 11, True)
    rows = [
        (
            _("Streifen gesamt zu kaufen (gerundet auf Raster)", "strip to buy in total (rounded to the cut pitch)"),
            _mm(S["strip_cut_total"]),
        ),
        (_("davon sichtbar vorne", "visible at the front"), _mm(S["front"])),
        (_("davon hinter der Platte (Streifen)", "behind the plate (strip)"), _mm(S["back_strip"])),
        (_("Kabel hinter der Platte (inkl. Reserve)", "cable behind the plate (incl. reserve)"), _mm(S["cable"])),
        (_("Stücke vorne / Zuschnitte", "pieces at the front / cuts"), f"{S['pieces']} / {S['groups']}"),
        (_("Bohrungen (Ø %g mm)", "holes (Ø %g mm)") % P["hole_diameter"], str(S["holes"])),
        (_("Übergänge hinter der Platte", "transitions behind the plate"), str(S["transitions"])),
    ]
    if lb:
        rows.insert(0, (_("Schriftmaße (B × H)", "lettering size (W × H)"), f"{lb['x1'] - lb['x0']:.0f} × {lb['y1'] - lb['y0']:.0f} mm"))
    f.table(["", ""], rows, [110, 50], ["left", "right"], 8.5)
    f.space(3)

    if plan["warnings"]:
        f.text(_("Hinweise", "Notes"), 11, True, RED)
        for w in plan["warnings"]:
            f.text("• " + w, 8, color=RED, indent=2)
        f.space(2)

    cut = plan.get("cut")
    if cut:
        if cut["mode"] == "groove":
            f.text(
                _(
                    f"Nut fräsen: Breite {cut['width']:g} mm, Tiefe {cut['depth']:g} mm (dunkel im Verlegeplan).",
                    f"Mill a groove: width {cut['width']:g} mm, depth {cut['depth']:g} mm (dark in the laying plan).",
                ),
                9,
                True,
            )
        else:
            f.text(
                _(
                    f"Durchbruch: Kanalbreite {cut['width']:g} mm. {cut['islands']} Teil(e) wären lose und werden von "
                    f"{len(cut['bridges'])} Steg(en) gehalten (grün im Verlegeplan). An jedem Steg ist der Streifen "
                    "unterbrochen und läuft hinter dem Brett.",
                    f"Through cut: channel width {cut['width']:g} mm. {cut['islands']} part(s) would fall out and are held by "
                    f"{len(cut['bridges'])} bridge(s) (green in the laying plan). At every bridge the strip is interrupted "
                    "and runs behind the board.",
                ),
                9,
                True,
            )
        f.space(2)

    if plan["hidden"]:
        f.text(
            _(
                "Verdeckte Übergänge hinter der Platte (Buchstaben aus mehreren Stücken)",
                "Hidden transitions behind the plate (letters made of several pieces)",
            ),
            11,
            True,
            ORANGE,
        )
        for h in plan["hidden"]:
            f.text(f"• {h['char']}: {h['reason']} – {_('Stücke', 'pieces')} {', '.join(map(str, h['pieces']))}", 8, indent=2)
        f.text(
            _(
                "An diesen Stellen den Streifen durch die Bohrung nach hinten führen; die Verbindung ist von vorne nicht sichtbar. "
                "Bei transparenten Platten die Rückseite abdecken.",
                "At these places lead the strip through the hole to the back; the connection is invisible from the front. "
                "Cover the back of transparent plates.",
            ),
            7.5,
            color=GREY,
            indent=2,
        )
        f.space(2)

    f.text(_("Zuschnittliste", "Cut list"), 11, True)
    f.table(
        [
            _("Zuschnitt", "cut"),
            _("Stücke", "pieces"),
            _("vorne", "front"),
            _("hinten", "back"),
            _("Zugabe", "allowance"),
            _("abschneiden", "cut length"),
            _("Hinweis", "note"),
        ],
        [
            (
                f"Z{g['no']}",
                _range(g["pieces"]),
                _mm(g["front"]),
                _mm(g["back"]),
                _mm(P["piece_allowance"]),
                _mm(g["cut"]),
                "; ".join(g["notes"])[:60],
            )
            for g in plan["groups"]
        ],
        [18, 26, 24, 24, 20, 26, 52],
        ["left", "left", "right", "right", "right", "right", "left"],
        7.5,
    )
    f.space(3)

    f.text(_("Verlegereihenfolge", "Laying order"), 11, True)
    rows, cols = [], []
    for p, link in zip(plan["pieces"], plan["links"], strict=False):
        kind = _("Streifen", "strip") if link["kind"] == "strip" else _("Kabel", "cable")
        rows.append(
            (
                p["no"],
                p["char"][:12],
                ROLE(p["role"]) + (_(" (geschl.)", " (closed)") if p["closed"] else ""),
                _mm(p["length"]),
                f"Z{p['group']}",
                f"{kind} {_mm(link['length'])} · {REASON(link['reason'])}",
                f"{len(p['violations'])}" if p["violations"] else "",
            )
        )
        cols.append(ORANGE if link["reason"] == "same_glyph" else BLACK)
    f.table(
        [
            "#",
            _("Zeichen", "char"),
            _("Art", "type"),
            _("Länge", "length"),
            _("Zuschn.", "cut"),
            _("davor hinter der Platte", "before it, behind the plate"),
            _("eng", "tight"),
        ],
        rows,
        [10, 24, 28, 22, 16, 76, 14],
        ["left", "left", "left", "right", "left", "left", "right"],
        7.5,
        cols,
    )
    f.space(3)

    f.text(_("Druck & Montage", "Printing & assembly"), 11, True)
    nf, nb = sheet_counts.get("front", 0), sheet_counts.get("back", 0)
    steps = [
        _(
            "Alle Seiten mit „Tatsächliche Größe“ (100 %, ohne Anpassen) drucken. Das Prüfmaß unten rechts muss genau 100 mm messen.",
            'Print all pages at "actual size" (100 %, no fitting). The check scale at the bottom right must measure exactly 100 mm.',
        ),
        _(
            f"Blätter liegen in einem Raster (A1, A2 … von oben links). Vorderseite: {nf} Blätter, Rückseite: {nb} Blätter.",
            f"Sheets form a grid (A1, A2 … from the top left). Front: {nf} sheets, back: {nb} sheets.",
        ),
        _(
            "Bei jedem Blatt den Rand an der gestrichelten Linie „schneiden“ entfernen, die blaue Klebefläche auf das "
            "Nachbarblatt legen, Passkreuze deckungsgleich ausrichten und kleben.",
            'Trim every sheet along the dashed "cut" line, lay the blue glue area onto the neighbouring sheet, '
            "align the registration crosses and glue.",
        ),
        _(
            "Vorderseite: Vorlage auf die Platte legen, Bohrungen (B-Nummern) ankörnen und bohren, Streifen entlang der "
            "pinken Bahn in Pfeilrichtung verlegen, Stück-Nummern beachten.",
            "Front: put the template on the plate, mark and drill the holes (B numbers), lay the strip along the pink "
            "path in arrow direction, follow the piece numbers.",
        ),
        _(
            "Rückseite (gespiegelt!): Vorlage auf die Rückseite legen. Die orangen Bahnen zeigen, wo der Streifen hinter "
            "der Platte läuft, blaue Linien sind Kabel.",
            "Back (mirrored!): put the template on the back. Orange paths show where the strip runs behind the plate, "
            "blue lines are cables.",
        ),
        _(
            "Rot markierte Stellen sind enger als der Mindest-Biegeradius – dort vorsichtig biegen, abändern oder Schrift vergrößern.",
            "Spots marked red are tighter than the minimum bend radius – bend carefully, change them or enlarge the lettering.",
        ),
    ]
    for i, st in enumerate(steps, 1):
        f.text(f"{i}. {st}", 8, indent=2)


def _range(nums):
    if len(nums) > 3 and nums == list(range(nums[0], nums[-1] + 1)):
        return f"{nums[0]}–{nums[-1]}"
    return ", ".join(map(str, nums))


def _dim_h(c, xa, xb, y, label, col=GREY):
    c.stroke_color(*col)
    c.line_width(0.2)
    c.dash()
    c.move(xa, y)
    c.line(xb, y)
    c.move(xa, y - 1.5)
    c.line(xa, y + 1.5)
    c.move(xb, y - 1.5)
    c.line(xb, y + 1.5)
    c.stroke()
    w = text_width(label, 7) + 2
    c.fill_color(1, 1, 1)
    c.rect((xa + xb) / 2 - w / 2, y - 1.5, w, 3)
    c.fill()
    c.text((xa + xb) / 2, y - 0.9, label, 7, False, "center", col)


def _dim_v(c, ya, yb, x, label, col=GREY):
    c.stroke_color(*col)
    c.line_width(0.2)
    c.dash()
    c.move(x, ya)
    c.line(x, yb)
    c.move(x - 1.5, ya)
    c.line(x + 1.5, ya)
    c.move(x - 1.5, yb)
    c.line(x + 1.5, yb)
    c.stroke()
    w = text_width(label, 7) + 2
    c.fill_color(1, 1, 1)
    c.rect(x - 1.5, (ya + yb) / 2 - w / 2, 3, w)
    c.fill()
    c.text(x + 0.9, (ya + yb) / 2, label, 7, False, "center", col, angle=90)


def render_plan(plan: dict, paper: str = "A4", parts=("overview", "front", "back")) -> bytes:
    paper = paper if paper in PAPER else "A4"
    doc = Document(title=f"LED-Neon Plan – {plan['params']['text'][:40]}")
    counts = {}
    if "front" in parts or "back" in parts:
        _, tiles = _tiling(plan, paper)
        n = tiles[1] * tiles[2]
        counts = {"front": n if "front" in parts else 0, "back": n if "back" in parts else 0}
    if "overview" in parts:
        _overview(doc, plan, paper, counts)
    if "front" in parts:
        _tiled_pages(doc, plan, paper, back=False)
    if "back" in parts:
        _tiled_pages(doc, plan, paper, back=True)
    return doc.tobytes()
