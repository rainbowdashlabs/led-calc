"""Cut-outs for recessing the strip into a board (e.g. wood) instead of mounting it on top.

- "groove":  a channel is milled to a given depth; nothing can fall out.
- "through": the channel is cut through the board (laser, jigsaw, CNC). Material that
  would be completely enclosed by channels (counters of "o", "a", the inside of a "D",
  the inside of a frame, ...) would fall out and needs bridges.

A bridge is material that stays, so no strip can lie there: the strip has to pass
behind the board. Bridges are therefore created by *splitting* a strip piece - the gap
becomes the bridge and the strip changes to the back side there, like at any other
transition. Cuts are placed preferably at corners (where the bowl of a "D" meets its
stem) and, where possible, two per island so that it is held on two sides.
"""

from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LineString, box
from shapely.ops import substring, unary_union


def _line(pts, closed):
    pts = np.asarray(pts, dtype=float)
    return LineString(np.vstack([pts, pts[:1]]) if closed else pts)


def channels(pieces, strip_width: float, tolerance: float):
    """Union of all strip paths widened to the channel width (pieces as dicts or Piece)."""
    half = (strip_width + tolerance) / 2
    shapes = []
    for p in pieces:
        pts, closed = (p["pts"], p["closed"]) if isinstance(p, dict) else (p.pts, p.closed)
        if len(pts) < 2:
            continue
        shapes.append(_line(pts, closed).buffer(half, cap_style="round" if closed else "flat"))
    return unary_union(shapes) if shapes else shapely.Polygon()


def _parts(g):
    return [x for x in shapely.get_parts(g) if not x.is_empty and x.area > 1.0]


def _components(board, pieces, strip_width, tolerance):
    return _parts(board.difference(channels(pieces, strip_width, tolerance)))


def _corner_score(line: LineString, s: float, window: float) -> float:
    """Turning angle of the path around arc length `s` (corners score high)."""
    L = line.length
    a = line.interpolate(max(0.0, s - window))
    b = line.interpolate(s)
    c = line.interpolate(min(L, s + window))
    v1 = np.array([b.x - a.x, b.y - a.y])
    v2 = np.array([c.x - b.x, c.y - b.y])
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    return math.acos(float(np.clip(v1 @ v2 / (n1 * n2), -1, 1)))


def _candidates(pieces, island, half, gap, bridge_width):
    """Positions on strip pieces whose channel borders the island, best (corners) first."""
    cands = []
    near = island.buffer(half + 1.0)
    shapely.prepare(near)
    for i, p in enumerate(pieces):
        line = _line(p.pts, p.closed)
        L = line.length
        if 2 * gap + 4 > L:
            continue
        lo, hi = (0.0, L) if p.closed else (gap / 2 + 2, L - gap / 2 - 2)
        for s in np.arange(lo, hi, 2.0):
            pt = line.interpolate(s)
            if not near.contains(pt):
                continue
            score = _corner_score(line, s, max(gap, 10.0))
            cands.append((score, i, float(s), (pt.x, pt.y)))
    cands.sort(key=lambda c: -c[0])
    return cands


def split_for_bridges(pieces, plate_w, plate_h, strip_width, tolerance, bridge_width, make, per_island: int = 2):
    """Split strip pieces until no part of the board would fall out.

    Returns (pieces, bridges, islands_before) - bridges as polygons of the material that
    stays where a strip piece was interrupted.
    """
    board = box(0, 0, plate_w, plate_h)
    half = (strip_width + tolerance) / 2
    gap = bridge_width + strip_width  # bridge plus room for the strip to bend behind the board
    comps = _components(board, pieces, strip_width, tolerance)
    islands_before = max(0, len(comps) - 1)
    bridges = []
    for _ in range(4 * islands_before + 4):
        comps = sorted(_components(board, pieces, strip_width, tolerance), key=lambda c: -c.area)
        if len(comps) <= 1:
            break
        progress = False
        for island in comps[1:]:
            cands = _candidates(pieces, island, half, gap, bridge_width)
            for _k, (_score, pi, s, xy) in enumerate(cands[:80]):
                # second cut far away from the first one, preferably also at a corner
                second = None
                if per_island > 1:
                    for _score2, pj, s2, xy2 in cands:
                        far_enough = math.dist(xy, xy2) > max(4 * gap, 0.25 * math.sqrt(island.area))
                        if far_enough and (pj != pi or abs(s2 - s) > 2 * gap):
                            second = (pj, s2)
                            break
                for cuts in ([(pi, s), second] if second else [(pi, s)], [(pi, s)]):
                    trial, gaps = _apply_cuts(pieces, cuts, gap, make)
                    if len(_components(board, trial, strip_width, tolerance)) < len(comps):
                        pieces = trial
                        bridges += [g.buffer(half, cap_style="flat").intersection(board) for g in gaps]
                        progress = True
                        break
                if progress:
                    break
            if progress:
                break
        if not progress:
            break
    return pieces, bridges, islands_before


def _apply_cuts(pieces, cuts, gap, make):
    """Apply cuts [(piece_index, s)] - all cuts of one piece at once, on its original path.

    Returns (new_pieces, gap_lines) where gap_lines are the removed path sections.
    """
    by_piece: dict[int, list[float]] = {}
    for pi, s in cuts:
        by_piece.setdefault(pi, []).append(s)
    out, gaps = [], []
    for i, p in enumerate(pieces):
        if i not in by_piece:
            out.append(p)
            continue
        line = _line(p.pts, p.closed)
        L = line.length
        ss = sorted(by_piece[i])
        for s in ss:
            gaps.append(_section(line, s - gap / 2, s + gap / 2, p.closed))
        if p.closed:
            # keep the sections between consecutive gaps (cyclically)
            for k, s in enumerate(ss):
                a = s + gap / 2
                b = ss[(k + 1) % len(ss)] - gap / 2 + (L if k == len(ss) - 1 else 0)
                if b - a > 1.0:
                    out.append(make(p, np.asarray(_section(line, a, b, True).coords), False))
        else:
            bounds = [0.0] + [v for s in ss for v in (s - gap / 2, s + gap / 2)] + [L]
            for a, b in zip(bounds[0::2], bounds[1::2], strict=False):
                if b - a > 1.0:
                    out.append(make(p, np.asarray(substring(line, max(0.0, a), min(L, b)).coords), False))
    return out, gaps


def _section(line: LineString, a: float, b: float, closed: bool) -> LineString:
    """Part of `line` between arc lengths a..b (wrapping around for closed rings)."""
    L = line.length
    if not closed or (a >= 0 and b <= L):
        return substring(line, max(0.0, a), min(L, b))
    a, b = a % L, b % L
    if a < b:
        return substring(line, a, b)
    first = np.asarray(substring(line, a, L).coords)
    second = np.asarray(substring(line, 0, b).coords)
    return LineString(np.vstack([first, second[1:]]))


def to_rings(geom):
    out = []
    for poly in _parts(geom):
        if poly.geom_type != "Polygon":
            continue
        out.append(
            [np.round(np.asarray(poly.exterior.coords), 2).tolist()] + [np.round(np.asarray(r.coords), 2).tolist() for r in poly.interiors]
        )
    return out
