#!/usr/bin/env python3
"""Step 6: Animation & video (reels and videos only). Renders an MP4 from the approved step 5 design with Remotion.

The video shows only the layers of the approved design, page by page, after an opening SEBI disclosure slate.
Scene length comes from reading time (brand.yaml video settings), so every line stays on screen long enough to read.

Outputs, in <run>/06_animation/:
  props.json    the exact input given to Remotion
  video.mp4     the render
  video.json    manifest the checks read: scenes, their words, timings, and fingerprints of the design and the MP4

  animate.py build RUN                                 engine run; step 5 must be signed (G5)
  animate.py from-design DESIGN.json OUT_DIR           any design file (used for console runs)
  add --no-render to write props.json only
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validators as V  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REMOTION = Path(__file__).resolve().parent / "remotion"


def words_on(page: dict) -> int:
    return sum(len(l["text"].split()) for l in page["layers"] if l["kind"] == "text" and l["role"] in ("script", "highlight"))


def scene_seconds(n_words: int, vid: dict) -> float:
    return min(max(n_words * vid["seconds_per_word"], vid["min_scene_seconds"]), vid["max_scene_seconds"])


def build_props(design: dict, brand: dict) -> dict:
    vid, C = brand["video"], brand["colors"]
    w, h, fps = design["canvas"]["w"], design["canvas"]["h"], vid["fps"]
    scenes = []
    disc = next((l for p in design["pages"] for l in p["layers"] if l["role"] == "disclosure"), None)
    if disc:
        m = int(min(w, h) * brand["margin"])
        size = int(w * 0.04)
        slate = {**disc, "id": "slate-disclosure", "x": m, "y": h // 2 - size, "w": w - 2 * m, "font_size": size,
                 "lines": None, "align": "center"}
        # wrap the placeholder text for the slate
        from design import wrap  # noqa: E402
        slate["lines"] = wrap(disc["text"], brand["fonts"]["small"], size, w - 2 * m)
        slate["h"] = int(len(slate["lines"]) * size * 1.25)
        scenes.append({"id": "S00", "kind": "slate", "durationInFrames": int(vid["disclosure_seconds"] * fps), "page_id": None,
                       "layers": [{"id": "slate-bg", "role": "background", "kind": "rect", "x": 0, "y": 0, "w": w, "h": h, "fill": C["strip_bg"]}, slate]})
    for i, p in enumerate(design["pages"], 1):
        secs = scene_seconds(words_on(p), vid)
        scenes.append({"id": f"S{i:02d}", "kind": "page", "page_id": p["id"], "durationInFrames": int(round(secs * fps)), "layers": p["layers"]})
    return {"width": w, "height": h, "fps": fps, "colors": C, "scenes": scenes}


def manifest(props: dict, design_sha: str, mp4: Path | None) -> dict:
    t, scenes = 0, []
    for s in props["scenes"]:
        scenes.append({"id": s["id"], "kind": s["kind"], "page_id": s.get("page_id"), "start_frame": t, "frames": s["durationInFrames"],
                       "texts": [{"role": l["role"], "text": l["text"]} for l in s["layers"] if l["kind"] == "text"]})
        t += s["durationInFrames"]
    return {"design_sha256": design_sha, "fps": props["fps"], "width": props["width"], "height": props["height"], "total_frames": t,
            "seconds": round(t / props["fps"], 1), "scenes": scenes,
            "mp4": mp4.name if mp4 else None, "mp4_sha256": V.sha256_file(mp4) if mp4 and mp4.exists() else None}


def render(props_path: Path, out: Path):
    if not (REMOTION / "node_modules").exists():
        raise SystemExit("Remotion is not installed. Run: cd tools/remotion && npm i")
    cmd = ["npx", "remotion", "render", "src/index.ts", "FinpediaVideo", str(out.resolve()), f"--props={props_path.resolve()}",
           "--codec=h264", "--crf=20", "--x264-preset=veryfast", "--log=error"]
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if chrome:
        cmd.append(f"--browser-executable={chrome}")
    subprocess.run(cmd, cwd=REMOTION, check=True)


def run(design_path: Path, out_dir: Path, config_dir: Path, do_render: bool = True) -> dict:
    brand = V.load_yaml(config_dir, "brand.yaml")
    design = V.load_json(design_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    props = build_props(design, brand)
    pp = out_dir / "props.json"
    pp.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    mp4 = out_dir / "video.mp4"
    if do_render:
        render(pp, mp4)
    man = manifest(props, V.sha256_file(design_path), mp4 if do_render else None)
    (out_dir / "video.json").write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
    return man


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-dir", default=str(ROOT / "runs"))
    ap.add_argument("--config-dir", default=str(ROOT / "config"))
    ap.add_argument("--no-render", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("build"); s.add_argument("run")
    s = sub.add_parser("from-design"); s.add_argument("design"); s.add_argument("out")
    a = ap.parse_args(argv)
    cfg = Path(a.config_dir)
    if a.cmd == "build":
        rd = Path(a.runs_dir) / a.run
        st = V.load_json(rd / "state.json")
        if 5 not in st.get("done", []):
            raise SystemExit("Step 5 is not signed off (Gate 5). Animation starts only after the design is approved.")
        man = run(rd / "05_design" / "design.json", rd / "06_animation", cfg, not a.no_render)
    else:
        man = run(Path(a.design), Path(a.out), cfg, not a.no_render)
    print(f"{len(man['scenes'])} scenes, {man['seconds']} s. Run the step 6 checks, then a person watches it for Gate 6.")


if __name__ == "__main__":
    main()
