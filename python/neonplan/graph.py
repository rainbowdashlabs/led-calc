"""Line graphs: centreline (skeleton) of a shape and decomposition into strip pieces.

An LED strip cannot branch. A line network (e.g. the letter "E") is therefore split
into as few, as straight as possible, continuous pieces. Pieces that end at a junction
butt against another piece there.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

import numpy as np
import shapely
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import substring, unary_union

from . import paths


@dataclass
class Graph:
    nodes: list = field(default_factory=list)  # [np.array([x, y])]
    edges: dict = field(default_factory=dict)  # id -> [u, v, pts(np.ndarray)]
    _next: int = 0

    def add_node(self, xy) -> int:
        self.nodes.append(np.asarray(xy, dtype=float))
        return len(self.nodes) - 1

    def add_edge(self, u: int, v: int, pts) -> int:
        eid = self._next
        self._next += 1
        self.edges[eid] = [u, v, np.asarray(pts, dtype=float)]
        return eid

    def incident(self) -> dict:
        inc: dict[int, list[int]] = {}
        for eid, (u, v, _) in self.edges.items():
            inc.setdefault(u, []).append(eid)
            inc.setdefault(v, []).append(eid)  # a loop (u == v) counts twice
        return inc

    def degree(self) -> dict:
        return {n: len(es) for n, es in self.incident().items()}

    def edge_length(self, eid) -> float:
        return paths.length(self.edges[eid][2], False)

    def contract(self) -> None:
        """Merge the two edges at every node of degree 2."""
        changed = True
        while changed:
            changed = False
            inc = self.incident()
            for n, es in inc.items():
                if len(es) != 2 or es[0] == es[1]:
                    continue
                e1, e2 = es
                u1, v1, p1 = self.edges[e1]
                u2, v2, p2 = self.edges[e2]
                # orient p1 to end at n and p2 to start at n
                if u1 == n and v1 != n:
                    p1, u1, v1 = p1[::-1], v1, u1
                if v2 == n and u2 != n:
                    p2, u2, v2 = p2[::-1], v2, u2
                merged = np.vstack([p1, p2[1:]])
                del self.edges[e1]
                del self.edges[e2]
                self.add_edge(u1, v2, merged)
                changed = True
                break


def graph_from_polylines(lines, snap: float) -> Graph:
    """Build a graph from polylines; endpoints closer than `snap` are merged."""
    g = Graph()
    index: dict[tuple[int, int], int] = {}

    def node_for(xy):
        key = (round(xy[0] / snap), round(xy[1] / snap))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                k = (key[0] + dx, key[1] + dy)
                if k in index and np.linalg.norm(g.nodes[index[k]] - xy) < snap:
                    return index[k]
        nid = g.add_node(xy)
        index[key] = nid
        return nid

    for pts in lines:
        pts = np.asarray(pts, dtype=float)
        if len(pts) < 2 or paths.length(pts, False) < 1e-6:
            continue
        u = node_for(pts[0])
        v = node_for(pts[-1])
        pts = pts.copy()
        pts[0], pts[-1] = g.nodes[u], g.nodes[v]
        g.add_edge(u, v, pts)
    g.contract()
    return g


def graph_from_linework(geom, snap: float = 0.05) -> Graph:
    """Graph from linework (e.g. Hershey strokes); crossings become nodes."""
    noded = unary_union(geom)
    lines = [np.asarray(ls.coords) for ls in shapely.get_parts(shapely.line_merge(noded)) if ls.length > 0]
    return graph_from_polylines(lines, snap)


# --------------------------------------------------------------------------- Skeleton


def medial_axis(poly, sample_step: float) -> Graph:
    """Approximate the medial axis of a shape via a Voronoi diagram of boundary samples."""
    boundary = shapely.segmentize(poly.boundary, sample_step)
    pts = shapely.get_coordinates(boundary)
    if len(pts) < 4:
        return Graph()
    pts = np.unique(np.round(pts, 6), axis=0)
    edges = shapely.voronoi_polygons(MultiPoint(pts), only_edges=True)
    segs = shapely.get_parts(edges)
    shapely.prepare(poly)
    inside = shapely.contains(poly, segs)
    segs = segs[inside]
    if len(segs) == 0:
        return Graph()
    coords = [np.asarray(s.coords) for s in segs]
    g = graph_from_polylines(coords, snap=sample_step * 1e-3)
    collapse_short(g, sample_step * 3)
    return g


def collapse_short(g: Graph, tol: float) -> None:
    """Merge nodes joined by edges shorter than `tol` (clusters at round stroke ends).

    Removes the resulting self-loops and keeps only the longest of parallel edges.
    """
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    # merge along short edges, but only while a cluster stays small: chains of short
    # edges along a straight stroke (e.g. the stem of "D") must not collapse into a point
    members: dict[int, list[int]] = {}
    short = sorted((paths.length(p, False), u, v) for (u, v, p) in g.edges.values())
    for L, u, v in short:
        if tol <= L:
            break
        ru, rv = find(u), find(v)
        if ru == rv:
            continue
        mu, mv = members.get(ru, [ru]), members.get(rv, [rv])
        pts = np.array([g.nodes[m] for m in mu + mv])
        if np.ptp(pts, axis=0).max() > tol:
            continue
        parent[ru] = rv
        members[rv] = mu + mv
        members.pop(ru, None)
    groups: dict[int, list[int]] = {}
    for n in list(parent):
        groups.setdefault(find(n), []).append(n)
    for root, members in groups.items():  # node position: centroid of the cluster
        g.nodes[root] = np.mean([g.nodes[m] for m in members], axis=0)
    best: dict[tuple, int] = {}
    for eid in list(g.edges):
        u, v, p = g.edges[eid]
        ru, rv = find(u), find(v)
        if ru == rv and paths.length(p, False) < 4 * tol:
            del g.edges[eid]
            continue
        p = p.copy()
        p[0], p[-1] = g.nodes[ru], g.nodes[rv]
        g.edges[eid] = [ru, rv, p]
        key = (min(ru, rv), max(ru, rv))
        if paths.length(p, False) >= 4 * tol:
            continue  # long parallel edges are real (stem and bowl of "D")
        if ru != rv and key in best:
            other = best[key]
            if paths.length(p, False) > paths.length(g.edges[other][2], False):
                del g.edges[other]
                best[key] = eid
            else:
                del g.edges[eid]
        elif ru != rv:
            best[key] = eid
    g.contract()


def prune(g: Graph, poly, factor: float = 0.5, min_keep: float = 0.0) -> None:
    """Remove short side branches (they originate at corners of the shape).

    A branch is judged by how far the shape actually reaches beyond the junction:
    ``length + R_leaf - R_junction`` (R = distance to the boundary). Corner spurs score
    well below half the junction radius, real arms (crossbar of "f", arm of "r") far above.
    """
    boundary = poly.boundary
    for _ in range(200):
        inc = g.incident()
        deg = {n: len(es) for n, es in inc.items()}
        cands = []
        for eid, (u, v, pts) in g.edges.items():
            if u == v:
                continue
            if deg[u] == 1 and deg[v] >= 2:
                leaf, junc = u, v
            elif deg[v] == 1 and deg[u] >= 2:
                leaf, junc = v, u
            else:
                continue
            L = paths.length(pts, False)
            R = boundary.distance(Point(g.nodes[junc]))
            R_leaf = boundary.distance(Point(g.nodes[leaf]))
            reach = L + R_leaf - R
            if reach < factor * R + min_keep:
                cands.append((reach, eid, junc))
        if not cands:
            break
        cands.sort()
        removed = False
        for _reach, eid, junc in cands:
            if eid not in g.edges:
                continue
            if deg[junc] >= 2:
                u, v, _ = g.edges.pop(eid)
                deg[u] -= 1
                deg[v] -= 1
                removed = True
        if not removed:
            break
        g.contract()
    # isolated nodes do not matter; drop tiny noise loops
    for eid in [e for e, (u, v, p) in g.edges.items() if u == v and paths.length(p, False) < 1e-3]:
        del g.edges[eid]


def _fit_curvature(pts: np.ndarray) -> tuple[float, np.ndarray] | None:
    """Least-squares circle fit (Kasa); returns (radius, centre) or None."""
    if len(pts) < 4:
        return None
    x, y = pts[:, 0], pts[:, 1]
    A = np.column_stack([x, y, np.ones_like(x)])
    b = -(x * x + y * y)
    try:
        (D, E, F), *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None
    c = np.array([-D / 2, -E / 2])
    r2 = c @ c - F
    if not np.isfinite(r2) or r2 <= 0:
        return None
    return float(np.sqrt(r2)), c


def _arc_length_index(p: np.ndarray, dist: float) -> int:
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
    j = int(np.searchsorted(cum, min(cum[-1], dist)))
    return min(max(j, 1), len(p) - 1)


def extend_leaves(g: Graph, poly, end_gap: float, stems=None) -> None:
    """Rebuild free ends so that they follow the stroke up to `end_gap` before its end.

    Near a stroke end the medial axis is unreliable (left-overs of corner branches make
    it hook sideways). The last stretch (about one stroke radius) is cut off and replaced
    by a continuation with the curvature of the stroke just before it: straight strokes
    end straight, curved terminals (f, s, e, C) keep curving the way the letter does.
    """
    deg = g.degree()
    boundary = poly.boundary
    inner = poly.buffer(-end_gap)
    shapely.prepare(inner)
    for _eid, edge in g.edges.items():
        for at_start in (True, False):
            node = edge[0] if at_start else edge[1]
            if deg.get(node, 0) != 1 or len(edge[2]) < 2:
                continue
            p = edge[2] if at_start else edge[2][::-1]
            L = paths.length(p, False)
            R = boundary.distance(Point(p[0]))
            cut = min(R * 0.9, L * 0.35)
            if cut > 0.5:
                p = np.asarray(substring(LineString(p), cut, L).coords)
            # direction of travel towards the end and curvature of the stroke before it
            fit_len = min(paths.length(p, False), max(3 * R, 12.0))
            win = p[: _arc_length_index(p, fit_len) + 1]
            rough = p[0] - win[-1]
            if np.linalg.norm(rough) < 1e-9:
                continue
            rough /= np.linalg.norm(rough)
            kappa = 0.0
            fit = _fit_curvature(win)
            zone_dir = _stem_direction(stems, p[0], R, rough) if stems else None
            if zone_dir is not None:
                # the end lies in a straight stroke: continue exactly along that stroke
                t = zone_dir if zone_dir @ rough >= 0 else -zone_dir
            elif fit is not None and fit_len / fit[0] >= np.radians(15):
                # curved end: continue along the fitted circle (tangent at the end point)
                rho, centre = fit
                radial = p[0] - centre
                t = np.array([-radial[1], radial[0]]) / max(np.linalg.norm(radial), 1e-9)
                if t @ rough < 0:
                    t = -t
                side = t[0] * (centre[1] - p[0][1]) - t[1] * (centre[0] - p[0][0])
                kappa = np.sign(side) / max(rho, R)
            else:
                # straight end: principal direction of the window (immune to a hook at the tip)
                c = win - win.mean(axis=0)
                t = np.linalg.svd(c, full_matrices=False)[2][0]
                if t @ rough < 0:
                    t = -t
            # march along the arc until the end gap is reached
            heading = np.arctan2(t[1], t[0])
            pos = p[0].copy()
            ext = []
            ds = 0.5
            for _ in range(int((4 * R + 10) / ds)):
                heading += kappa * ds
                nxt = pos + ds * np.array([np.cos(heading), np.sin(heading)])
                if not shapely.contains_xy(inner, nxt[0], nxt[1]):
                    break
                ext.append(nxt)
                pos = nxt
            if ext:
                p = np.vstack([np.asarray(ext[::-1]), p])
            edge[2] = p if at_start else p[::-1]
            g.nodes[node] = edge[2][0] if at_start else edge[2][-1]


def _stem_direction(stems, xy, R, along):
    """Direction of a straight stroke that the end at `xy` (heading `along`) belongs to."""
    pt = shapely.points(xy)
    for zone, m0, m1 in stems:
        d = (m1 - m0) / np.linalg.norm(m1 - m0)
        if abs(d @ along) < np.cos(np.radians(25)):
            continue  # a crossing stroke (arm of "f" next to its stem)
        if zone.distance(pt) <= 0.5 * R:
            return d
    return None


def junctions(g: Graph, poly) -> list[tuple[np.ndarray, float]]:
    """Nodes where three or more edges meet, with the stroke radius there."""
    boundary = poly.boundary
    return [(g.nodes[n], boundary.distance(Point(g.nodes[n]))) for n, d in g.degree().items() if d >= 3]


def straighten_at_junctions(
    pts: np.ndarray, closed: bool, junction_list, butt_start: bool, butt_end: bool, factor: float = 2.2
) -> np.ndarray:
    """Remove the dent the medial axis makes where other strokes join.

    A strip passing a junction (stem of "K") is replaced around it by a smooth Hermite
    curve between the undisturbed parts; an end that butts against a junction continues
    straight in its own direction instead of bending towards the junction centre.
    """
    if len(pts) < 4 or not junction_list:
        return pts
    p = pts
    for xy, R in junction_list:
        d = np.linalg.norm(p - xy, axis=1)
        i = int(np.argmin(d))
        if d[i] > max(1.0, 0.6 * R):
            continue
        cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
        s0, total = cum[i], cum[-1]
        win = factor * R
        at_start = s0 < win * 0.75 and not closed
        at_end = total - s0 < win * 0.75 and not closed
        if at_start or at_end:
            if not ((at_start and butt_start) or (at_end and butt_end)):
                continue
            q = p if at_end else p[::-1]
            cq = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))])
            L = cq[-1]
            k = int(np.searchsorted(cq, max(0.0, L - min(win, L / 3))))
            k = min(max(k, 1), len(q) - 2)
            tdir = q[k] - q[max(0, _back_index(cq, k, max(4.0, R)))]
            n = np.linalg.norm(tdir)
            if n < 1e-9:
                continue
            tdir /= n
            end = q[-1]
            chord = end - q[k]
            cl = np.linalg.norm(chord)
            if cl < 1e-6:
                continue
            # keep the end point, approach it smoothly from the undisturbed part
            u = np.linspace(0, 1, max(3, int(cl / 1.0)))[:, None]
            t0, t1 = tdir * cl, chord
            h = (2 * u**3 - 3 * u**2 + 1) * q[k] + (u**3 - 2 * u**2 + u) * t0 + (-2 * u**3 + 3 * u**2) * end + (u**3 - u**2) * t1
            q = np.vstack([q[: k + 1], h[1:]])
            p = q if at_end else q[::-1]
            continue
        if closed:
            continue  # rings (e.g. "e") keep their shape
        win = min(win, 0.35 * s0, 0.35 * (total - s0))  # never reshape most of a short piece
        if win < 2.0:
            continue
        a_s, b_s = max(0.0, s0 - win), min(total, s0 + win)
        ia = int(np.searchsorted(cum, a_s))
        ib = int(np.searchsorted(cum, b_s))
        ia = min(max(ia, 1), len(p) - 2)
        ib = min(max(ib, ia + 2), len(p) - 2)
        A, B = p[ia], p[ib]
        base = max(4.0, R)
        tA = A - p[_back_index(cum, ia, base)]
        tB = p[_fwd_index(cum, ib, base)] - B
        if np.linalg.norm(tA) < 1e-9 or np.linalg.norm(tB) < 1e-9:
            continue
        chord = np.linalg.norm(B - A)
        u = np.linspace(0, 1, max(4, int(chord / 1.0)))[:, None]
        cdir = (B - A) / max(chord, 1e-9)
        ua, ub = tA / np.linalg.norm(tA), tB / np.linalg.norm(tB)
        if ua @ cdir > np.cos(np.radians(12)) and ub @ cdir > np.cos(np.radians(12)):
            h = A + (B - A) * u  # passing straight through: keep it exactly straight
        else:
            tA, tB = ua * chord, ub * chord
            h = (2 * u**3 - 3 * u**2 + 1) * A + (u**3 - 2 * u**2 + u) * tA + (-2 * u**3 + 3 * u**2) * B + (u**3 - u**2) * tB
        p = np.vstack([p[:ia], h, p[ib + 1 :]])
    return p


def _back_index(cum, i, dist):
    return max(0, int(np.searchsorted(cum, cum[i] - dist)))


def _fwd_index(cum, i, dist):
    return min(len(cum) - 1, int(np.searchsorted(cum, cum[i] + dist)))


# --------------------------------------------------------------------------- Decomposition


@dataclass
class Trail:
    pts: np.ndarray
    closed: bool
    start_butt: bool = False  # ends at a junction (butts against another piece)
    end_butt: bool = False


def _dir_from(pts: np.ndarray, dist: float = 4.0) -> np.ndarray:
    """Direction away from the first point (averaged over `dist` mm)."""
    cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    j = int(np.searchsorted(cum, min(cum[-1], dist)))
    j = min(max(j, 1), len(pts) - 1)
    d = pts[j] - pts[0]
    n = np.linalg.norm(d)
    return d / n if n > 1e-12 else np.array([1.0, 0.0])


def decompose(g: Graph, max_turn_deg: float = 100.0, dir_dist: float = 4.0) -> list[Trail]:
    """Decompose the graph into strip pieces (edge-disjoint trails)."""
    inc = g.incident()
    deg = {n: len(es) for n, es in inc.items()}
    unused = set(g.edges)
    passed: set[int] = set()
    through = _pass_through_pairs(g, inc, max_turn_deg, dir_dist)
    trails: list[Trail] = []
    max_turn = math.radians(max_turn_deg)

    def oriented(eid, frm):
        u, v, p = g.edges[eid]
        return (p, v) if u == frm else (p[::-1], u)

    while unused:
        # start node: free ends first, then odd nodes, otherwise any
        free = {n: sum(1 for e in inc[n] if e in unused) for n in inc}
        cand = [n for n, k in free.items() if k > 0]
        start = min(cand, key=lambda n: (0 if deg[n] == 1 else (1 if free[n] % 2 else 2), -free[n]))
        # take the longest unused edge at this node
        eid = max((e for e in inc[start] if e in unused), key=g.edge_length)
        pts, cur = oriented(eid, start)
        unused.discard(eid)
        chain = [pts]
        while True:
            if cur == start and g.edges.get(eid) is not None and deg[cur] <= 2:
                break
            if cur in passed:
                break
            options = []
            if cur in through:
                # at a junction only the designated straight pair passes through
                pair = through[cur]
                if eid not in pair:
                    break
                allowed = pair - {eid}
            else:
                allowed = None
            for e in set(inc.get(cur, [])):
                if e not in unused or (allowed is not None and e not in allowed):
                    continue
                p, nxt = oriented(e, cur)
                options.append((e, p, nxt))
                if g.edges[e][0] == g.edges[e][1]:  # loop: both directions possible
                    options.append((e, p[::-1], nxt))
            if not options:
                break
            incoming = -_dir_from(chain[-1][::-1], dir_dist)
            scored = []
            for opt in options:
                out = _dir_from(opt[1], dir_dist)
                turn = math.acos(float(np.clip(np.dot(incoming, out), -1, 1)))
                scored.append((turn, paths.length(opt[1], False), opt))
            min_turn = min(t for t, _, _ in scored)
            # continuations that are about as straight as the straightest one: take the
            # longest (the right stem of "u" rather than its short foot)
            similar = [x for x in scored if x[0] <= min_turn + math.radians(30)]
            best_turn, _, best = max(similar, key=lambda x: x[1])
            if best_turn > max_turn:
                break
            passed.add(cur)
            eid, p, nxt = best
            unused.discard(eid)
            chain.append(p)
            cur = nxt
        pts = np.vstack([chain[0]] + [c[1:] for c in chain[1:]])
        closed = cur == start and np.linalg.norm(pts[0] - pts[-1]) < 1e-6 and deg[start] <= 2
        if closed:
            pts = pts[:-1]
        trails.append(
            Trail(
                pts=paths.dedupe(pts, closed),
                closed=closed,
                start_butt=(not closed) and deg[start] >= 2,
                end_butt=(not closed) and deg[cur] >= 2,
            )
        )
    return trails


def _pass_through_pairs(g: Graph, inc: dict, max_turn_deg: float, dir_dist: float) -> dict:
    """For every junction choose the pair of edges a strip passes straight through.

    Only one strip can pass a junction (two would cross). Among pairs that are about as
    straight as the straightest pair, the longest one wins - e.g. stem + hook of "f"
    rather than its short crossbar; the other edges butt against it.
    """
    out = {}
    for node, es in inc.items():
        if len(es) < 3 or len(set(es)) != len(es):  # skip nodes with loops
            continue
        dirs = {}
        for e in es:
            u, _v, p = g.edges[e]
            q = p if u == node else p[::-1]
            dirs[e] = (_dir_from(q, dir_dist), paths.length(q, False))
        cands = []
        for i in range(len(es)):
            for j in range(i + 1, len(es)):
                a, b = es[i], es[j]
                turn = math.degrees(math.acos(float(np.clip(-(dirs[a][0] @ dirs[b][0]), -1, 1))))
                if turn <= max_turn_deg:
                    cands.append((turn, dirs[a][1] + dirs[b][1], frozenset((a, b))))
        if not cands:
            continue
        best_turn = min(c[0] for c in cands)
        similar = [c for c in cands if c[0] <= best_turn + 30]
        out[node] = max(similar, key=lambda c: c[1])[2]
    return out


def shorten(p: np.ndarray, at_start: float, at_end: float) -> np.ndarray:
    """Shorten an open polyline at its ends."""
    L = paths.length(p, False)
    if at_start + at_end >= L * 0.8:
        return p
    ls = LineString(p)
    sub = substring(ls, at_start, L - at_end)
    return np.asarray(sub.coords)


# --------------------------------------------------------------------------- straight strokes


def stem_zones(poly, min_len: float, min_width: float, max_width: float) -> list:
    """Straight strokes of a letter: pairs of long, parallel, facing outline edges.

    Returns [(zone_polygon, midline_start, midline_end)] - the zone is the area between the
    two edges, the midline the exact centre line of that stroke.
    """
    raw = []
    for ring in [poly.exterior, *poly.interiors] if poly.geom_type == "Polygon" else []:
        c = np.asarray(ring.simplify(0.3).coords)
        for a, b in itertools.pairwise(c):
            if np.linalg.norm(b - a) >= 0.35 * min_len:
                raw.append((a, b))
    # collinear pieces of one outline edge interrupted by a crossing stroke (stem of "f"
    # interrupted by the crossbar) are merged when the gap between them is ink
    edges = _merge_collinear(raw, poly)
    edges = [(a, b) for a, b in edges if np.linalg.norm(b - a) >= min_len]
    zones = []
    for i in range(len(edges)):
        a1, b1 = edges[i]
        d1 = (b1 - a1) / np.linalg.norm(b1 - a1)
        n1 = np.array([-d1[1], d1[0]])
        for j in range(i + 1, len(edges)):
            a2, b2 = edges[j]
            d2 = (b2 - a2) / np.linalg.norm(b2 - a2)
            if abs(abs(d1 @ d2) - 1) > 1 - np.cos(np.radians(4)):
                continue
            dist = (a2 - a1) @ n1
            if not (min_width <= abs(dist) <= max_width):
                continue
            # overlap of both edges along the common direction
            s1 = sorted([0.0, (b1 - a1) @ d1])
            s2 = sorted([(a2 - a1) @ d1, (b2 - a1) @ d1])
            lo, hi = max(s1[0], s2[0]), min(s1[1], s2[1])
            if hi - lo < 0.6 * min_len:
                continue
            m0 = a1 + d1 * lo + n1 * dist / 2
            m1 = a1 + d1 * hi + n1 * dist / 2
            if not poly.contains(Point((m0 + m1) / 2)):
                continue
            zone = Polygon([a1 + d1 * lo, a1 + d1 * hi, a1 + d1 * hi + n1 * dist, a1 + d1 * lo + n1 * dist])
            # the area between the edges must really be ink (not a counter between strokes)
            if zone.difference(poly).area > 0.05 * zone.area:
                continue
            zones.append((zone.buffer(-0.01), m0, m1))
    return zones


def _merge_collinear(edges, poly, ang_tol_deg: float = 2.0, off_tol: float = 0.6):
    """Merge collinear edge segments whose gaps lie inside the shape."""
    used = [False] * len(edges)
    out = []
    for i, (a, b) in enumerate(edges):
        if used[i]:
            continue
        d = (b - a) / np.linalg.norm(b - a)
        n = np.array([-d[1], d[0]])
        group = [(a @ d, b @ d)]
        used[i] = True
        for j in range(i + 1, len(edges)):
            if used[j]:
                continue
            a2, b2 = edges[j]
            d2 = (b2 - a2) / np.linalg.norm(b2 - a2)
            if abs(abs(d @ d2) - 1) > 1 - np.cos(np.radians(ang_tol_deg)):
                continue
            if abs((a2 - a) @ n) > off_tol or abs((b2 - a) @ n) > off_tol:
                continue
            group.append(tuple(sorted((a2 @ d, b2 @ d))))
            used[j] = True
        group = sorted(tuple(sorted(g)) for g in group)
        base = a - d * (a @ d)  # point on the line at parameter 0
        cur = list(group[0])
        for lo, hi in group[1:]:
            mid = base + d * ((cur[1] + lo) / 2)
            if lo <= cur[1] + 1e-6 or poly.buffer(0.5).contains(Point(mid)):
                cur[1] = max(cur[1], hi)
            else:
                out.append((base + d * cur[0], base + d * cur[1]))
                cur = [lo, hi]
        out.append((base + d * cur[0], base + d * cur[1]))
    return out


def snap_to_stems(pts: np.ndarray, zones) -> np.ndarray:
    """Pull path points inside a straight stroke onto its exact centre line.

    Inside the stroke the point is projected fully; over one stroke width beyond the
    stroke's ends the pull fades out, so the path joins curves and junctions smoothly.
    """
    if not zones or len(pts) < 2:
        return pts
    q = pts.copy()
    for zone, m0, m1 in zones:
        d = m1 - m0
        L = float(np.linalg.norm(d))
        if L < 1e-9:
            continue
        u = d / L
        nrm = np.array([-u[1], u[0]])
        # half width of the stroke = distance from the midline to the zone edge
        half = max(1e-6, float(shapely.distance(zone.exterior, shapely.points(m0 + d / 2))))
        rel = q - m0
        along = rel @ u
        across = rel @ nrm
        lateral = np.abs(across) <= half * 1.05
        # only points that run along this stroke (not a crossing stroke such as the stem of "f")
        k = 4  # tangent over about +-4 mm (points are ~1 mm apart) - robust against noise
        idx = np.arange(len(q))
        tang = q[np.minimum(idx + k, len(q) - 1)] - q[np.maximum(idx - k, 0)]
        tn = np.linalg.norm(tang, axis=1)
        parallel = np.abs((tang @ u) / np.maximum(tn, 1e-9)) > np.cos(np.radians(25))
        fade = half * 2
        w = np.where((along >= 0) & (along <= L), 1.0, np.clip(1 - np.maximum(-along, along - L) / fade, 0, 1))
        w = np.where(lateral & parallel, w, 0.0)
        if (w > 0.99).sum() < 2:
            continue
        q = q - (w * across)[:, None] * nrm
    return q
