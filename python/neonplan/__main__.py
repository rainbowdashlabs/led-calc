"""Command line interface: compute a plan and write the printable PDF (and JSON).

Example (inside the nix shell, from the repository root):
    PYTHONPATH=python python -m neonplan "Hallo" --font public/fonts/pacifico.ttf \
        --mode contour --cap-height 150 --strip-width 7 --bend-radius 30 --paper A3 -o hallo.pdf
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from . import api


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="neonplan", description="LED neon strip planner for illuminated lettering")
    ap.add_argument("text")
    ap.add_argument("--font", required=True, help="TTF/OTF outline font or Hershey .jhf single-stroke font")
    ap.add_argument("--mode", choices=["contour", "single"], default="contour")
    ap.add_argument("--cap-height", type=float, default=150, help="capital letter height in mm")
    ap.add_argument("--width-scale", type=float, default=1.0)
    ap.add_argument("--tracking", type=float, default=0.0, help="extra letter spacing in mm")
    ap.add_argument("--strip-width", type=float, default=7.0, help="mm")
    ap.add_argument("--bend-radius", type=float, default=30.0, help="minimum bend radius in mm")
    ap.add_argument("--connection", choices=["strip", "cable"], default="strip")
    ap.add_argument("--paper", choices=["A4", "A3"], default="A4")
    ap.add_argument("--params", type=pathlib.Path, help="JSON file with further parameters (see api.DEFAULTS)")
    ap.add_argument("-o", "--output", type=pathlib.Path, default=pathlib.Path("neonplan.pdf"))
    ap.add_argument("--json", type=pathlib.Path, help="also write the computed plan as JSON")
    a = ap.parse_args(argv)

    font = pathlib.Path(a.font)
    params = json.loads(a.params.read_text()) if a.params else {}
    params.update(
        {
            "text": a.text,
            "font_kind": "hershey" if font.suffix.lower() == ".jhf" else "outline",
            "mode": a.mode,
            "cap_height": a.cap_height,
            "width_scale": a.width_scale,
            "tracking": a.tracking,
            "strip_width": a.strip_width,
            "bend_radius": a.bend_radius,
            "connection": a.connection,
        }
    )
    plan = api.compute(params, font.read_bytes())
    if not plan.get("ok"):
        print("\n".join(plan.get("warnings", ["failed"])), file=sys.stderr)
        return 1
    a.output.write_bytes(api.make_pdf(plan, a.paper))
    if a.json:
        a.json.write_text(json.dumps(plan))
    s = plan["summary"]
    print(
        f"strip to buy: {s['strip_cut_total'] / 1000:.2f} m  (front {s['front'] / 1000:.2f} m, "
        f"behind plate {s['back_strip'] / 1000:.2f} m)  pieces: {s['pieces']}  holes: {s['holes']}"
    )
    for w in plan["warnings"]:
        print("note:", w)
    print(f"wrote {a.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
