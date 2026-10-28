"""Ordering of strip pieces, plate holes and the connections behind the plate.

Every change from one strip piece to the next happens behind the plate so that it is
invisible from the front:

- connection "strip": the same strip dives through a hole to the back, runs behind the
  plate and comes back to the front through the next hole.
- connection "cable": every piece is fed separately; wires run behind the plate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import shapely
from shapely.geometry import LineString, Point, box
from shapely.ops import substring

from . import paths
from .dubins import dubins, dubins_length


@dataclass
class Piece:
    pts: np.ndarray
    closed: bool
    char: str = ""
    glyph: int = -1  # index of the glyph placement the piece belongs to
    role: str = "line"  # "contour" | "line" | "dot" | "frame"
    butt_start: bool = False  # end touches another piece at a junction
    butt_end: bool = False
    notes: list = field(default_factory=list)
    separate: bool = False  # always fed by its own cable (e.g. dots in "separate" mode)
    inner: bool = False  # inner contour (counter of o, a, e, ...)
    smoothed: list = field(default_factory=list)  # spots moved further than max_dev by auto-smoothing


@dataclass
class Hole:
    x: float
    y: float
    uses: list = field(default_factory=list)  # [(piece_no, "in" | "out")]


@dataclass
class Link:
    """Connection behind the plate between two consecutive pieces (or from the feed point)."""

    kind: str  # "strip" | "cable"
    a: tuple  # (x, y) start, front coordinates
    b: tuple
    from_piece: int  # 0 = feed point
    to_piece: int
    reason: str  # "feed" | "same_glyph" | "next_glyph" | "next_word" | "next_line" | "roll"
    path: np.ndarray | None = None  # route behind the plate (respects the bend radius for strips)
    distance: float = 0.0  # length of `path`


def _rotate_ring(pts: np.ndarray, near) -> np.ndarray:
    """Rotate a closed ring so that it starts at the point closest to `near`."""
    ring = LineString(np.vstack([pts, pts[:1]]))
    d = ring.project(Point(near))
    L = ring.length
    if d <= 1e-6 or d >= L - 1e-6:
        return pts
    a = np.asarray(substring(ring, d, L).coords)
    b = np.asarray(substring(ring, 0, d).coords)
    return paths.dedupe(np.vstack([a, b[1:]]), True)


def order_pieces(
    pieces: list[Piece], feed, connection: str, bend_radius: float = 0.0, inside=None, hole_diameter: float = 10.0
) -> list[Piece]:
    """Greedy nearest-neighbour ordering that also picks the direction of every piece.

    With a continuous strip the cost of a hop is the length of the route behind the plate,
    which has to respect the bend radius (it leaves in the direction of travel and must
    arrive in the direction of the next piece). Closed rings may run either way round.
    """
    remaining = list(range(len(pieces)))
    cur = np.asarray(feed, dtype=float)
    cur_heading = None  # None: cable / feed point, direction does not matter
    out: list[Piece] = []
    placed: list[LineString] = []

    def cost(pos, heading):
        if cur_heading is None or bend_radius <= 0:
            return float(np.linalg.norm(pos - cur))
        # behind the plate the strip keeps its direction of travel
        return dubins_length(cur, cur_heading, pos, heading, bend_radius)

    def route_penalty(pos, heading):
        """Penalty for the real route: leaving the plate or crossing strips already laid."""
        if cur_heading is None:
            return 0.0, None
        _, pts = dubins(tuple(cur), cur_heading, tuple(pos), heading, bend_radius)
        line = LineString(pts)
        pen = 0.0
        if inside is not None:
            pen += 20.0 * line.difference(inside).length
        pen += 400.0 * _crossings(line, placed, hole_diameter)
        return pen, line

    while remaining:
        best = None
        all_cand = []
        for i in remaining:
            p = pieces[i]
            if p.closed:
                ring = LineString(np.vstack([p.pts, p.pts[:1]]))
                entry = np.asarray(ring.interpolate(ring.project(Point(cur))).coords[0])
                rot = _rotate_ring(p.pts, entry)
                cand = [(cost(rot[0], _heading(paths_dir(rot))), i, "ring", rot)]
                rev = np.vstack([rot[:1], rot[1:][::-1]])
                cand.append((cost(rev[0], _heading(paths_dir(rev))), i, "ring", rev))
            else:
                cand = [
                    (cost(p.pts[0], _heading(paths_dir(p.pts))), i, "fwd", None),
                    (cost(p.pts[-1], _heading(paths_dir(p.pts[::-1]))), i, "rev", None),
                ]
            for c in cand:
                if best is None or c[0] < best[0] - 1e-9:
                    best = c
            all_cand.extend(cand)
        # the best few by length are checked with their real route behind the plate
        if cur_heading is not None and len(all_cand) > 1:
            scored = []
            for c in sorted(all_cand, key=lambda c: c[0])[:6]:
                p_ = pieces[c[1]]
                pts_ = c[3] if c[2] == "ring" else (p_.pts if c[2] == "fwd" else p_.pts[::-1])
                pen, line = route_penalty(pts_[0], _heading(paths_dir(pts_)))
                scored.append((c[0] + pen, c, line))
            _, best, line = min(scored, key=lambda x: x[0])
            if line is not None:
                placed.append(line)
        _, i, how, pts = best
        p = pieces[i]
        if how == "ring":
            p.pts = pts
        elif how == "rev":
            p.pts = p.pts[::-1].copy()
            p.butt_start, p.butt_end = p.butt_end, p.butt_start
        out.append(p)
        remaining.remove(i)
        cable_fed = connection == "cable" or p.separate
        if cable_fed:
            cur, cur_heading = p.pts[0], None
        elif p.closed:
            cur, cur_heading = p.pts[0], _heading(p.pts[0] - p.pts[-1])
        else:
            cur, cur_heading = p.pts[-1], _heading(-paths_dir(p.pts[::-1]))
    return out


def _reason(prev: Piece, nxt: Piece, glyph_word: dict, glyph_line: dict) -> str:
    if prev.glyph == nxt.glyph:
        return "same_glyph"
    if glyph_line.get(prev.glyph) != glyph_line.get(nxt.glyph):
        return "next_line"
    if glyph_word.get(prev.glyph) != glyph_word.get(nxt.glyph):
        return "next_word"
    return "next_glyph"


def _heading(v) -> float:
    return math.atan2(v[1], v[0])


def _end_heading(p: Piece) -> float:
    """Direction of travel where the strip leaves a piece."""
    pts = p.pts
    if p.closed:
        return _heading(pts[0] - pts[-1])
    return _heading(paths_dir(pts[::-1]) * -1)


def _start_heading(p: Piece) -> float:
    return _heading(paths_dir(p.pts))


def paths_dir(pts: np.ndarray, dist: float = 5.0) -> np.ndarray:
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    j = int(np.searchsorted(cum, min(cum[-1], dist)))
    j = min(max(j, 1), len(pts) - 1)
    d = pts[j] - pts[0]
    n = np.linalg.norm(d)
    return d / n if n > 1e-12 else np.array([1.0, 0.0])


def plan(
    pieces: list[Piece],
    feed,
    *,
    connection: str,
    strip_width: float,
    hole_diameter: float,
    plate_thickness: float,
    pass_extra: float,
    roll_length: float,
    bend_radius: float,
    glyph_word: dict,
    glyph_line: dict,
    joined_glyphs: set,
    plate_size=None,
) -> dict:
    """Order pieces, place holes and create links. Mutates piece geometry (shortening)."""
    inside = None
    if plate_size is not None:
        inset = hole_diameter / 2 + 2
        inside = box(inset, inset, plate_size[0] - inset, plate_size[1] - inset)
    ordered = order_pieces(pieces, feed, connection, bend_radius, inside, hole_diameter)
    n = len(ordered)
    pass_len = plate_thickness + pass_extra

    # 1. link kinds
    kinds = []
    for k in range(n):
        p = ordered[k]
        if k == 0 or connection == "cable" or p.separate or ordered[k - 1].separate:
            kinds.append("cable")
        else:
            kinds.append("strip")

    # 2. holes at piece ends: "in" always, "out" when the next link is a strip
    has_out = [k + 1 < n and kinds[k + 1] == "strip" for k in range(n)]

    # 3. shorten ends that butt against another piece; leave room for a hole there
    for k, p in enumerate(ordered):
        if p.closed:
            continue
        s = (strip_width / 2 + hole_diameter / 2) if p.butt_start else 0.0
        e = (strip_width / 2 + (hole_diameter / 2 if has_out[k] else 0.0)) if p.butt_end else 0.0
        if s or e:
            p.pts = _shorten(p.pts, s, e)

    # 4. links (front coordinates) and roll-length splitting
    links: list[Link] = []
    for k, p in enumerate(ordered):
        if k == 0:
            a = tuple(map(float, feed))
            reason = "feed"
        else:
            prev = ordered[k - 1]
            # a strip leaves where the previous piece ends; wires are daisy-chained from feed hole to feed hole
            leaves_at_end = kinds[k] == "strip" and not prev.closed
            a = tuple(map(float, prev.pts[-1] if leaves_at_end else prev.pts[0]))
            reason = _reason(prev, p, glyph_word, glyph_line)
        links.append(Link(kinds[k], a, tuple(map(float, p.pts[0])), k, k + 1, reason))

    placed: list[LineString] = []  # strip routes already laid behind the plate

    def route(lk: Link, k: int) -> None:
        """Strips behind the plate obey the bend radius; cables run straight.

        The strip leaves a hole in its direction of travel and reaches the next hole in
        the direction of the next piece (no reversal). Plate edge and crossings are
        already taken into account when the order is chosen.
        """
        if lk.kind != "strip":
            lk.path = np.asarray([lk.a, lk.b], dtype=float)
            lk.distance = _dist(lk.a, lk.b)
            return
        prev = ordered[k - 1]
        L, pts = dubins(lk.a, _end_heading(prev), lk.b, _start_heading(ordered[k]), bend_radius)
        lk.path, lk.distance = pts, float(L)
        placed.append(LineString(pts))

    for k, lk in enumerate(links):
        route(lk, k)

    def front_len(p):
        return paths.length(p.pts, p.closed)

    # split into cut groups that fit on one roll; a split turns a strip link into a cable
    group_len = 0.0
    for k, p in enumerate(ordered):
        lk = links[k]
        add = front_len(p)
        if lk.kind == "strip":
            add += lk.distance + 2 * pass_len
        if lk.kind == "strip" and group_len + add > roll_length:
            lk.kind = "cable"
            lk.reason = "roll"
            lk.a = tuple(map(float, ordered[k - 1].pts[0]))
            placed[:] = [pl for pl in placed if pl is not None]
            route(lk, k)
            add = front_len(p)
        group_len = add if lk.kind == "cable" else group_len + add
    has_out = [k + 1 < n and links[k + 1].kind == "strip" for k in range(n)]

    # 5. holes (merge holes closer than one diameter)
    holes: list[Hole] = []

    def add_hole(xy, use):
        for h in holes:
            if math.dist((h.x, h.y), xy) < hole_diameter * 0.9:
                h.uses.append(use)
                return
        holes.append(Hole(float(xy[0]), float(xy[1]), [use]))

    for k, p in enumerate(ordered):
        add_hole(p.pts[0], (k + 1, "in"))
        if has_out[k]:
            add_hole(p.pts[0] if p.closed else p.pts[-1], (k + 1, "out"))

    # 6. cut groups
    groups = []
    for k, p in enumerate(ordered):
        lk = links[k]
        if lk.kind == "cable" or not groups:
            groups.append({"pieces": [], "front": 0.0, "back": 0.0})
        g = groups[-1]
        g["pieces"].append(k + 1)
        g["front"] += front_len(p)
        if lk.kind == "strip":
            g["back"] += lk.distance + 2 * pass_len

    # remaining crossings / routes outside the plate
    strip_lines = [(i, LineString(link.path)) for i, link in enumerate(links) if link.kind == "strip" and link.path is not None]
    crossings = []
    for x in range(len(strip_lines)):
        for y in range(x + 1, len(strip_lines)):
            inter = strip_lines[x][1].intersection(strip_lines[y][1])
            for pt in shapely.get_parts(inter):
                if pt.geom_type == "Point" and not _near_hole(pt, links, hole_diameter):
                    crossings.append((pt.x, pt.y))
    outside = 0.0
    if inside is not None:
        outside = sum(line.difference(inside).length for _, line in strip_lines)

    return {
        "pieces": ordered,
        "links": links,
        "holes": holes,
        "groups": groups,
        "joined_glyphs": joined_glyphs,
        "crossings": crossings,
        "outside": outside,
    }


def _crossings(line: LineString, placed: list, hole_diameter: float) -> int:
    n = 0
    for other in placed:
        inter = line.intersection(other)
        if inter.is_empty:
            continue
        for pt in shapely.get_parts(inter):
            if pt.geom_type != "Point":
                n += 1
                continue
            # touching at a shared hole is not a crossing
            if min(Point(line.coords[0]).distance(pt), Point(line.coords[-1]).distance(pt)) > hole_diameter:
                n += 1
    return n


def _near_hole(pt, links, hole_diameter) -> bool:
    return any(min(math.dist((pt.x, pt.y), link.a), math.dist((pt.x, pt.y), link.b)) <= hole_diameter for link in links)


def _dist(a, b) -> float:
    return float(math.dist(a, b))


def _shorten(p: np.ndarray, s: float, e: float) -> np.ndarray:
    L = paths.length(p, False)
    if s + e >= L * 0.8:
        return p
    return np.asarray(substring(LineString(p), s, L - e).coords)
