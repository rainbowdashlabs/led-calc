"""Prepare the bundled fonts for the web app.

- Downloads the font sources from github.com/google/fonts (or uses a local directory).
- Variable fonts keep their weight axis, so the stroke weight can be chosen in the app
  (thin weights give cleaner centre lines for single-line laying). Other axes are pinned.
- All fonts are subset to Latin-1 plus common punctuation.
- Hershey single-stroke fonts (public domain) are downloaded.
- Writes public/fonts/fonts.json as the catalogue for the frontend.

Usage (inside the nix shell):  python scripts/prepare_fonts.py [dir-with-ttf-files]
"""

import io
import json
import pathlib
import sys
import tempfile
import urllib.parse
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "fonts"
GOOGLE = "https://raw.githubusercontent.com/google/fonts/main/"

# (id, display name, source path in google/fonts, pinned axes, category (UI label), licence)
FONTS = [
    ("pacifico", "Pacifico", "ofl/pacifico/Pacifico-Regular.ttf", None, "Schreibschrift", "OFL"),
    ("dancing", "Dancing Script", "ofl/dancingscript/DancingScript[wght].ttf", None, "Schreibschrift", "OFL"),
    ("lobster", "Lobster", "ofl/lobster/Lobster-Regular.ttf", None, "Schreibschrift", "OFL"),
    ("kaushan", "Kaushan Script", "ofl/kaushanscript/KaushanScript-Regular.ttf", None, "Schreibschrift", "OFL"),
    ("yellowtail", "Yellowtail", "apache/yellowtail/Yellowtail-Regular.ttf", None, "Schreibschrift", "Apache-2.0"),
    ("sacramento", "Sacramento", "ofl/sacramento/Sacramento-Regular.ttf", None, "Schreibschrift (dünn)", "OFL"),
    ("neonderthaw", "Neonderthaw", "ofl/neonderthaw/Neonderthaw-Regular.ttf", None, "Schreibschrift (dünn)", "OFL"),
    ("bebas", "Bebas Neue", "ofl/bebasneue/BebasNeue-Regular.ttf", None, "Serifenlos", "OFL"),
    ("montserrat", "Montserrat", "ofl/montserrat/Montserrat[wght].ttf", None, "Serifenlos", "OFL"),
    ("righteous", "Righteous", "ofl/righteous/Righteous-Regular.ttf", None, "Serifenlos", "OFL"),
    ("comfortaa", "Comfortaa", "ofl/comfortaa/Comfortaa[wght].ttf", None, "Gerundet", "OFL"),
    ("quicksand", "Quicksand", "ofl/quicksand/Quicksand[wght].ttf", None, "Gerundet", "OFL"),
    ("baloo", "Baloo 2", "ofl/baloo2/Baloo2[wght].ttf", None, "Gerundet", "OFL"),
    ("fredoka", "Fredoka", "ofl/fredoka/Fredoka[wdth,wght].ttf", {"wdth": 100}, "Gerundet", "OFL"),
]

HERSHEY = [
    ("h-futural", "Hershey Futura Light", "futural", "Einlinien (Hershey)"),
    ("h-futuram", "Hershey Futura Medium", "futuram", "Einlinien (Hershey)"),
    ("h-rowmans", "Hershey Roman Simplex", "rowmans", "Einlinien (Hershey)"),
    ("h-scripts", "Hershey Script Simplex", "scripts", "Einlinien (Hershey)"),
    ("h-cursive", "Hershey Cursive", "cursive", "Einlinien (Hershey)"),
]
HERSHEY_URL = "https://raw.githubusercontent.com/kamalmostafa/hershey-fonts/master/hershey-fonts/{}.jhf"

UNICODES = (
    list(range(0x20, 0x7F))
    + list(range(0xA0, 0x100))
    + [0x20AC, 0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x201E, 0x2022, 0x2026, 0x2665, 0x2764]
)


def fetch(url: str, target: pathlib.Path) -> pathlib.Path:
    if not target.exists():
        target.write_bytes(urllib.request.urlopen(url, timeout=120).read())
    return target


def main(src: pathlib.Path | None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="fonts-"))
    catalog = []
    for fid, name, path, pin, cat, lic in FONTS:
        fname = pathlib.Path(path).name
        local = (src / fname) if src and (src / fname).exists() else fetch(GOOGLE + urllib.parse.quote(path), tmp / fname)
        font = TTFont(local)
        if pin:
            font = instancer.instantiateVariableFont(font, pin)
            buf = io.BytesIO()
            font.save(buf)  # reload: the partially instanced font must be fully compiled before subsetting
            buf.seek(0)
            font = TTFont(buf)
        axes = {}
        if "fvar" in font:
            for ax in font["fvar"].axes:
                axes[ax.axisTag] = [ax.minValue, ax.defaultValue, ax.maxValue]
        opts = subset.Options()
        opts.layout_features = ["kern", "liga", "calt", "curs"]
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=UNICODES)
        sub.subset(font)
        out = OUT / f"{fid}.ttf"
        font.save(out)
        entry = {"id": fid, "name": name, "file": f"{fid}.ttf", "kind": "outline", "category": cat, "license": lic}
        if "wght" in axes:
            lo, _, hi = axes["wght"]
            entry["weight"] = {
                "min": lo,
                "max": hi,
                "single": max(lo, min(hi, 300)),  # thin strokes: clean centre lines
                "contour": max(lo, min(hi, 700)),
            }  # bold strokes: room for two strips
        catalog.append(entry)
        print(f"{fid:12s} {out.stat().st_size // 1024:5d} KiB  axes={axes}")
    for fid, name, base, cat in HERSHEY:
        data = urllib.request.urlopen(HERSHEY_URL.format(base), timeout=60).read()
        (OUT / f"{fid}.jhf").write_bytes(data)
        catalog.append({"id": fid, "name": name, "file": f"{fid}.jhf", "kind": "hershey", "category": cat, "license": "Public Domain"})
        print(f"{fid:12s} {len(data) // 1024:5d} KiB")
    (OUT / "fonts.json").write_text(json.dumps(catalog, indent=2, ensure_ascii=False))
    for lic, path in (("OFL.txt", "ofl/pacifico/OFL.txt"), ("APACHE.txt", "apache/yellowtail/LICENSE.txt")):
        fetch(GOOGLE + path, OUT / lic)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None)
