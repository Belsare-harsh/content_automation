#!/usr/bin/env python3
"""Step 5 with an art style (first style: risograph). Same rules as design.py, rendered as a printed look.

Claude writes a short page plan (which scene each beat gets); the style renderer draws the art and prints the words
in a separate pass, then this tool turns the renderer's text layout into design.json, so the same step 5 checks run.

  styled_design.py from-script SCRIPT.json PLAN.json OUT_DIR
  styled_design.py build RUN PLAN.json                 engine run; needs handoff.json from step 4

PLAN.json: {"style": "risograph", "pages": [{"beat": "B01", "scene": "morning"}, {"beat": "B02", "scene": "windows", "highlight": "999.87 lakh"}, ...]}
Scenes for risograph: morning, windows, noon, sheets, tower, overprint, dusk (see tools/styles/risograph/page.html).

Outputs in OUT_DIR: P0n-art.png (art only, for co-branding), P0n-final.png (art + printed type), design.json, fabric.json.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design as D  # noqa: E402
import validators as V  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STYLES = Path(__file__).resolve().parent / "styles"
STYLE_INFO = {"risograph": {"paper": "#F4EEE2", "ink": "#3D5588", "logo": [757, 70, 237, 94]}}


def content_for(script: dict, plan: dict, slot: str) -> dict:
    beats = {b["id"]: b for b in script["beats"]}
    pages = []
    for i, p in enumerate(plan["pages"], 1):
        b = beats[p["beat"]]
        hl = p.get("highlight")
        if hl is None and b["kind"] in ("point", "proof"):
            hl = D.figure_of(b["text"])
        pages.append({"id": f"P{i:02d}", "beat": b["id"], "kind": b["kind"], "scene": p["scene"], "text": b["text"],
                      **({"highlight": hl} if hl else {})})
    return {"slot": slot, "pages": pages}


def to_design(content: dict, layout: list, style: str, script_sha: str, brand: dict) -> dict:
    info = STYLE_INFO[style]
    pages = []
    for p, l in zip(content["pages"], layout):
        x, y, w, h = info["logo"]
        layers = [{"id": f'{p["id"]}-bg', "role": "background", "kind": "rect", "x": 0, "y": 0, "w": 1080, "h": 1350, "fill": info["paper"]},
                  {"id": f'{p["id"]}-logo', "role": "logo_slot", "kind": "rect", "x": x, "y": y, "w": w, "h": h, "fill": "none",
                   "stroke": info["ink"], "placeholder": "{{DISTRIBUTOR_LOGO}}"}]
        for i, t in enumerate(l["layout"]):
            layers.append({"id": f'{p["id"]}-{t["role"]}-{i}', "kind": "text", "font_key": "body",
                           **{k: t[k] for k in ("role", "text", "lines", "x", "y", "w", "h", "font_size", "font_weight",
                                                "font_family", "line_height", "color", "align", "beat_id")}})
        pages.append({"id": p["id"], "beat_ids": [p["beat"]], "w": 1080, "h": 1350, "layers": layers,
                      "art": f'{p["id"]}-art.png', "final": f'{p["id"]}-final.png', "scene": p["scene"]})
    return {"format": "carousel", "style": style, "script_sha256": script_sha, "brand_status": brand.get("status"),
            "canvas": {"w": 1080, "h": 1350}, "pages": pages}


def to_fabric(design: dict) -> dict:
    """Art PNG as a locked background image; words as text layers (only the disclosure is editable, at co-branding)."""
    out = D.to_fabric([{**p, "layers": [l for l in p["layers"] if l["role"] != "background"]} for p in design["pages"]])
    for fp, p in zip(out["pages"], design["pages"]):
        fp["canvas"]["backgroundImage"] = {"type": "Image", "src": p["art"], "left": 0, "top": 0, "selectable": False}
    return out


def build(script: dict, plan: dict, out_dir: Path, config_dir: Path, script_sha: str) -> tuple[dict, list]:
    style = plan.get("style", "risograph")
    if script["format"] != "carousel":
        raise SystemExit("The risograph style is built for carousels so far (1080 x 1350).")
    renderer = STYLES / style / "render.mjs"
    if not renderer.exists():
        raise SystemExit(f"No renderer for style '{style}'.")
    brand = V.load_yaml(config_dir, "brand.yaml")
    slot = (V.load_yaml(config_dir, "compliance-rules.yaml").get("sebi_disclosure") or {}).get("slot_text", "")
    content = content_for(script, plan, slot)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "content.json").write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")
    subprocess.run(["node", str(renderer), str(out_dir / "content.json"), str(out_dir)], check=True, cwd=renderer.parent)
    layout = json.loads((out_dir / "layout.json").read_text())
    design = to_design(content, layout, style, script_sha, brand)
    (out_dir / "design.json").write_text(json.dumps(design, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "fabric.json").write_text(json.dumps(to_fabric(design), ensure_ascii=False, indent=1), encoding="utf-8")
    findings = V.check_design_data(design, script, config_dir, script_sha)
    return design, findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-dir", default=str(ROOT / "runs"))
    ap.add_argument("--config-dir", default=str(ROOT / "config"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("build"); s.add_argument("run"); s.add_argument("plan")
    s = sub.add_parser("from-script"); s.add_argument("script"); s.add_argument("plan"); s.add_argument("out")
    a = ap.parse_args(argv)
    cfg = Path(a.config_dir)
    plan = V.load_json(Path(a.plan))
    if a.cmd == "build":
        rd = Path(a.runs_dir) / a.run
        if not (rd / "handoff.json").exists():
            raise SystemExit("Step 4 is not signed off (no handoff.json). Design starts only after Gate 4.")
        sp, out = rd / "04_script" / "script.json", rd / "05_design"
    else:
        sp, out = Path(a.script), Path(a.out)
    design, findings = build(V.load_json(sp), plan, out, cfg, V.sha256_file(sp))
    for f in findings:
        print(f"{f.level.upper():5} {f.code} {f.where}: {f.message}")
    print(f"Built {len(design['pages'])} {design['style']} page(s). Look at every P0n-final.png at full size before asking for Gate 5.")


if __name__ == "__main__":
    main()
