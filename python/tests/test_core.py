"""Tests for the neonplan core (run with `pytest` inside the nix shell)."""

import math
import re

import numpy as np
import pytest
from conftest import FONTS
from neonplan import api, paths
from neonplan.dubins import dubins, dubins_length
from neonplan.fonts import OutlineFont, layout_text


def font(name):
    return (FONTS / name).read_bytes()


# ----------------------------------------------------------------------------- fonts


def test_cap_height_and_width_scale():
    f = OutlineFont.from_bytes(font("bebas.ttf"))
    lay = layout_text(f, "outline", "H", 100)
    x0, y0, x1, y1 = lay.geometry.bounds
    assert y1 - y0 == pytest.approx(100, rel=0.01)
    wide = layout_text(f, "outline", "H", 100, width_scale=1.5).geometry.bounds
    assert (wide[2] - wide[0]) == pytest.approx(1.5 * (x1 - x0), rel=0.01)


def test_missing_characters_are_reported():
    res = api.compute({"text": "A☃B"}, font("bebas.ttf"))
    assert res["ok"] and any("☃" in w for w in res["warnings"])


# ----------------------------------------------------------------------------- paths


def test_fillet_creates_requested_radius():
    square = np.array([[0, 0], [200, 0], [200, 200], [0, 200]], float)
    p = paths.resample(paths.fillet(square, 30, True), 1.0, True)
    r = paths.local_radius(p, True, 5)
    assert r.min() == pytest.approx(30, rel=0.08)
    # perimeter of a rounded square: 4 straight parts + one full circle
    assert paths.length(p, True) == pytest.approx(4 * (200 - 60) + 2 * math.pi * 30, rel=0.01)


def test_smoothing_never_tightens_bends():
    # an arc of radius 40 must keep (about) its radius, i.e. not be pulled inwards
    t = np.linspace(0, math.pi, 80)
    arc = np.column_stack([40 * np.cos(t), 40 * np.sin(t)])
    out = paths.smooth_path(arc, 30, False)
    r = paths.local_radius(out, False, 5)[8:-8]
    assert r.min() > 38


def test_auto_smooth_is_opt_in_and_marks_spots():
    plain = api.compute({"text": "Hallo", "mode": "contour"}, font("pacifico.ttf"))
    smooth = api.compute({"text": "Hallo", "mode": "contour", "auto_smooth": True}, font("pacifico.ttf"))
    assert plain["summary"]["smoothed"] == 0
    assert smooth["summary"]["smoothed"] > 0
    assert smooth["summary"]["violations"] < plain["summary"]["violations"]


# ----------------------------------------------------------------------------- dubins


@pytest.mark.parametrize("seed", range(5))
def test_dubins_reaches_target_with_heading(seed):
    rng = np.random.default_rng(seed)
    for _ in range(100):
        p0, p1 = rng.uniform(-100, 100, 2), rng.uniform(-100, 100, 2)
        h0, h1 = rng.uniform(0, 2 * math.pi, 2)
        L, pts = dubins(tuple(p0), h0, tuple(p1), h1, 30)
        assert np.allclose(pts[-1], p1, atol=0.6)
        assert np.linalg.norm(p1 - p0) - 1e-6 <= L
        assert pytest.approx(dubins_length(tuple(p0), h0, tuple(p1), h1, 30), rel=1e-6) == L


# ----------------------------------------------------------------------------- skeleton / single mode


def test_f_keeps_both_crossbar_arms():
    res = api.compute({"text": "f", "mode": "single", "cap_height": 150}, font("fredoka.ttf"))
    xs = np.vstack([np.asarray(p["pts"]) for p in res["pieces"]])[:, 0]
    letter = np.vstack([np.asarray(r) for poly in res["letters"] for r in poly])[:, 0]
    # strip covers nearly the full width of the letter (both crossbar arms present)
    assert (xs.max() - xs.min()) > 0.75 * (letter.max() - letter.min())


def test_round_stroke_ends_produce_no_splinters():
    res = api.compute({"text": "t", "mode": "single"}, font("quicksand.ttf"))
    assert all(p["length"] > 10 for p in res["pieces"])
    assert len(res["pieces"]) <= 3


def test_dots_and_umlauts():
    dots = api.compute({"text": "ä", "mode": "single"}, font("montserrat.ttf"))
    bar = api.compute({"text": "ä", "mode": "single", "umlaut_style": "bar"}, font("montserrat.ttf"))
    omit = api.compute({"text": "ä", "mode": "single", "dot_mode": "omit"}, font("montserrat.ttf"))
    assert sum(p["role"] == "dot" for p in dots["pieces"]) == 2
    assert sum(p["role"] == "dot" for p in bar["pieces"]) == 1
    assert sum(p["role"] == "dot" for p in omit["pieces"]) == 0 and len(omit["omitted"]) == 2
    assert dots["hidden"] and "Umlaut" in dots["hidden"][0]["reason"]


def test_hershey_i_dot_detected():
    res = api.compute({"text": "i", "font_kind": "hershey", "mode": "single"}, font("h-futural.jhf"))
    assert [p["role"] for p in res["pieces"]].count("dot") == 1


# ----------------------------------------------------------------------------- lengths & routing


def test_back_side_is_part_of_strip_length():
    res = api.compute({"text": "Hi", "connection": "strip", "cut_unit": 0}, font("bebas.ttf"))
    s = res["summary"]
    assert s["back_strip"] > 0
    assert s["strip_cut_total"] == pytest.approx(s["front"] + s["back_strip"], abs=1.0)
    for link in res["links"]:
        if link["kind"] == "strip":  # route behind the plate is never shorter than the straight line
            assert link["distance"] >= math.dist(link["a"], link["b"]) - 1e-6


def test_back_routes_respect_bend_radius():
    res = api.compute({"text": "Hi", "bend_radius": 30}, font("bebas.ttf"))
    for link in res["links"]:
        if link["kind"] == "strip" and len(link["path"]) > 5:
            r = paths.local_radius(paths.resample(np.asarray(link["path"]), 1.0, False), False, 4)
            assert r.min() > 27


def test_cut_raster_rounding_and_roll_split():
    res = api.compute({"text": "HELLO WORLD", "cut_unit": 25, "roll_length": 1500}, font("bebas.ttf"))
    assert all(g["cut"] % 25 == 0 and g["cut"] >= g["raw"] for g in res["groups"])
    assert len(res["groups"]) > 1 and any(link["reason"] == "roll" for link in res["links"])


def test_manual_pieces_replace_generated_ones():
    base = api.compute({"text": "Hi"}, font("bebas.ttf"))
    manual = [dict(p) for p in base["pieces"][1:]]
    res = api.compute({"text": "Hi"}, font("bebas.ttf"), manual=manual)
    assert res["manual"] and len(res["pieces"]) == len(base["pieces"]) - 1


# ----------------------------------------------------------------------------- pdf


@pytest.mark.parametrize("paper", ["A4", "A3"])
def test_pdf_is_valid_and_tiled(paper):
    plan = api.compute({"text": "Neon"}, font("pacifico.ttf"))
    pdf = api.make_pdf(plan, paper)
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    count = int(re.search(rb"/Count (\d+)", pdf).group(1))
    assert count >= 3


# ----------------------------------------------------------------------------- frame & cut-outs


def test_frame_round_and_butt():
    r = api.compute({"text": "A", "frame": True, "bend_radius": 30}, font("bebas.ttf"))
    frame = [p for p in r["pieces"] if p["role"] == "frame"]
    assert len(frame) == 1 and frame[0]["closed"] and not frame[0]["violations"]
    b = api.compute({"text": "A", "frame": True, "frame_corners": "butt"}, font("bebas.ttf"))
    assert sum(p["role"] == "frame" for p in b["pieces"]) == 4


@pytest.mark.parametrize("mode,text", [("contour", "Dose"), ("single", "Oa e B")])
def test_through_cut_leaves_no_loose_parts(mode, text):
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union

    r = api.compute({"text": text, "mode": mode, "cut_mode": "through"}, font("fredoka.ttf"))
    cut = r["cut"]
    assert cut["islands"] > 0 and cut["bridges"]
    chan = unary_union([Polygon(p[0], p[1:]).buffer(0) for p in cut["channels"]])
    material = box(0, 0, r["plate"]["w"], r["plate"]["h"]).difference(chan)
    parts = [g for g in getattr(material, "geoms", [material]) if g.area > 1]
    assert len(parts) == 1, f"{len(parts)} separate parts"


def test_bridges_never_carry_a_strip():
    from shapely.geometry import LineString, Polygon

    r = api.compute({"text": "D Oa", "mode": "single", "cut_mode": "through"}, font("fredoka.ttf"))
    bridges = [Polygon(b[0], b[1:]).buffer(-0.5) for b in r["cut"]["bridges"]]
    assert bridges
    for p in r["pieces"]:
        line = LineString(p["pts"] + ([p["pts"][0]] if p["closed"] else []))
        assert not any(line.intersects(b) for b in bridges), "a strip runs over a bridge"


def test_closed_d_is_split_into_two_elements():
    r = api.compute({"text": "D", "mode": "single", "cut_mode": "through"}, font("fredoka.ttf"))
    assert len(r["pieces"]) == 2 and len(r["cut"]["bridges"]) == 2
    assert all(not p["closed"] for p in r["pieces"])


def test_groove_has_no_bridges():
    r = api.compute({"text": "O", "cut_mode": "groove"}, font("fredoka.ttf"))
    assert r["cut"]["mode"] == "groove" and r["cut"]["bridges"] == [] and r["cut"]["depth"] > 0
