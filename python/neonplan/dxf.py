"""DXF export of a plan for CNC milling (DXF R12, millimetres, one layer per purpose).

The file is meant for a CAM program (Estlcam, Fusion 360, Carbide Create, Vectric, ...),
which creates the tool paths. Layers:

- PLATTE              plate outline (closed)
- SCHRIFT             letter outlines (reference)
- LED_MITTELLINIE     centre line of every strip piece (e.g. for a slot cut with a cutter
                      as wide as the channel)
- KANAL               channel outlines to mill (groove) or cut through
- STEGE               bridges that must stay (through cuts)
- BOHRUNGEN           holes for the strip / cables (circles)
- RUECKSEITE_ROUTING  routes behind the plate, mirrored for machining from the back

R12 is the oldest and most widely supported DXF version; it needs no library.
"""

from __future__ import annotations

import math

# AutoCAD colour index per layer
LAYERS = {
    "PLATTE": 7,
    "SCHRIFT": 8,
    "LED_MITTELLINIE": 6,
    "KANAL": 1,
    "STEGE": 3,
    "BOHRUNGEN": 4,
    "RUECKSEITE_ROUTING": 30,
}


class _Writer:
    def __init__(self):
        self.lines: list[str] = []

    def pair(self, code: int, value) -> None:
        if isinstance(value, float):
            value = f"{value:.4f}".rstrip("0").rstrip(".") or "0"
        self.lines += [str(code), str(value)]

    def comment(self, text: str) -> None:
        self.pair(999, text)

    def polyline(self, layer: str, points, closed: bool) -> None:
        pts = [(float(x), float(y)) for x, y in points]
        if closed and len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-6:
            pts = pts[:-1]
        if len(pts) < 2:
            return
        self.pair(0, "POLYLINE")
        self.pair(8, layer)
        self.pair(66, 1)  # vertices follow
        self.pair(10, 0.0)
        self.pair(20, 0.0)
        self.pair(30, 0.0)
        self.pair(70, 1 if closed else 0)
        for x, y in pts:
            self.pair(0, "VERTEX")
            self.pair(8, layer)
            self.pair(10, x)
            self.pair(20, y)
            self.pair(30, 0.0)
        self.pair(0, "SEQEND")
        self.pair(8, layer)

    def circle(self, layer: str, x: float, y: float, r: float) -> None:
        self.pair(0, "CIRCLE")
        self.pair(8, layer)
        self.pair(10, float(x))
        self.pair(20, float(y))
        self.pair(30, 0.0)
        self.pair(40, float(r))

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def _rounded_rect(w: float, h: float, r: float, step_deg: float = 5.0):
    """Outline of the plate as a polygon (rounded corners approximated by short segments)."""
    r = max(0.0, min(r, w / 2, h / 2))
    if r <= 0:
        return [(0, 0), (w, 0), (w, h), (0, h)]
    pts = []
    n = max(2, int(90 / step_deg))
    for cx, cy, start in ((w - r, r, -90), (w - r, h - r, 0), (r, h - r, 90), (r, r, 180)):
        for k in range(n + 1):
            a = math.radians(start + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def render_dxf(plan: dict) -> str:
    """DXF text of the plan (front coordinates; the back side routes are mirrored)."""
    W, H = plan["plate"]["w"], plan["plate"]["h"]
    params = plan["params"]
    out = _Writer()
    out.comment("LED-Neon Planer - CNC export, units: millimetres")
    cut = plan.get("cut")
    if cut:
        depth = "through" if cut["mode"] == "through" else f"{cut['depth']:g} mm deep"
        out.comment(f"Channel width {cut['width']:g} mm, {depth}")
    out.comment(f"Holes: diameter {params['hole_diameter']:g} mm")

    # header: millimetres and drawing extents
    out.pair(0, "SECTION")
    out.pair(2, "HEADER")
    out.pair(9, "$ACADVER")
    out.pair(1, "AC1009")
    out.pair(9, "$INSUNITS")
    out.pair(70, 4)  # millimetres
    out.pair(9, "$MEASUREMENT")
    out.pair(70, 1)  # metric
    out.pair(9, "$EXTMIN")
    out.pair(10, 0.0)
    out.pair(20, 0.0)
    out.pair(9, "$EXTMAX")
    out.pair(10, float(W))
    out.pair(20, float(H))
    out.pair(0, "ENDSEC")

    # layer table
    out.pair(0, "SECTION")
    out.pair(2, "TABLES")
    out.pair(0, "TABLE")
    out.pair(2, "LAYER")
    out.pair(70, len(LAYERS))
    for name, colour in LAYERS.items():
        out.pair(0, "LAYER")
        out.pair(2, name)
        out.pair(70, 0)
        out.pair(62, colour)
        out.pair(6, "CONTINUOUS")
    out.pair(0, "ENDTAB")
    out.pair(0, "ENDSEC")

    # geometry
    out.pair(0, "SECTION")
    out.pair(2, "ENTITIES")
    out.polyline("PLATTE", _rounded_rect(W, H, plan["plate"]["corner"]), closed=True)
    for rings in plan["letters"]:
        for ring in rings:
            out.polyline("SCHRIFT", ring, closed=True)
    for stroke in plan.get("strokes", []):
        out.polyline("SCHRIFT", stroke, closed=False)
    for piece in plan["pieces"]:
        out.polyline("LED_MITTELLINIE", piece["pts"], closed=piece["closed"])
    if cut:
        for rings in cut["channels"]:
            for ring in rings:
                out.polyline("KANAL", ring, closed=True)
        for rings in cut["bridges"]:
            for ring in rings:
                out.polyline("STEGE", ring, closed=True)
    radius = params["hole_diameter"] / 2
    for hole in plan["holes"]:
        out.circle("BOHRUNGEN", hole["x"], hole["y"], radius)
    for link in plan["links"]:
        path = link.get("path") or [link["a"], link["b"]]
        out.polyline("RUECKSEITE_ROUTING", [(W - x, y) for x, y in path], closed=False)
    out.pair(0, "ENDSEC")
    out.pair(0, "EOF")
    return out.text()
