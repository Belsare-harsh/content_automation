#!/usr/bin/env python3
"""Step 5: Design & visuals. Turns an approved script into page designs.

The script is the only source of words. Every text layer on a page is either:
  script      the exact text of one beat
  highlight   a figure copied out of that same beat (for emphasis)
  disclosure  the SEBI placeholder text from compliance-rules.yaml, filled at co-branding
No other text is ever placed. The logo slot is an empty box, filled per distributor at co-branding.

Outputs, in <run>/05_design/:
  design.json   layout spec (pages and layers) that the checks read, and that Figma and Remotion use
  fabric.json   the same pages as Fabric.js canvases for the Cobranding Studio
  previews/     PNG of each page, for the human reviewing Gate 5

  design.py build RUN                         engine run; needs handoff.json from step 4
  design.py from-script SCRIPT.json OUT_DIR   any script file (used for console runs)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validators as V  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIG = re.compile(r"₹?\d[\d,]*(?:\.\d+)?\s?(?:%|lakh crore|crore|lakh)?")


# ------------------------------------------------------------------ text fitting

def _font(spec: dict, size: int):
    return ImageFont.truetype(spec["file"], size)


def wrap(text: str, spec: dict, size: int, width: int) -> list[str]:
    f = _font(spec, size)
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if f.getlength(trial) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(text: str, spec: dict, box_w: int, box_h: int, start: int, minimum: int, line_h: float = 1.25):
    """Largest font size at which the wrapped text fits the box. Returns (size, lines, used_height)."""
    size = start
    while size >= minimum:
        lines = wrap(text, spec, size, box_w)
        f = _font(spec, size)
        widest = max(f.getlength(l) for l in lines)
        h = int(len(lines) * size * line_h)
        if h <= box_h and widest <= box_w:
            return size, lines, h
        size -= 2
    lines = wrap(text, spec, minimum, box_w)
    return minimum, lines, int(len(lines) * minimum * line_h)


def figure_of(text: str) -> str | None:
    """The most prominent figure in a beat (percent first, then rupee amounts, then dates are skipped)."""
    hits = [m.group(0).strip() for m in FIG.finditer(text)]
    hits = [h for h in hits if not re.fullmatch(r"\d{4}", h)]          # a bare year is not a highlight
    for pref in ("%", "₹", "crore", "lakh"):
        for h in hits:
            if pref in h:
                return h
    return None


# ------------------------------------------------------------------ layout

def layer(id_, role, kind, x, y, w, h, **kw):
    return {"id": id_, "role": role, "kind": kind, "x": int(x), "y": int(y), "w": int(w), "h": int(h), **kw}


def text_layer(id_, role, text, spec, color, x, y, w, h, start, minimum, align="left", beat_id=None):
    size, lines, used = fit(text, spec, w, h, start, minimum)
    return layer(id_, role, "text", x, y, w, used, text=text, lines=lines, font_family=spec["family"],
                 font_weight=spec["weight"], font_size=size, line_height=1.25, color=color, align=align,
                 font_key=[k for k, v in BRAND_FONTS.items() if v is spec][0], beat_id=beat_id)


BRAND_FONTS: dict = {}


def build_pages(script: dict, fmt: str, brand: dict, slot_text: str) -> list[dict]:
    global BRAND_FONTS
    BRAND_FONTS = brand["fonts"]
    C, F = brand["colors"], brand["fonts"]
    cw, ch = brand["canvas"][fmt]["w"], brand["canvas"][fmt]["h"]
    m = int(min(cw, ch) * brand["margin"])
    beats = script["beats"]
    disclosure = next((b for b in beats if b["kind"] == "disclosure"), None)
    content = [b for b in beats if b["kind"] not in ("disclosure",)]
    strip_h = int(ch * 0.055)

    def frame(pid, n_total, idx, with_disclosure):
        layers = [layer(f"{pid}-bg", "background", "rect", 0, 0, cw, ch, fill=C["background"])]
        lw, lh = int(cw * brand["logo_slot"]["w"]), int(ch * brand["logo_slot"]["h"])
        layers.append(layer(f"{pid}-logo", "logo_slot", "rect", cw - m - lw, m, lw, lh, fill="none", stroke=C["muted"],
                            dash=True, placeholder="{{DISTRIBUTOR_LOGO}}"))
        layers.append(layer(f"{pid}-progress", "progress", "rect", m, m + lh // 2 - 4, int((cw - 2 * m - lw - m) * (idx + 1) / n_total), 8,
                            fill=C["accent"]))
        if with_disclosure and disclosure:
            layers.append(layer(f"{pid}-strip", "disclosure_bg", "rect", 0, ch - strip_h, cw, strip_h, fill=C["strip_bg"]))
            t = text_layer(f"{pid}-disclosure", "disclosure", disclosure["text"], F["small"], C["strip_ink"], m, ch - strip_h + strip_h // 4,
                           cw - 2 * m, strip_h // 2, int(strip_h * 0.38), 14, "center", disclosure["id"])
            layers.append(t)
        return layers

    pages = []
    if fmt == "one_pager":
        pid = "P01"
        body_w = cw - 2 * m
        bottom = ch - strip_h - m

        def lay(k):
            L = frame(pid, 1, 0, bool(disclosure))
            y = m + int(ch * 0.11)
            gap = int(m * 0.55 * k)
            for b in content:
                if b["kind"] == "hook":
                    t = text_layer(f"{pid}-{b['id']}", "script", b["text"], F["heading"], C["ink"], m, y, body_w, int(ch * 0.2), int(64 * k), 34, "left", b["id"])
                    L.append(t); y += t["h"] + int(m * 0.5)
                    L.append(layer(f"{pid}-rule", "rule", "rect", m, y, int(body_w * 0.18), 8, fill=C["accent"])); y += int(m * 0.7)
                elif b["kind"] == "recap":
                    pad = int(m * 0.4)
                    t = text_layer(f"{pid}-{b['id']}", "script", b["text"], F["heading"], C["ink"], m + pad, y + pad, body_w - 2 * pad, int(ch * 0.2), int(34 * k), 22, "left", b["id"])
                    L.append(layer(f"{pid}-{b['id']}-box", "panel", "rect", m, y, body_w, t["h"] + 2 * pad, fill=C["panel"], radius=18))
                    L.append(t); y += t["h"] + 2 * pad + gap
                else:
                    t = text_layer(f"{pid}-{b['id']}", "script", b["text"], F["body"], C["ink"], m + 28, y, body_w - 28, int(ch * 0.2), int(30 * k), 20, "left", b["id"])
                    L.append(layer(f"{pid}-{b['id']}-bar", "rule", "rect", m, y + 6, 8, max(t["h"] - 12, 20), fill=C["accent"]))
                    L.append(t); y += t["h"] + gap
            return L, y

        k = 1.8
        L, y = lay(k)
        while y > bottom and k > 0.7:
            k -= 0.05
            L, y = lay(k)
        pages.append({"id": pid, "beat_ids": [b["id"] for b in content], "w": cw, "h": ch, "layers": L})
        return pages

    total = len(content)
    for i, b in enumerate(content):
        pid = f"P{i + 1:02d}"
        on = brand["disclosure_placement"] == "every_page" or i == 0
        L = frame(pid, total, i, on)
        top = m + int(ch * brand["logo_slot"]["h"]) + m
        bottom = (ch - strip_h if on and disclosure else ch) - m
        box_w = cw - 2 * m
        fig = figure_of(b["text"]) if b["kind"] in ("point", "proof") else None
        if b["kind"] == "hook":
            t = text_layer(f"{pid}-{b['id']}", "script", b["text"], F["heading"], C["ink"], m, top, box_w, bottom - top, int(cw * 0.085), 36, "left", b["id"])
            t["y"] = top + (bottom - top - t["h"]) // 2
            L.append(t)
            L.append(layer(f"{pid}-rule", "rule", "rect", m, t["y"] - 40, int(box_w * 0.18), 10, fill=C["accent"]))
        elif b["kind"] == "recap":
            pad = int(m * 0.6)
            t = text_layer(f"{pid}-{b['id']}", "script", b["text"], F["heading"], C["ink"], m + pad, top, box_w - 2 * pad, bottom - top - 2 * pad, int(cw * 0.06), 28, "left", b["id"])
            y = top + (bottom - top - t["h"] - 2 * pad) // 2
            t["y"] = y + pad
            L.append(layer(f"{pid}-{b['id']}-box", "panel", "rect", m, y, box_w, t["h"] + 2 * pad, fill=C["panel"], radius=24))
            L.append(t)
        else:
            y = top
            if fig:
                hs = int(cw * 0.16)
                h = text_layer(f"{pid}-fig", "highlight", fig, F["heading"], C["accent"], m, y, box_w, int(hs * 1.3), hs, 48, "left", b["id"])
                L.append(h); y += h["h"] + int(m * 0.5)
            t = text_layer(f"{pid}-{b['id']}", "script", b["text"], F["body"], C["ink"], m, y, box_w, bottom - y, int(cw * 0.06), 28, "left", b["id"])
            if not fig:
                t["y"] = top + (bottom - top - t["h"]) // 2
            L.append(t)
        pages.append({"id": pid, "beat_ids": [b["id"]], "w": cw, "h": ch, "layers": L,
                      "visual_note": b.get("visual_note", "")})
    return pages


# ------------------------------------------------------------------ exporters

def to_fabric(pages: list[dict]) -> dict:
    out = []
    for p in pages:
        objs = []
        for l in p["layers"]:
            base = {"left": l["x"], "top": l["y"], "originX": "left", "originY": "top", "name": l["id"],
                    "data": {"role": l["role"], "beat_id": l.get("beat_id")}}
            if l["kind"] == "rect":
                objs.append({**base, "type": "Rect", "width": l["w"], "height": l["h"],
                             "fill": "transparent" if l.get("fill") == "none" else l["fill"],
                             "stroke": l.get("stroke"), "strokeWidth": 3 if l.get("stroke") else 0,
                             "strokeDashArray": [14, 10] if l.get("dash") else None,
                             "rx": l.get("radius", 0), "ry": l.get("radius", 0),
                             "selectable": l["role"] == "logo_slot",
                             **({"data": {**base["data"], "placeholder": l["placeholder"]}} if l.get("placeholder") else {})})
            else:
                objs.append({**base, "type": "Textbox", "text": l["text"], "width": l["w"], "fontSize": l["font_size"],
                             "fontFamily": l["font_family"], "fontWeight": l["font_weight"], "fill": l["color"],
                             "textAlign": l["align"], "lineHeight": l["line_height"], "splitByGrapheme": False,
                             "editable": l["role"] == "disclosure", "lockMovementX": True, "lockMovementY": True})
        out.append({"id": p["id"], "width": p["w"], "height": p["h"], "canvas": {"version": "6.0.0", "objects": objs}})
    return {"generator": "finpedia-content-engine step 5", "pages": out}


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def render_png(page: dict, brand: dict, path: Path, scale: float = 0.5):
    img = Image.new("RGB", (page["w"], page["h"]), _hex(brand["colors"]["background"]))
    d = ImageDraw.Draw(img)
    for l in page["layers"]:
        if l["kind"] == "rect":
            box = [l["x"], l["y"], l["x"] + l["w"], l["y"] + l["h"]]
            if l.get("fill") not in (None, "none"):
                d.rounded_rectangle(box, radius=l.get("radius", 0), fill=_hex(l["fill"]))
            if l.get("stroke"):
                x0, y0, x1, y1 = box
                col = _hex(l["stroke"])
                for x in range(x0, x1, 24):
                    d.line([(x, y0), (min(x + 12, x1), y0)], fill=col, width=3); d.line([(x, y1), (min(x + 12, x1), y1)], fill=col, width=3)
                for y in range(y0, y1, 24):
                    d.line([(x0, y), (x0, min(y + 12, y1))], fill=col, width=3); d.line([(x1, y), (x1, min(y + 12, y1))], fill=col, width=3)
                f = ImageFont.truetype(brand["fonts"]["small"]["file"], max(14, l["h"] // 4))
                d.text(((x0 + x1) / 2, (y0 + y1) / 2), "logo", fill=col, font=f, anchor="mm")
        else:
            f = ImageFont.truetype(brand["fonts"][l["font_key"]]["file"], l["font_size"])
            lh = l["font_size"] * l["line_height"]
            for i, line in enumerate(l["lines"]):
                y = l["y"] + i * lh
                if l["align"] == "center":
                    d.text((l["x"] + l["w"] / 2, y), line, fill=_hex(l["color"]), font=f, anchor="ma")
                else:
                    d.text((l["x"], y), line, fill=_hex(l["color"]), font=f)
    if scale != 1:
        img = img.resize((int(page["w"] * scale), int(page["h"] * scale)), Image.LANCZOS)
    img.save(path)


# ------------------------------------------------------------------ build

def build(script: dict, fmt: str, out_dir: Path, config_dir: Path, script_sha: str, previews: bool = True) -> dict:
    brand = V.load_yaml(config_dir, "brand.yaml")
    if fmt not in brand["canvas"]:
        raise SystemExit(f"No canvas size for format '{fmt}' in brand.yaml.")
    slot = (V.load_yaml(config_dir, "compliance-rules.yaml").get("sebi_disclosure") or {}).get("slot_text", "")
    pages = build_pages(script, fmt, brand, slot)
    out_dir.mkdir(parents=True, exist_ok=True)
    design = {"format": fmt, "script_sha256": script_sha, "brand_status": brand.get("status"),
              "canvas": brand["canvas"][fmt], "pages": pages}
    (out_dir / "design.json").write_text(json.dumps(design, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "fabric.json").write_text(json.dumps(to_fabric(pages), indent=2, ensure_ascii=False), encoding="utf-8")
    if previews:
        pv = out_dir / "previews"
        pv.mkdir(exist_ok=True)
        for p in pages:
            render_png(p, brand, pv / f"{p['id']}.png")
    return design


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-dir", default=str(ROOT / "runs"))
    ap.add_argument("--config-dir", default=str(ROOT / "config"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("build"); s.add_argument("run")
    s = sub.add_parser("from-script"); s.add_argument("script"); s.add_argument("out")
    a = ap.parse_args(argv)
    cfg = Path(a.config_dir)
    if a.cmd == "build":
        rd = Path(a.runs_dir) / a.run
        if not (rd / "handoff.json").exists():
            raise SystemExit("Step 4 is not signed off (no handoff.json). Design starts only after Gate 4.")
        sp = rd / "04_script" / "script.json"
        script = V.load_json(sp)
        d = build(script, script["format"], rd / "05_design", cfg, V.sha256_file(sp))
    else:
        sp = Path(a.script)
        script = V.load_json(sp)
        d = build(script, script["format"], Path(a.out), cfg, V.sha256_file(sp))
    print(f"Built {len(d['pages'])} page(s) for {d['format']}. Run the step 5 checks before asking for Gate 5.")


if __name__ == "__main__":
    main()
