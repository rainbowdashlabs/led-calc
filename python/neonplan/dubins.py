"""Shortest paths with a minimum turning radius (Dubins paths).

Used for the strip behind the plate: it leaves a hole in its direction of travel and
must reach the next hole in the direction of the next piece without bending tighter
than the minimum bend radius.
"""

from __future__ import annotations

import math

import numpy as np

TAU = 2 * math.pi


def _mod(a: float) -> float:
    return a % TAU


def _words(alpha, beta, d):
    """Candidate (t, p, q) segment lengths (normalised) for the six Dubins words."""
    sa, sb, ca, cb = math.sin(alpha), math.sin(beta), math.cos(alpha), math.cos(beta)
    cab = math.cos(alpha - beta)
    out = {}
    tmp = 2 + d * d - 2 * cab + 2 * d * (sa - sb)
    if tmp >= 0:
        th = math.atan2(cb - ca, d + sa - sb)
        out["LSL"] = (_mod(-alpha + th), math.sqrt(tmp), _mod(beta - th))
    tmp = 2 + d * d - 2 * cab + 2 * d * (sb - sa)
    if tmp >= 0:
        th = math.atan2(ca - cb, d - sa + sb)
        out["RSR"] = (_mod(alpha - th), math.sqrt(tmp), _mod(-beta + th))
    tmp = -2 + d * d + 2 * cab + 2 * d * (sa + sb)
    if tmp >= 0:
        p = math.sqrt(tmp)
        th = math.atan2(-ca - cb, d + sa + sb) - math.atan2(-2.0, p)
        out["LSR"] = (_mod(-alpha + th), p, _mod(-_mod(beta) + th))
    tmp = d * d - 2 + 2 * cab - 2 * d * (sa + sb)
    if tmp >= 0:
        p = math.sqrt(tmp)
        th = math.atan2(ca + cb, d - sa - sb) - math.atan2(2.0, p)
        out["RSL"] = (_mod(alpha - th), p, _mod(beta - th))
    tmp = (6 - d * d + 2 * cab + 2 * d * (sa - sb)) / 8
    if abs(tmp) <= 1:
        p = _mod(TAU - math.acos(tmp))
        t = _mod(alpha - math.atan2(ca - cb, d - sa + sb) + p / 2)
        out["RLR"] = (t, p, _mod(alpha - beta - t + p))
    tmp = (6 - d * d + 2 * cab + 2 * d * (sb - sa)) / 8
    if abs(tmp) <= 1:
        p = _mod(TAU - math.acos(tmp))
        t = _mod(-alpha - math.atan2(ca - cb, d + sa - sb) + p / 2)
        out["LRL"] = (t, p, _mod(_mod(beta) - alpha - t + p))
    return out


def _sample(x, y, th, word, lens, r, step):
    pts = [(x, y)]
    for kind, L in zip(word, lens, strict=False):
        L *= r
        n = max(1, math.ceil(L / step))
        ds = L / n
        for _ in range(n):
            if kind == "S":
                x += ds * math.cos(th)
                y += ds * math.sin(th)
            else:
                sgn = 1 if kind == "L" else -1
                dth = sgn * ds / r
                cx, cy = x - sgn * r * math.sin(th), y + sgn * r * math.cos(th)
                th += dth
                x, y = cx + sgn * r * math.sin(th), cy - sgn * r * math.cos(th)
            pts.append((x, y))
    return np.asarray(pts), th


def dubins_length(p0, heading0: float, p1, heading1: float, r: float) -> float:
    """Length of the shortest path (no sampling, fast)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    D = math.hypot(dx, dy)
    if r <= 0:
        return D
    theta = _mod(math.atan2(dy, dx)) if D > 1e-9 else 0.0
    words = _words(_mod(heading0 - theta), _mod(heading1 - theta), D / r)
    return min((sum(v) * r for v in words.values()), default=D)


def dubins(p0, heading0: float, p1, heading1: float, r: float, step: float = 2.0):
    """Return (length, points) of the shortest path; straight line if r <= 0."""
    if r <= 0:
        pts = np.asarray([p0, p1], dtype=float)
        return float(np.linalg.norm(pts[1] - pts[0])), pts
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    D = math.hypot(dx, dy)
    d = D / r
    theta = _mod(math.atan2(dy, dx)) if D > 1e-9 else 0.0
    alpha = _mod(heading0 - theta)
    beta = _mod(heading1 - theta)
    best = None
    for word, lens in sorted(_words(alpha, beta, d).items(), key=lambda kv: sum(kv[1])):
        pts, th = _sample(p0[0], p0[1], heading0, word, lens, r, step)
        dth = abs((th - heading1 + math.pi) % TAU - math.pi)
        if np.linalg.norm(pts[-1] - np.asarray(p1)) < max(0.5, r * 0.02) and dth < 0.05:  # self-check
            pts[-1] = p1
            best = (sum(lens) * r, pts)
            break
    if best is None:
        pts = np.asarray([p0, p1], dtype=float)
        return D, pts
    return best
