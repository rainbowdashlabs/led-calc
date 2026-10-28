# LED-Neon Planner

Plan LED neon flex strips for illuminated lettering — entirely in the browser.

Pick a font, type the text and choose how the strip is laid. The app computes the strip
paths, the required length (front **and** behind the plate), drill holes, the routing behind
the plate and produces a printable 1:1 cut and routing template (DIN A4 / A3, tiled with glue
overlaps) that can be stuck together and used as a stencil.

The UI is available in German and English (follows the browser, switchable). Code, comments
and documentation are English.

## Features

- **Fonts**: 14 bundled outline fonts (OFL / Apache) — variable ones with an adjustable stroke
  weight (thin by default for single-line laying, bold for outlines) — 5 Hershey single-stroke
  fonts, or your own `.ttf` / `.otf` / `.jhf`. The picker renders every font.
- **Laying modes**
  - *Outline (double)* – the strip runs along the inside of every letter outline.
  - *Shape (single)* – the strip follows the stroke centre line.
- **Bend radius everywhere**: real corners become arcs of the minimum radius, spots that stay
  too tight are marked; optional automatic smoothing with its own radius and deviation limit.
  Behind the plate the strip keeps its direction of travel and follows the shortest route with
  the minimum turning radius (Dubins path), staying on the plate and avoiding crossings.
- **Hidden transitions**: every change between pieces happens behind the plate (through a hole,
  or with cable). Dots of i / j / ä / ö / ü, counters and multi-part letters are listed;
  umlaut dots can be laid as one horizontal bar.
- **Lengths**: front, behind the plate, passes through the plate, cut list rounded to the cut
  pitch, automatic split when a roll is too short.
- **Frame**: optional rectangular frame (bent corners or four straight pieces).
- **Recessed strips**: grooves, or through cuts for laser / jigsaw. Parts that would fall out
  (inside of o, a, e, D, a frame …) are held by bridges. A bridge is material, so the strip is
  split there and passes behind the board — a closed "D" becomes bowl + stem.
- **Views**: front, mirrored back, simulated result without the font, cut-outs; dimensions,
  zoom slider.
- **Path editor**: paths become splines with few control points (an "o" needs about four).
  Points are round or corners, segments curves or straight lines — via hover menu or
  double-click (icons with tooltips). Every edit can be undone / redone (Ctrl+Z, Ctrl+Shift+Z).
  Lengths, holes and routing are recomputed.
- **Save / load**: JSON file (incl. an uploaded font), share code or link.
- **PDF**: overview & cut list, 1:1 front laying plan, 1:1 mirrored back routing, with
  registration crosses, glue areas and a 100 mm check scale.

## Architecture

There is no backend: the page is static and serves everything itself (fonts, Pyodide runtime
with numpy / shapely / fontTools), so it runs on GitHub Pages.

```
python/neonplan/          Python core (CPython and Pyodide)
  fonts.py                font loading (fontTools, variable weights, Hershey), text layout
  graph.py                medial axis, pruning, straight strokes, decomposition into pieces
  paths.py                resampling, corner filleting, bend radius checks, smoothing
  dubins.py               minimum-radius routes behind the plate
  routing.py              piece order, holes, links, cut groups
  cutout.py               channels and bridges for recessed strips
  api.py                  compute() / make_pdf() entry points
  pdf.py, pdfwriter.py    printable templates (dependency-free PDF writer)
  i18n.py                 German / English texts for messages and PDF
  __main__.py             command line interface
python/tests/             pytest suite

src/
  App.vue                 mounts the single view
  views/PlannerView.vue   page: settings sidebar, preview, results
  views/plannerview/      the parts of that page
    settings/             one component per settings section
    preview/              toolbar, zoom, editor bar, point menu, legend, SVG preview
    results/              messages, key figures, tables
  components/             reusable building blocks, grouped by kind
    button/ input/ container/ layout/ display/
  composables/            state and behaviour (settings, fonts, planner, editor, share, pdf …)
  util/                   worker bridge, editor geometry, undo history, share codes, i18n setup
  locales/                de.json, en.json (vue-i18n)
  worker.js               Web Worker hosting Pyodide; Python sources are bundled at build time
```

Single-line mode in short: medial axis from a Voronoi diagram of the outline; corner branches
pruned by how far they reach beyond their junction; free ends rebuilt with the curvature of the
stroke; inside straight strokes the path snaps onto the exact centre line between the two
parallel outline edges; at a junction only the longest nearly straight pair passes through.

## Development

The project uses a Nix shell via direnv (`.envrc` → `use nix`, see `shell.nix`):

```sh
direnv allow                      # or: nix-shell
npm install
python scripts/fetch_pyodide.py   # serve Pyodide locally (otherwise the CDN is used)
npm run dev                       # http://localhost:5173
npm test                          # unit tests (vitest) and Python tests (pytest)
npm run lint                      # ESLint (Vue) + Ruff
node scripts/e2e.mjs              # browser end-to-end test against the dev server
```

Command line usage of the core:

```sh
PYTHONPATH=python python -m neonplan "Hallo" --font public/fonts/pacifico.ttf \
    --mode contour --cap-height 150 --strip-width 7 --bend-radius 30 --paper A3 -o hallo.pdf
```

`python scripts/prepare_fonts.py` regenerates the bundled fonts from google/fonts.

## Deployment

`.github/workflows/pages.yml` lints, runs the tests, fetches Pyodide, builds with Vite and
deploys `dist/` to GitHub Pages. Enable *Settings → Pages → Source: GitHub Actions*.

## Licences

Bundled fonts are licensed under the SIL Open Font License (`public/fonts/OFL.txt`) or
Apache 2.0 (Yellowtail, `public/fonts/APACHE.txt`). Hershey fonts are public domain.
