"""Polyline tools: length, resampling, corner filleting, bend radius checks.

A path is an (n, 2) NumPy array. Closed paths do not repeat the first point at the end.
"""

from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LinearRing, LineString


def as_array(pts) -> np.ndarray:
    a = np.asarray(pts, dtype=float).reshape(-1, 2)
    return a


def dedupe(p: np.ndarray, closed: bool, eps: float = 1e-6) -> np.ndarray:
    if len(p) < 2:
        return p
    keep = np.ones(len(p), dtype=bool)
    keep[1:] = np.linalg.norm(np.diff(p, axis=0), axis=1) > eps
    p = p[keep]
    if closed and len(p) > 2 and np.linalg.norm(p[0] - p[-1]) <= eps:
        p = p[:-1]
    return p


def length(p: np.ndarray, closed: bool) -> float:
    if len(p) < 2:
        return 0.0
    q = np.vstack([p, p[:1]]) if closed else p
    return float(np.sum(np.linalg.norm(np.diff(q, axis=0), axis=1)))


def resample(p: np.ndarray, step: float, closed: bool) -> np.ndarray:
    """Evenly spaced points along the path (spacing ~ step)."""
    q = np.vstack([p, p[:1]]) if closed else p
    seg = np.linalg.norm(np.diff(q, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    total = cum[-1]
    if total <= 0:
        return p[:1].copy()
    n = max(2 if not closed else 3, math.ceil(total / step))
    t = np.linspace(0, total, n, endpoint=False) if closed else np.linspace(0, total, n + 1)
    x = np.interp(t, cum, q[:, 0])
    y = np.interp(t, cum, q[:, 1])
    return np.column_stack([x, y])


def simplify(p: np.ndarray, tol: float, closed: bool) -> np.ndarray:
    if len(p) < (4 if closed else 3):
        return p
    if closed:
        g = LinearRing(p).simplify(tol, preserve_topology=False)
        c = np.asarray(g.coords)[:-1] if not g.is_empty else p
        return c if len(c) >= 3 else p
    g = LineString(p).simplify(tol, preserve_topology=False)
    return np.asarray(g.coords)


def fillet(
    p: np.ndarray, radius: float, closed: bool, min_turn_deg: float = 12.0, arc_step: float = 1.0, allow: np.ndarray | None = None
) -> np.ndarray:
    """Replace corners by circular arcs of `radius` (as far as the segments allow).

    `allow` (bool per vertex) restricts filleting to selected vertices.
    """
    n = len(p)
    if n < 3 or radius <= 0:
        return p
    out = []
    idx = range(n) if closed else range(1, n - 1)
    if not closed:
        out.append(p[0])
    min_turn = math.radians(min_turn_deg)
    for i in idx:
        a, b, c = p[(i - 1) % n], p[i], p[(i + 1) % n]
        ba, bc = a - b, c - b
        la, lc = np.linalg.norm(ba), np.linalg.norm(bc)
        if la < 1e-9 or lc < 1e-9:
            out.append(b)
            continue
        u, v = ba / la, bc / lc
        cosphi = float(np.clip(np.dot(u, v), -1, 1))
        phi = math.acos(cosphi)  # interior angle
        turn = math.pi - phi  # change of direction
        if turn < min_turn or phi < 1e-3:
            out.append(b)
            continue
        if allow is not None and not allow[i]:
            out.append(b)
            continue
        # room: half of each segment, the whole segment at open path ends
        avail_a = la if (not closed and i - 1 == 0) else la / 2
        avail_c = lc if (not closed and i + 1 == n - 1) else lc / 2
        t_need = radius * math.tan(turn / 2)
        t = min(t_need, avail_a, avail_c)
        r_eff = t / math.tan(turn / 2)
        p1 = b + u * t
        p2 = b + v * t
        bis = u + v
        bis /= np.linalg.norm(bis)
        center = b + bis * (r_eff / math.sin(phi / 2))
        a1 = math.atan2(p1[1] - center[1], p1[0] - center[0])
        a2 = math.atan2(p2[1] - center[1], p2[0] - center[0])
        sweep = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        k = max(2, math.ceil(abs(sweep) * r_eff / arc_step), math.ceil(abs(sweep) / math.radians(6)))
        for j in range(k + 1):
            ang = a1 + sweep * j / k
            out.append(center + r_eff * np.array([math.cos(ang), math.sin(ang)]))
    if not closed:
        out.append(p[-1])
    return dedupe(np.asarray(out), closed)


def local_radius(p: np.ndarray, closed: bool, span: int) -> np.ndarray:
    """Circumradius through points i-span, i, i+span (for evenly spaced paths)."""
    n = len(p)
    r = np.full(n, np.inf)
    if n < 3:
        return r
    if closed:
        span = max(1, min(span, (n - 1) // 2))
        a = np.roll(p, span, axis=0)
        c = np.roll(p, -span, axis=0)
        b = p
        sl = slice(None)
    else:
        span = max(1, min(span, (n - 1) // 2))
        a, b, c = p[: -2 * span], p[span:-span], p[2 * span :]
        sl = slice(span, n - span)
    ab = np.linalg.norm(b - a, axis=1)
    bc = np.linalg.norm(c - b, axis=1)
    ca = np.linalg.norm(a - c, axis=1)
    cross = np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
    with np.errstate(divide="ignore", invalid="ignore"):
        rr = ab * bc * ca / (2 * cross)
    rr[~np.isfinite(rr)] = np.inf
    r[sl] = rr
    return r


def _clamp_to(corridor, boundary, q: np.ndarray, mask: np.ndarray) -> None:
    """Move points of `q[mask]` that left `corridor` back onto its boundary (in place)."""
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return
    inside = shapely.contains_xy(corridor, q[idx, 0], q[idx, 1])
    out = idx[~inside]
    if len(out) == 0:
        return
    lines = shapely.shortest_line(boundary, shapely.points(q[out]))
    q[out] = shapely.get_coordinates(lines)[0::2]


def relax(p: np.ndarray, radius: float, closed: bool, step: float, max_dev: float, iterations: int = 150, corridor=None) -> np.ndarray:
    """Smooth spots whose bend radius is too small (Laplacian smoothing).

    Movement is limited either by `max_dev` (distance to the original path) or, if a
    `corridor` polygon is given, by staying inside it. A corridor lets the strip use the
    full width of a thick stroke and cut the inside of a bend like a racing line, which
    gives a much larger bend radius than following the centreline.
    """
    if len(p) < 5 or radius <= 0:
        return p
    span = max(1, round(radius / (3 * step)))
    orig = p.copy()
    q = p.copy()
    len(q)
    boundary = None
    if corridor is not None:
        shapely.prepare(corridor)
        boundary = corridor.boundary
    for _ in range(iterations):
        r = local_radius(q, closed, span)
        bad = r < radius * 0.97
        if not bad.any():
            break
        # smooth the neighbourhood of bad spots as well
        mask = bad.copy()
        for s in range(1, span + 1):
            mask |= np.roll(bad, s) | np.roll(bad, -s) if closed else _shift_or(bad, s)
        if not closed:
            mask[0] = mask[-1] = False
        if closed:
            mid = (np.roll(q, 1, axis=0) + np.roll(q, -1, axis=0)) / 2
        else:
            mid = q.copy()
            mid[1:-1] = (q[:-2] + q[2:]) / 2
        q[mask] = q[mask] + 0.5 * (mid[mask] - q[mask])
        if corridor is not None:
            _clamp_to(corridor, boundary, q, mask)
        else:
            d = q - orig
            dist = np.linalg.norm(d, axis=1)
            over = dist > max_dev
            if over.any():
                q[over] = orig[over] + d[over] / dist[over, None] * max_dev
    return q


def _shift_or(bad: np.ndarray, s: int) -> np.ndarray:
    out = np.zeros_like(bad)
    out[s:] |= bad[:-s]
    out[:-s] |= bad[s:]
    return out


def find_violations(p: np.ndarray, radius: float, closed: bool, step: float) -> list[dict]:
    """Group spots with bend radius < radius; return position and smallest radius of each."""
    if len(p) < 5 or radius <= 0:
        return []
    span = max(1, round(radius / (3 * step)))
    r = local_radius(p, closed, span)
    bad = r < radius * 0.9
    if not bad.any():
        return []
    out = []
    n = len(p)
    visited = np.zeros(n, dtype=bool)
    idxs = np.flatnonzero(bad)
    for start in idxs:
        if visited[start]:
            continue
        group = []
        j = start
        while bad[j] and not visited[j]:
            visited[j] = True
            group.append(j)
            j = (j + 1) % n if closed else j + 1
            if j >= n:
                break
        k = group[int(np.argmin(r[group]))]
        out.append({"x": float(p[k, 0]), "y": float(p[k, 1]), "radius": float(r[k])})
    return out


def smooth_path(p: np.ndarray, radius: float, closed: bool, step: float = 1.5) -> np.ndarray:
    """Clean a strip path without changing its character.

    Removes noise (e.g. from the Voronoi skeleton), replaces sharp corners by arcs of
    `radius` where the segments allow it and resamples evenly. Bends are never pulled
    inwards here - that would make them tighter. Spots that stay too tight are reported;
    stronger, shape-changing smoothing is the opt-in `relax`.
    """
    p = dedupe(as_array(p), closed)
    if len(p) < 2:
        return p
    p = resample(p, step, closed)
    p = taubin(p, closed, passes=12)
    if radius > 0:
        # only vertices where the dense path is actually tighter than `radius` are corners;
        # filleting vertices of a gentle curve would make it tighter instead
        r_dense = local_radius(p, closed, max(1, round(radius / (3 * step))))
        s = simplify(p, 0.25, closed)
        d = np.linalg.norm(s[:, None, :] - p[None, :, :], axis=2)
        near = np.argmin(d, axis=1)
        win = max(1, round(radius / (2 * step)))
        allow = np.array(
            [
                np.min(r_dense[np.arange(j - win, j + win + 1) % len(p)] if closed else r_dense[max(0, j - win) : j + win + 1])
                < radius * 0.97
                for j in near
            ]
        )
        if not allow.any():
            return p  # nothing tighter than the radius: keep the dense, faithful path
        p = fillet(s, radius, closed, allow=allow)
        p = taubin(resample(p, step, closed), closed, passes=4)  # remove facets of the simplified polygon
    return resample(p, step, closed)


def taubin(q: np.ndarray, closed: bool, passes: int = 1, lam: float = 0.5, mu: float = -0.53, mask: np.ndarray | None = None) -> np.ndarray:
    """Low-pass filter for polylines that removes zig-zag without shrinking the path.

    `mask` restricts the filter to selected points (others stay where they are).
    """
    q = q.copy()
    w = np.ones(len(q)) if mask is None else mask.astype(float)
    if not closed:
        w[0] = w[-1] = 0.0
    for _ in range(passes):
        for f in (lam, mu):
            if closed:
                mid = (np.roll(q, 1, axis=0) + np.roll(q, -1, axis=0)) / 2
            else:
                mid = q.copy()
                mid[1:-1] = (q[:-2] + q[2:]) / 2
            q += (f * w)[:, None] * (mid - q)
    return q
