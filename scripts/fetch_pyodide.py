"""Download the Pyodide runtime and the packages neonplan needs into public/pyodide/.

The app then serves Pyodide itself (no CDN needed at runtime). Run once locally and in CI:
    python scripts/fetch_pyodide.py
"""

import json
import pathlib
import sys
import urllib.request

VERSION = "314.0.7"
BASE = f"https://cdn.jsdelivr.net/pyodide/v{VERSION}/full/"
OUT = pathlib.Path(__file__).resolve().parent.parent / "public" / "pyodide"
CORE = ["pyodide.mjs", "pyodide.asm.mjs", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
PACKAGES = ["numpy", "shapely", "fonttools"]


def fetch(name: str) -> None:
    target = OUT / name
    if target.exists() and target.stat().st_size > 0:
        print(f"ok    {name}")
        return
    tmp = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(BASE + name, timeout=600) as r, open(tmp, "wb") as fh:
        while chunk := r.read(1 << 16):
            fh.write(chunk)
    tmp.rename(target)
    print(f"fetch {name} ({target.stat().st_size // 1024} KiB)", flush=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in CORE:
        fetch(name)
    lock = json.loads((OUT / "pyodide-lock.json").read_text())
    todo, seen = list(PACKAGES), set()
    while todo:
        pkg = todo.pop()
        if pkg in seen:
            continue
        seen.add(pkg)
        info = lock["packages"][pkg]
        todo += info.get("depends", [])
        fetch(info["file_name"])
    (OUT / "VERSION").write_text(VERSION)


if __name__ == "__main__":
    sys.exit(main())
