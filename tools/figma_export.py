#!/usr/bin/env python3
"""Step 5, Figma output. Prints a Figma Plugin API script that rebuilds a design.json in a Figma file.

Claude runs the printed script with the Figma connector (use_figma). The script:
  - keeps brand colours as Figma variables in a "Brand" collection (update them there when the real brand arrives),
  - builds the disclosure strip and logo slot once as components and places instances,
  - draws one frame per page, with text layers carrying the beat text exactly and named by layer id.

  figma_export.py DESIGN.json --label "rmwd8ndev" [--x 0] [--y 0]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validators as V  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STYLE = {700: "Bold", 600: "Semi Bold", 500: "Medium", 400: "Regular"}

JS = r"""
const D = __DESIGN__;
const BRAND = __BRAND__;
const LABEL = __LABEL__;
const hex = h => ({r: parseInt(h.slice(1,3),16)/255, g: parseInt(h.slice(3,5),16)/255, b: parseInt(h.slice(5,7),16)/255});
await Promise.all(["Bold","Medium","Regular"].map(s => figma.loadFontAsync({family: "Inter", style: s})));

// Brand colour variables (one collection, reused across runs)
const cols = await figma.variables.getLocalVariableCollectionsAsync();
let coll = cols.find(c => c.name === "Brand");
if (!coll) coll = figma.variables.createVariableCollection("Brand");
const existing = (await figma.variables.getLocalVariablesAsync("COLOR")).filter(v => v.variableCollectionId === coll.id);
const vars = {};
for (const [k, h] of Object.entries(BRAND.colors)) {
  let v = existing.find(x => x.name === "color/" + k);
  if (!v) { v = figma.variables.createVariable("color/" + k, coll, "COLOR"); v.scopes = k.endsWith("ink") || k === "ink" || k === "muted" || k === "accent" ? ["TEXT_FILL", "SHAPE_FILL", "FRAME_FILL", "STROKE_COLOR"] : ["FRAME_FILL", "SHAPE_FILL"]; }
  v.setValueForMode(coll.modes[0].modeId, {...hex(h), a: 1});
  if (!vars[h.toUpperCase()]) vars[h.toUpperCase()] = v;  // first role wins when two roles share a colour
}
const paint = h => { const v = vars[(h||"").toUpperCase()]; const p = {type: "SOLID", color: hex(h)}; return v ? figma.variables.setBoundVariableForPaint(p, "color", v) : p; };

// Shared components for this canvas size
const W = D.canvas.w, H = D.canvas.h;
const sample = D.pages[0].layers;
const stripL = sample.find(l => l.role === "disclosure_bg"), discL = sample.find(l => l.role === "disclosure"), logoL = sample.find(l => l.role === "logo_slot");
const compPage = figma.currentPage;
let maxX = 0; for (const c of compPage.children) maxX = Math.max(maxX, c.x + c.width);
const created = [];
function findComp(name) { return compPage.findAllWithCriteria({types: ["COMPONENT"]}).find(c => c.name === name); }
let strip = null;
if (stripL && discL) {
  const name = `Disclosure strip / ${W}`;
  strip = findComp(name);
  if (!strip) {
    strip = figma.createComponent(); strip.name = name; strip.resize(W, stripL.h); strip.fills = [paint(stripL.fill)];
    strip.description = "SEBI disclosure strip. Placeholders are filled per distributor at co-branding. Never type real names here.";
    const t = figma.createText(); t.name = "disclosure"; t.fontName = {family: "Inter", style: "Regular"}; t.characters = discL.text;
    t.fontSize = discL.font_size; t.fills = [paint(discL.color)]; t.textAlignHorizontal = "CENTER";
    t.resize(discL.w, t.height); t.textAutoResize = "HEIGHT"; t.x = discL.x; t.y = discL.y - stripL.y;
    strip.appendChild(t); strip.x = maxX + 200; strip.y = -400; created.push(strip.id);
  }
}
let logo = null;
if (logoL) {
  const name = `Logo slot / ${logoL.w}x${logoL.h}`;
  logo = findComp(name);
  if (!logo) {
    logo = figma.createComponent(); logo.name = name; logo.resize(logoL.w, logoL.h); logo.fills = [];
    logo.strokes = [paint(logoL.stroke)]; logo.strokeWeight = 3; logo.dashPattern = [14, 10];
    logo.description = "Distributor logo, placed at co-branding (step 9). Leave empty.";
    logo.x = maxX + 200 + W + 100; logo.y = -400; created.push(logo.id);
  }
}

// One frame per page
const frames = [];
let x = maxX + 200;
for (const p of D.pages) {
  const f = figma.createFrame(); f.name = `${LABEL} / ${p.id}`; f.resize(p.w, p.h); f.x = x; f.y = 0; f.clipsContent = true; f.fills = [];
  for (const l of p.layers) {
    if (l.role === "disclosure_bg" || l.role === "disclosure" || l.role === "logo_slot") continue;
    if (l.kind === "rect") {
      if (l.role === "background") { f.fills = [paint(l.fill)]; continue; }
      const r = figma.createRectangle(); r.name = l.id; r.resize(Math.max(1, l.w), Math.max(1, l.h)); r.x = l.x; r.y = l.y;
      r.fills = l.fill && l.fill !== "none" ? [paint(l.fill)] : []; if (l.radius) r.cornerRadius = l.radius; f.appendChild(r);
    } else {
      const t = figma.createText(); t.name = l.id + (l.role === "script" ? " · " + l.beat_id : "");
      t.fontName = {family: "Inter", style: __STYLE__[l.font_weight] || "Regular"}; t.characters = l.text;
      t.fontSize = l.font_size; t.lineHeight = {unit: "PIXELS", value: l.font_size * l.line_height};
      t.fills = [paint(l.color)]; t.textAlignHorizontal = l.align === "center" ? "CENTER" : "LEFT";
      if (l.role === "highlight") {  // one line; shrink to fit the column (Figma's Inter can run wider than the preview font)
        t.textAutoResize = "WIDTH_AND_HEIGHT"; let fs = l.font_size;
        while (t.width > l.w && fs > 48) { fs -= 4; t.fontSize = fs; t.lineHeight = {unit: "PIXELS", value: fs * l.line_height}; }
      } else { t.resize(l.w, t.height); t.textAutoResize = "HEIGHT"; }
      t.x = l.x; t.y = l.y; f.appendChild(t);
    }
  }
  if (strip && p.layers.some(l => l.role === "disclosure")) { const i = strip.createInstance(); i.x = 0; i.y = stripL.y; f.appendChild(i); }
  if (logo && p.layers.some(l => l.role === "logo_slot")) { const i = logo.createInstance(); i.x = logoL.x; i.y = logoL.y; f.appendChild(i); }
  frames.push(f.id); x += p.w + 80;
}
// Read back every text layer so the engine can compare it with the approved script
const texts = [];
for (const id of frames) { const f = await figma.getNodeByIdAsync(id); for (const t of f.findAllWithCriteria({types: ["TEXT"]})) texts.push({frame: f.name, name: t.name, text: t.characters}); }
return {createdNodeIds: created.concat(frames), frames, texts};
"""


def script(design: dict, brand: dict, label: str) -> str:
    return (JS.replace("__DESIGN__", json.dumps(design, ensure_ascii=False))
              .replace("__BRAND__", json.dumps({"colors": brand["colors"]}))
              .replace("__LABEL__", json.dumps(label))
              .replace("__STYLE__", json.dumps({str(k): v for k, v in STYLE.items()})))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design"); ap.add_argument("--label", required=True)
    ap.add_argument("--config-dir", default=str(ROOT / "config"))
    a = ap.parse_args(argv)
    d = V.load_json(Path(a.design))
    slim = {"canvas": d["canvas"], "pages": [{"id": p["id"], "w": p["w"], "h": p["h"],
            "layers": [{k: v for k, v in l.items() if k not in ("lines", "font_key", "placeholder", "dash")} for l in p["layers"]]} for p in d["pages"]]}
    print(script(slim, V.load_yaml(Path(a.config_dir), "brand.yaml"), a.label))


if __name__ == "__main__":
    main()
