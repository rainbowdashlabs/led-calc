"""Public entry points used by the web worker (Pyodide) and the CLI.

`compute(params, font_bytes)` returns a JSON-serialisable plan.
`make_pdf(plan, params)` renders the printable cut and routing templates.
All user-facing strings (warnings, notes) are German because the UI is German.
"""

from __future__ import annotations

import contextlib
import hashlib
import math

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from . import cutout, graph, paths, routing
from .fonts import layout_text, load_font, weight_range
from .i18n import _, set_lang

DEFAULTS = {
    "text": "Hallo",
    "font_kind": "outline",  # "outline" | "hershey"
    "font_weight": None,  # weight of a variable font; None = 300 (single) / 700 (contour)
    "mode": "contour",  # "contour" (outline, doubled) | "single" (centreline)
    "cap_height": 150.0,  # mm, height of capital letters
    "tracking": 0.0,  # mm, extra letter spacing
    "width_scale": 1.0,  # horizontal glyph scale (1 = original width)
    "line_spacing": 1.5,  # x cap height
    "align": "center",
    "strip_width": 7.0,  # mm
    "bend_radius": 30.0,  # mm, minimum bend radius for a 90 degree bend
    "contour_offset": None,  # mm from letter edge to strip centre; None = strip_width / 2
    "auto_smooth": False,  # opt-in: smooth spots tighter than smooth_radius (changes the shape)
    "smooth_radius": None,  # mm, target radius for auto smoothing; None = bend_radius
    "smooth_max_dev": 8.0,  # mm, how far auto smoothing may move the strip
    "hershey_stroke": None,  # mm, stroke width when outlining a single-stroke font; None = 3 x strip width
    "dot_mode": "through",  # "through" | "separate" | "omit"
    "umlaut_style": "dots",  # "dots" | "bar"
    "margin": 40.0,  # mm, plate margin around the lettering
    "plate_corner": 10.0,  # mm, corner radius of the plate
    "plate_thickness": 5.0,  # mm
    "hole_diameter": 10.0,  # mm
    "connection": "strip",  # "strip" | "cable"
    "feed": "bottom-left",
    "pass_extra": 10.0,  # mm, extra strip per pass through the plate (bending)
    "piece_allowance": 0.0,  # mm, extra per cut piece (connector / end cap)
    "cable_reserve": 50.0,  # mm, extra per wire
    "cut_unit": 10.0,  # mm, strip can only be cut at this pitch
    "roll_length": 5000.0,  # mm
    "lang": "de",  # language of messages and PDF: "de" | "en"
    "frame": False,  # rectangular LED frame around the lettering
    "frame_inset": None,  # mm from the plate edge to the frame strip centre; None = margin / 2
    "frame_corners": "round",  # "round" (bend radius) | "butt" (four straight pieces)
    "cut_mode": "none",  # "none" | "groove" | "through" (recess the strip into the board)
    "cut_tolerance": 1.0,  # mm added to the strip width for the channel
    "cut_depth": None,  # mm, groove depth; None = strip height (= strip width)
    "bridge_width": 8.0,  # mm, bridges that hold islands in "through" mode
}

DOT_CHARS = set("ijäöüÄÖÜ.:;!?ÿ")
UMLAUTS = set("äöüÄÖÜ")

_font_cache: dict = {}


def _font(data: bytes, kind: str, weight=None):
    key = (hashlib.sha1(data).hexdigest(), kind, weight)
    if key not in _font_cache:
        if len(_font_cache) > 24:
            _font_cache.clear()
        _font_cache[key] = load_font(data, kind, weight)
    return _font_cache[key]


def effective_weight(data: bytes, kind: str, mode: str, weight=None):
    """Weight used for a variable font: explicit, else thin for single-line, bold for outlines."""
    if kind != "outline":
        return None
    rng = weight_range(data)
    if rng is None:
        return None
    w = weight if weight not in (None, "") else (300 if mode == "single" else 700)
    return float(min(max(float(w), rng[0]), rng[1]))


def _parts(geom):
    return [g for g in shapely.get_parts(geom) if not g.is_empty]


def _rings(poly):
    out = [np.asarray(poly.exterior.coords)[:-1]]
    out += [np.asarray(r.coords)[:-1] for r in poly.interiors]
    return out


def _segment_for(poly, strip_width):
    """Short straight piece along the long axis of a small shape (used for dots)."""
    rect = poly.minimum_rotated_rectangle
    c = np.asarray(rect.exterior.coords)[:4] if rect.geom_type == "Polygon" else np.asarray(poly.centroid.coords) * np.ones((4, 1))
    e1, e2 = c[1] - c[0], c[2] - c[1]
    axis = e1 if np.linalg.norm(e1) >= np.linalg.norm(e2) else e2
    L = float(np.linalg.norm(axis))
    centre = np.asarray(poly.centroid.coords[0])
    axis = np.array([1.0, 0.0]) if L < 1e-06 else axis / L
    half = max(0.5, (L - strip_width) / 2)
    return np.vstack([centre - axis * half, centre + axis * half])


def compute(params: dict, font_bytes: bytes, progress=None, manual: list | None = None) -> dict:
    """Compute the full plan.

    progress: optional callable(fraction, label) for UI feedback.
    manual:   optional list of hand-edited pieces (from the editor). When given, the
              generated strip paths are replaced by these and only routing, checks and
              lengths are recomputed.
    """

    def report(frac, label):
        if progress is not None:
            with contextlib.suppress(Exception):  # never let UI feedback break the computation
                progress(float(frac), label)

    report(0.02, "Schrift setzen")
    P = {**DEFAULTS, **{k: v for k, v in params.items() if v is not None}}
    set_lang(P.get("lang"))
    w = float(P["strip_width"])
    r = float(P["bend_radius"])
    H = float(P["cap_height"])
    offset = float(P["contour_offset"]) if P.get("contour_offset") not in (None, "") else w / 2
    warnings: list[str] = []

    weight = effective_weight(font_bytes, P["font_kind"], P["mode"], P.get("font_weight"))
    font = _font(font_bytes, P["font_kind"], weight)
    lay = layout_text(
        font, P["font_kind"], P["text"], H, float(P["tracking"]), float(P["line_spacing"]), P["align"], float(P["width_scale"])
    )
    if lay.missing:
        warnings.append(
            _("Zeichen nicht in der Schrift enthalten und ausgelassen: ", "Characters missing in the font (skipped): ")
            + " ".join(lay.missing)
        )
    if not lay.glyphs:
        return {"ok": False, "warnings": [*warnings, _("Kein darstellbarer Text.", "No printable text.")]}

    glyph_word = {i: g.word for i, g in enumerate(lay.glyphs)}
    glyph_line = {i: g.line for i, g in enumerate(lay.glyphs)}
    hershey = P["font_kind"] == "hershey"

    # ---------------------------------------------------------------- letter areas
    if hershey:
        stroke = float(P["hershey_stroke"]) if P.get("hershey_stroke") else 3 * w
        glyph_areas = [g.geometry.buffer(stroke / 2) if not g.geometry.is_empty else Polygon() for g in lay.glyphs]
    else:
        glyph_areas = [g.geometry for g in lay.glyphs]
    shape = unary_union([a for a in glyph_areas if not a.is_empty])

    # move everything so that the plate starts at (0, 0)
    minx, miny, maxx, maxy = shape.bounds
    m = float(P["margin"])
    dx, dy = m - minx, m - miny
    shape = affinity.translate(shape, dx, dy)
    glyph_areas = [affinity.translate(a, dx, dy) for a in glyph_areas]
    glyph_lines = [affinity.translate(g.geometry, dx, dy) for g in lay.glyphs] if hershey else None
    plate_w, plate_h = (maxx - minx) + 2 * m, (maxy - miny) + 2 * m

    def glyphs_of(geom):
        """Indices of glyphs overlapping `geom`, best match first."""
        hits = []
        for i, a in enumerate(glyph_areas):
            if a.is_empty or not a.intersects(geom):
                continue
            hits.append((a.intersection(geom).area if geom.area > 0 else 1.0, i))
        hits.sort(reverse=True)
        return [i for _, i in hits]

    report(0.1, "Formen analysieren")
    # ---------------------------------------------------------------- components
    components = []
    for comp in _parts(shape):
        gi = glyphs_of(comp)
        if not gi:
            continue
        minx_, miny_, maxx_, maxy_ = comp.bounds
        size = max(maxx_ - minx_, maxy_ - miny_)
        small = size < 0.32 * H and comp.area < 0.07 * H * H
        is_dot = small and lay.glyphs[gi[0]].char in DOT_CHARS
        components.append({"geom": comp, "glyphs": gi, "dot": is_dot})

    joined = sorted({tuple(sorted(c["glyphs"])) for c in components if len(c["glyphs"]) > 1})

    pieces: list[routing.Piece] = []
    markers: list[dict] = []  # narrow spots etc.
    omitted: list[dict] = []
    step = 1.5

    def add_piece(pts, closed, comp, role, butt_s=False, butt_e=False, notes=None, inner=False):
        pts = np.asarray(pts, dtype=float)
        gi = comp["glyphs"][0]
        if len(comp["glyphs"]) > 1 and len(pts) >= 2:
            # connected script: attribute the piece to the glyph it overlaps most
            band = (LineString(np.vstack([pts, pts[:1]])) if closed else LineString(pts)).buffer(w)
            best = max(comp["glyphs"], key=lambda i: glyph_areas[i].intersection(band).area)
            gi = best
        pieces.append(
            routing.Piece(
                pts=pts,
                closed=closed,
                char=lay.glyphs[gi].char,
                glyph=gi,
                role=role,
                butt_start=butt_s,
                butt_end=butt_e,
                notes=list(notes or []),
                inner=inner,
            )
        )

    # umlauts as a bar: merge the two dot components of every umlaut glyph
    bar_done: set[int] = set()
    if P["umlaut_style"] == "bar" and manual is None:
        by_glyph: dict[int, list] = {}
        for c in components:
            if c["dot"] and lay.glyphs[c["glyphs"][0]].char in UMLAUTS:
                by_glyph.setdefault(c["glyphs"][0], []).append(c)
        for gi, dots in by_glyph.items():
            if len(dots) < 2:
                continue
            dots.sort(key=lambda c: c["geom"].centroid.x)
            left, right = dots[0]["geom"], dots[-1]["geom"]
            y = (left.centroid.y + right.centroid.y) / 2
            x0 = left.bounds[0] + w / 2
            x1 = right.bounds[2] - w / 2
            for c in dots:
                c["bar"] = True
            add_piece(
                [(x0, y), (x1, y)],
                False,
                dots[0],
                "dot",
                notes=[_("Umlaut-Punkte als waagerechter Strich", "Umlaut dots as a horizontal bar")],
            )
            bar_done.add(gi)

    def single_line_pieces(comp):
        poly = comp["geom"]
        sample = min(max(H / 120, 0.4), 2.0)
        g = graph.medial_axis(poly, sample)
        graph.prune(g, poly, factor=0.38, min_keep=w * 0.25)
        stems = graph.stem_zones(poly, min_len=0.12 * H, min_width=0.6 * w, max_width=0.45 * H)
        graph.extend_leaves(g, poly, end_gap=w / 2, stems=stems)
        if not g.edges:
            add_piece(_segment_for(poly, w), False, comp, "dot" if comp["dot"] else "line")
            return
        joints = graph.junctions(g, poly)
        for t in graph.decompose(g, dir_dist=max(4.0, 0.1 * H)):
            if paths.length(t.pts, t.closed) < max(0.5, w):
                continue
            # inside straight strokes the strip runs exactly on the stroke's centre line;
            # then the dents at junctions are removed between the straightened parts
            pts = graph.snap_to_stems(paths.resample(t.pts, 1.0, t.closed), stems)
            pts = graph.straighten_at_junctions(pts, t.closed, joints, t.start_butt, t.end_butt)
            add_piece(pts, t.closed, comp, "line", t.start_butt, t.end_butt)

    def contour_pieces(comp):
        poly = comp["geom"]
        inset = poly.buffer(-offset)
        if inset.is_empty or inset.area < 0.05 * poly.area:
            notes = [
                _(
                    "Strich zu schmal für Kontur bei dieser Streifenbreite – einfach gelegt",
                    "Stroke too narrow for an outline with this strip width – laid as single line",
                )
            ]
            n0 = len(pieces)
            single_line_pieces(comp)
            for p in pieces[n0:]:
                p.notes += notes
            return
        # spots where the two strip lines would overlap (stroke narrower than 2 x strip width)
        half = w / 2 * 0.95
        opened = inset.buffer(-half).buffer(half)
        narrow = inset.difference(opened.buffer(0.2))
        for zone in _parts(narrow):
            if zone.area > w * w * 0.5:
                c = zone.representative_point()
                markers.append(
                    {
                        "x": c.x,
                        "y": c.y,
                        "type": "narrow",
                        "text": _("Strich zu schmal – Streifen überlappen", "Stroke too narrow – strips overlap"),
                    }
                )
        for part in _parts(inset):
            for ri, ring in enumerate(_rings(part)):
                if paths.length(ring, True) < 3 * w:
                    continue
                if comp["dot"]:
                    smoothed = paths.smooth_path(ring, r, True, step)
                    if paths.find_violations(smoothed, r, True, step):
                        add_piece(
                            _segment_for(poly, w),
                            False,
                            comp,
                            "dot",
                            notes=[
                                _(
                                    "Punkt zu klein für Kontur-Ring (Biegeradius) – als kurzes Stück gelegt",
                                    "Dot too small for an outline ring (bend radius) – laid as a short piece",
                                )
                            ],
                        )
                        continue
                add_piece(ring, True, comp, "dot" if comp["dot"] else "contour", inner=ri > 0)

    for ci, comp in enumerate(components if manual is None else []):
        report(0.15 + 0.35 * ci / max(1, len(components)), "Streifenbahnen erzeugen")
        if comp.get("bar"):
            continue
        if comp["dot"] and P["mode"] == "single":
            add_piece(_segment_for(comp["geom"], w), False, comp, "dot")
        elif P["mode"] == "contour":
            contour_pieces(comp)
        elif not hershey:
            single_line_pieces(comp)

    if hershey and P["mode"] == "single" and manual is None:
        pieces = []
        for gi, (g, lines) in enumerate(zip(lay.glyphs, glyph_lines, strict=False)):
            if lines.is_empty:
                continue
            gr = graph.graph_from_linework(lines, snap=H * 0.004)
            comp = {"glyphs": [gi], "dot": False}
            for t in graph.decompose(gr):
                span = t.pts.max(axis=0) - t.pts.min(axis=0)
                is_dot = max(span) < 0.2 * H and g.char in DOT_CHARS and (t.pts[:, 1].min() > 0.55 * H or g.char in ".:;!?")
                if is_dot:
                    # a dot drawn as a tiny loop becomes a short straight piece
                    c = (t.pts.max(axis=0) + t.pts.min(axis=0)) / 2
                    half = max(w, span[0]) / 2
                    offset = np.array([half, 0.0])
                    t.pts, t.closed = np.vstack([c - offset, c + offset]), False
                    t.start_butt = t.end_butt = False
                add_piece(t.pts, t.closed, comp, "dot" if is_dot else "line", t.start_butt, t.end_butt)
        if P["umlaut_style"] == "bar":
            pieces = _hershey_umlaut_bars(pieces, lay, w)

    # ---------------------------------------------------------------- hand-edited pieces
    if manual is not None:
        pieces = [
            routing.Piece(
                pts=np.asarray(m["pts"], dtype=float),
                closed=bool(m.get("closed")),
                char=m.get("char", ""),
                glyph=int(m.get("glyph", -1)),
                role=m.get("role", "line"),
                inner=bool(m.get("inner")),
                butt_start=bool(m.get("butt_start")),
                butt_end=bool(m.get("butt_end")),
                notes=[_("manuell bearbeitet", "edited by hand")] if m.get("edited") else [],
            )
            for m in manual
            if len(m.get("pts", [])) >= 2
        ]

    # ---------------------------------------------------------------- frame
    if P["frame"] and manual is None:
        pieces += _frame_pieces(plate_w, plate_h, P, w, r)

    # ---------------------------------------------------------------- dots handling
    if P["dot_mode"] == "omit":
        kept = []
        for p in pieces:
            if p.role == "dot":
                c = p.pts.mean(axis=0)
                omitted.append({"x": float(c[0]), "y": float(c[1]), "char": p.char})
            else:
                kept.append(p)
        pieces = kept
        if omitted:
            warnings.append(
                _(
                    f"{len(omitted)} Punkt(e) ohne LED geplant (z. B. aufgeklebt oder graviert).",
                    f"{len(omitted)} dot(s) planned without LED (e.g. glued on or engraved).",
                )
            )
    elif P["dot_mode"] == "separate":
        for p in pieces:
            if p.role == "dot":
                p.separate = True

    # ---------------------------------------------------------------- smoothing
    smooth_r = float(P["smooth_radius"]) if P.get("smooth_radius") else r
    smooth_dev = float(P["smooth_max_dev"])
    # single-line strips must stay inside the letter (strip edge within the stroke)
    corridor = None
    if P["mode"] == "single" and not hershey:
        corridor = shape.buffer(-(w / 2) + 0.05)
        if corridor.is_empty:
            corridor = None
    for pi, p in enumerate(pieces):
        report(0.5 + 0.35 * pi / max(1, len(pieces)), "Biegeradien optimieren")
        if p.role == "frame":
            continue  # the frame is built exactly
        if manual is not None:
            # hand-edited paths: only corners are rounded with the minimum bend radius
            p.pts = paths.smooth_path(p.pts, r, p.closed, step)
            continue
        if p.role == "dot" and not p.closed and len(p.pts) <= 2:
            continue
        p.pts = paths.smooth_path(p.pts, r, p.closed, step)
        if P["auto_smooth"] and smooth_r > 0 and len(p.pts) >= 5:
            original = p.pts.copy()
            if paths.find_violations(p.pts, smooth_r, p.closed, step):
                cand = paths.relax(p.pts, smooth_r, p.closed, step, smooth_dev, iterations=600, corridor=corridor)
                if corridor is not None:  # corridor bounds the strip; also respect the deviation limit
                    cand = _limit_deviation(original, cand, p.closed, smooth_dev)
                # keep the result only if it did not collapse the piece
                if paths.length(cand, p.closed) > 0.6 * paths.length(p.pts, p.closed):
                    p.pts = cand
            p.smoothed = _deviation_spots(original, p.pts, p.closed, 1.0, r)

    # ---------------------------------------------------------------- bridges for through cuts
    bridges, islands = [], 0
    if P["cut_mode"] == "through":
        report(0.86, "Haltestege planen")

        def make(src, pts, closed):
            return routing.Piece(
                pts=pts,
                closed=closed,
                char=src.char,
                glyph=src.glyph,
                role=src.role,
                inner=src.inner,
                separate=src.separate,
                notes=[*src.notes, _("an Steg geteilt", "split at a bridge")],
            )

        pieces, bridges, islands = cutout.split_for_bridges(
            pieces, plate_w, plate_h, w, float(P["cut_tolerance"]), float(P["bridge_width"]), make
        )

    # ---------------------------------------------------------------- routing
    report(0.88, "Routing hinter der Platte")
    feed = _feed_point(P["feed"], plate_w, plate_h)
    res = routing.plan(
        pieces,
        feed,
        connection=P["connection"],
        strip_width=w,
        hole_diameter=float(P["hole_diameter"]),
        plate_thickness=float(P["plate_thickness"]),
        pass_extra=float(P["pass_extra"]),
        roll_length=float(P["roll_length"]),
        bend_radius=r,
        glyph_word=glyph_word,
        glyph_line=glyph_line,
        joined_glyphs=set(joined),
        plate_size=(plate_w, plate_h),
    )
    ordered = res["pieces"]

    # ---------------------------------------------------------------- output
    pass_len = float(P["plate_thickness"]) + float(P["pass_extra"])
    cut = float(P["cut_unit"])
    out_pieces = []
    piece_group = {}
    for gi_, g in enumerate(res["groups"], start=1):
        for k in g["pieces"]:
            piece_group[k] = gi_
    all_viol = []
    for k, p in enumerate(ordered, start=1):
        L = paths.length(p.pts, p.closed)
        viol = _cluster(paths.find_violations(p.pts, r, p.closed, step), max(r, 3 * w)) if p.role != "dot" else []
        for v in viol:
            v["piece"] = k
        all_viol += viol
        notes = list(p.notes)
        if p.smoothed:
            notes.append(
                _(
                    f"automatisch geglättet, bis {max(s['dev'] for s in p.smoothed):.0f} mm Abweichung",
                    f"smoothed automatically, up to {max(s['dev'] for s in p.smoothed):.0f} mm deviation",
                )
            )
        if p.role == "dot":
            notes.append(_("Punkt – eigenes Stück, Übergang hinter der Platte", "Dot – separate piece, transition behind the plate"))
        if p.butt_start or p.butt_end:
            notes.append(_("Ende stößt an Verzweigung an anderes Stück", "End butts against another piece at a junction"))
        out_pieces.append(
            {
                "no": k,
                "char": p.char,
                "role": p.role,
                "closed": p.closed,
                "glyph": p.glyph,
                "butt_start": p.butt_start,
                "butt_end": p.butt_end,
                "pts": np.round(p.pts, 2).tolist(),
                "length": round(L, 1),
                "group": piece_group.get(k),
                "violations": viol,
                "notes": notes,
                "separate": p.separate,
                "inner": p.inner,
                "smoothed": p.smoothed,
            }
        )

    links = []
    for lk in res["links"]:
        d = lk.distance
        L = d + 2 * pass_len if lk.kind == "strip" else d + float(P["cable_reserve"])
        links.append(
            {
                "kind": lk.kind,
                "a": list(lk.a),
                "b": list(lk.b),
                "from": lk.from_piece,
                "to": lk.to_piece,
                "reason": lk.reason,
                "distance": round(d, 1),
                "length": round(L, 1),
                "path": np.round(lk.path, 2).tolist(),
            }
        )

    holes = []
    for i, h in enumerate(res["holes"], start=1):
        holes.append({"no": i, "x": round(h.x, 2), "y": round(h.y, 2), "uses": [list(u) for u in h.uses]})

    groups = []
    for i, g in enumerate(res["groups"], start=1):
        raw = g["front"] + g["back"] + float(P["piece_allowance"])
        rounded = math.ceil(raw / cut - 1e-9) * cut if cut > 0 else raw
        notes = []
        if cut > 0 and g["front"] < cut and len(g["pieces"]) == 1:
            notes.append(
                _(
                    f"Kürzer als Schnittraster – Rest ({rounded - raw:.0f} mm) durch die Bohrung nach hinten führen",
                    f"Shorter than the cut pitch – feed the rest ({rounded - raw:.0f} mm) through the hole to the back",
                )
            )
        groups.append(
            {
                "no": i,
                "pieces": g["pieces"],
                "front": round(g["front"], 1),
                "back": round(g["back"], 1),
                "raw": round(raw, 1),
                "cut": round(rounded, 1),
                "notes": notes,
            }
        )

    # glyphs that need hidden transitions behind the plate
    hidden = []
    by_glyph: dict[int, list[int]] = {}
    for k, p in enumerate(ordered, start=1):
        by_glyph.setdefault(p.glyph, []).append(k)
    for gi, nums in sorted(by_glyph.items()):
        roles = [ordered[n - 1].role for n in nums]
        inner = any(ordered[n - 1].inner for n in nums)
        if len(nums) <= 1 and not inner and "dot" not in roles:
            continue
        if "dot" in roles:
            ch = ordered[nums[0] - 1].char
            why = (
                _("Umlaut-Punkte getrennt vom Buchstaben", "Umlaut dots separate from the letter")
                if ch in UMLAUTS
                else _("Punkt getrennt vom Buchstaben", "Dot separate from the letter")
            )
        elif inner and len(nums) <= 2:
            why = _("Innenkontur (Loch im Buchstaben) separat", "Inner contour (counter) separate")
        elif inner:
            why = _("mehrere Teile inkl. Innenkontur", "several parts incl. inner contour")
        else:
            why = _("Buchstabe besteht aus mehreren Teilen", "Letter consists of several parts")
        hidden.append({"glyph": gi, "char": ordered[nums[0] - 1].char, "pieces": nums, "reason": why})

    letters = []
    for poly in _parts(shape):
        letters.append([np.round(rg, 2).tolist() for rg in _rings(poly)])
    strokes = []
    if hershey:
        for gl in glyph_lines:
            strokes += [np.round(np.asarray(ls.coords), 2).tolist() for ls in _parts(gl)]

    front_total = sum(p["length"] for p in out_pieces)
    back_strip = sum(link["length"] for link in links if link["kind"] == "strip")
    cable_total = sum(link["length"] for link in links if link["kind"] == "cable")
    min_r = min((v["radius"] for v in all_viol), default=None)

    if all_viol:
        warnings.append(
            _(
                f"{len(all_viol)} Stelle(n) enger als der Mindest-Biegeradius ({r:.0f} mm), engste {min_r:.0f} mm. "
                "Abhilfe: größere Schrift, Streifen mit kleinerem Biegeradius, automatisches Glätten oder manuell nachbearbeiten.",
                f"{len(all_viol)} spot(s) tighter than the minimum bend radius ({r:.0f} mm), tightest {min_r:.0f} mm. "
                "Remedy: larger lettering, a strip with a smaller bend radius, automatic smoothing or manual editing.",
            )
        )
    if markers:
        warnings.append(
            _(
                f"{len(markers)} Stelle(n), an denen der Strich zu schmal für zwei Streifen ist.",
                f"{len(markers)} spot(s) where the stroke is too narrow for two strips.",
            )
        )
    if any(g["raw"] > float(P["roll_length"]) for g in groups):
        warnings.append(_("Ein einzelnes Stück ist länger als eine Rolle.", "A single piece is longer than one roll."))
    if res["crossings"]:
        warnings.append(
            _(
                f"{len(res['crossings'])} Kreuzung(en) von Streifen hinter der Platte – dort liegt der Streifen doppelt.",
                f"{len(res['crossings'])} crossing(s) of strips behind the plate – the strip is doubled there.",
            )
        )
    if res["outside"] > 1.0:
        warnings.append(
            _(
                f"Ein Teil der Rückseiten-Bahnen ({res['outside']:.0f} mm) läuft über den Plattenrand – Rand vergrößern "
                "oder Biegeradius prüfen.",
                f"Part of the routes behind the plate ({res['outside']:.0f} mm) runs over the plate edge – enlarge the "
                "margin or check the bend radius.",
            )
        )
    if P["connection"] == "strip" and any(link["reason"] == "roll" for link in links):
        warnings.append(
            _(
                "Streifen auf mehrere Rollen aufgeteilt – an den markierten Stellen mit Kabel verbinden.",
                "Strip split over several rolls – connect with cable at the marked places.",
            )
        )

    # ---------------------------------------------------------------- cut-outs
    cut = None
    if P["cut_mode"] in ("groove", "through"):
        report(0.95, "Ausschnitte berechnen")
        chan = cutout.channels(out_pieces, w, float(P["cut_tolerance"]))
        if P["cut_mode"] == "through" and islands:
            loose = len(cutout._components(shapely.box(0, 0, plate_w, plate_h), out_pieces, w, float(P["cut_tolerance"]))) - 1
            warnings.append(
                _(
                    f"Durchbruch: {islands} Teil(e) wären lose – {len(bridges)} Steg(e) halten sie. "
                    "An jedem Steg ist der Streifen unterbrochen und läuft hinter dem Brett."
                    + (f" Achtung: {loose} Teil(e) konnten nicht gesichert werden." if loose > 0 else ""),
                    f"Through cut: {islands} part(s) would fall out – {len(bridges)} bridge(s) hold them. "
                    "At every bridge the strip is interrupted and runs behind the board."
                    + (f" Warning: {loose} part(s) could not be secured." if loose > 0 else ""),
                )
            )
        depth = float(P["cut_depth"]) if P.get("cut_depth") else w
        cut = {
            "mode": P["cut_mode"],
            "channels": cutout.to_rings(chan),
            "bridges": cutout.to_rings(unary_union(bridges)) if bridges else [],
            "islands": islands,
            "width": round(w + float(P["cut_tolerance"]), 2),
            "depth": round(depth, 1),
            "area": round(chan.area, 0),
        }

    report(1.0, "fertig")
    return {
        "ok": True,
        "manual": manual is not None,
        "font_weight": weight,
        "params": P,
        "plate": {"w": round(plate_w, 1), "h": round(plate_h, 1), "corner": float(P["plate_corner"])},
        "bounds": {"x0": round(m, 1), "y0": round(m, 1), "x1": round(plate_w - m, 1), "y1": round(plate_h - m, 1)},
        "feed": {"x": feed[0], "y": feed[1]},
        "letters": letters,
        "strokes": strokes,
        "pieces": out_pieces,
        "links": links,
        "holes": holes,
        "groups": groups,
        "markers": markers,
        "omitted": omitted,
        "cut": cut,
        "back_crossings": [{"x": round(x, 1), "y": round(y, 1)} for x, y in res["crossings"]],
        "hidden": hidden,
        "joined": [[lay.glyphs[i].char for i in j] for j in joined],
        "summary": {
            "front": round(front_total, 1),
            "back_strip": round(back_strip, 1),
            "strip_total": round(front_total + back_strip, 1),
            "strip_cut_total": round(sum(g["cut"] for g in groups), 1),
            "cable": round(cable_total, 1),
            "pieces": len(out_pieces),
            "groups": len(groups),
            "holes": len(holes),
            "transitions": len(links) - 1,
            "violations": len(all_viol),
            "smoothed": sum(len(p.smoothed) for p in ordered),
            "min_radius": round(min_r, 1) if min_r is not None else None,
        },
        "warnings": warnings,
    }


def _cluster(spots: list[dict], dist: float) -> list[dict]:
    """Merge nearby spots, keeping the tightest radius of every cluster."""
    out: list[dict] = []
    for s in sorted(spots, key=lambda s: s["radius"]):
        if all(math.dist((s["x"], s["y"]), (o["x"], o["y"])) > dist for o in out):
            out.append(s)
    return out


def _limit_deviation(original, q, closed, max_dev):
    ref = LineString(np.vstack([original, original[:1]]) if closed else original)
    near = shapely.get_coordinates(shapely.shortest_line(shapely.points(q), ref))[1::2]
    d = q - near
    dd = np.linalg.norm(d, axis=1)
    over = dd > max_dev
    q = q.copy()
    q[over] = near[over] + d[over] / dd[over, None] * max_dev
    return q


def _deviation_spots(original, smoothed, closed, limit, dist):
    """Spots where smoothing moved the strip further than `limit` from the original path."""
    if len(original) < 2 or len(smoothed) < 2:
        return []
    ref = LineString(np.vstack([original, original[:1]]) if closed else original)
    dev = shapely.distance(ref, shapely.points(smoothed))
    idx = np.argsort(-dev)
    out = []
    for i in idx:
        if dev[i] <= limit:
            break
        x, y = smoothed[i]
        if all(math.dist((x, y), (o["x"], o["y"])) > dist for o in out):
            out.append({"x": round(float(x), 2), "y": round(float(y), 2), "dev": round(float(dev[i]), 1)})
    return out


def _hershey_umlaut_bars(pieces, lay, w):
    out, dots = [], {}
    for p in pieces:
        if p.role == "dot" and lay.glyphs[p.glyph].char in UMLAUTS:
            dots.setdefault(p.glyph, []).append(p)
        else:
            out.append(p)
    for gi, ds in dots.items():
        pts = np.vstack([d.pts for d in ds])
        x0, x1 = pts[:, 0].min(), pts[:, 0].max()
        y = pts[:, 1].mean()
        out.append(
            routing.Piece(
                np.array([[x0, y], [x1, y]]),
                False,
                ds[0].char,
                gi,
                "dot",
                notes=[_("Umlaut-Punkte als waagerechter Strich", "Umlaut dots as a horizontal bar")],
            )
        )
    return out


def _frame_pieces(W: float, H: float, P: dict, w: float, r: float) -> list:
    """Rectangular frame inside the plate edge."""
    inset = float(P["frame_inset"]) if P.get("frame_inset") else float(P["margin"]) / 2
    inset = max(inset, w)
    x0, y0, x1, y1 = inset, inset, W - inset, H - inset
    if x1 - x0 < 4 * w or y1 - y0 < 4 * w:
        return []
    if P["frame_corners"] == "butt":
        g = w / 2  # pieces butt at the corners: vertical pieces run through, horizontal ones stop
        segs = [
            [(x0, y0), (x0, y1)],
            [(x0 + g + w / 2, y1), (x1 - g - w / 2, y1)],
            [(x1, y1), (x1, y0)],
            [(x1 - g - w / 2, y0), (x0 + g + w / 2, y0)],
        ]
        return [
            routing.Piece(np.asarray(sg, float), False, _("Rahmen", "Frame"), -1, "frame", butt_start=i % 2 == 1, butt_end=i % 2 == 1)
            for i, sg in enumerate(segs)
        ]
    rect = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float)
    ring = paths.resample(paths.fillet(rect, max(r, float(P["plate_corner"]) - inset), True), 1.5, True)
    return [routing.Piece(ring, True, _("Rahmen", "Frame"), -1, "frame")]


def _feed_point(where: str, W: float, H: float, inset: float = 15.0):
    pos = {
        "bottom-left": (inset, inset),
        "bottom-center": (W / 2, inset),
        "bottom-right": (W - inset, inset),
        "left": (inset, H / 2),
        "right": (W - inset, H / 2),
        "top-left": (inset, H - inset),
        "top-center": (W / 2, H - inset),
        "top-right": (W - inset, H - inset),
    }
    x, y = pos.get(where, pos["bottom-left"])
    return (round(x, 2), round(y, 2))


def make_pdf(plan: dict, paper: str = "A4", parts=("overview", "front", "back"), lang: str | None = None) -> bytes:
    from .pdf import render_plan

    set_lang(lang or plan.get("params", {}).get("lang"))
    return render_plan(plan, paper=paper, parts=parts)
