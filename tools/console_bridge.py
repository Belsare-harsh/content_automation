#!/usr/bin/env python3
"""Bridge between the Content Review Console's database and the engine tools (used by the cloud worker).

The worker reads console documents with the artifact db tools, saves them as one JSON dump, and uses this tool to
turn them into engine inputs, then turns engine outputs back into console documents.

  console_bridge.py script DUMP.json OUT_SCRIPT.json        console run -> script.json for design.py from-script
  console_bridge.py design-doc DESIGN.json OUT.json          design.json -> runs/<id>/media/design document
  console_bridge.py video-doc VIDEO.json SRC OUT.json        video.json  -> runs/<id>/media/video document

DUMP.json: {"meta": <runs/<id> doc>, "angles": [<angle docs>], "beats": [<beat docs>], "facts": [<fact docs>]}
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _save(p, d):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def script_from_dump(dump: dict) -> dict:
    meta = dump.get("meta") or {}
    gates = meta.get("gates") or {}
    if "G4" not in gates:
        raise SystemExit("Gate 4 is not signed in the console; design may not start.")
    sel = (meta.get("selected") or {}).get("angle")
    angle = next((a for a in dump.get("angles", []) if a.get("id") == sel), None)
    if not angle:
        raise SystemExit("No selected angle in the console run.")
    beats = sorted(dump.get("beats", []), key=lambda b: b["id"])
    if not beats:
        raise SystemExit("The console run has no script beats.")
    fmt = meta.get("format") or angle.get("format") or "carousel"
    fmt = {"ppt": "presentation"}.get(fmt, fmt)
    brief = json.dumps(angle, sort_keys=True, ensure_ascii=False).encode()
    keep = ("id", "kind", "text", "key_point", "fact_ids", "disclaimer_id", "visual_note")
    return {
        "core_message": angle["core_message"],
        "locked_brief_sha256": hashlib.sha256(brief).hexdigest(),
        "format": fmt,
        "beats": [{k: b.get(k) for k in keep if k in b} | {"fact_ids": b.get("fact_ids") or []} for b in beats],
    }


def design_doc(design: dict) -> dict:
    d = dict(design)
    d.setdefault("built_by", "Claude worker (tools/design.py)")
    d["built_on"] = dt.date.today().isoformat()
    d.setdefault("warnings", [])
    if str(d.get("brand_status", "")).startswith("placeholder") and not any("placeholder brand" in w for w in d["warnings"]):
        d["warnings"].append("Designs use the placeholder brand, not TheFinPedia's real assets.")
    return d


def video_doc(video: dict, src: str) -> dict:
    v = dict(video)
    v["src"] = src
    v.setdefault("built_by", "Claude worker (tools/animate.py)")
    v["built_on"] = dt.date.today().isoformat()
    return v


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("script"); s.add_argument("dump"); s.add_argument("out")
    s = sub.add_parser("design-doc"); s.add_argument("design"); s.add_argument("out")
    s = sub.add_parser("video-doc"); s.add_argument("video"); s.add_argument("src"); s.add_argument("out")
    a = ap.parse_args(argv)
    if a.cmd == "script":
        _save(a.out, script_from_dump(_load(a.dump)))
    elif a.cmd == "design-doc":
        _save(a.out, design_doc(_load(a.design)))
    else:
        _save(a.out, video_doc(_load(a.video), a.src))
    print("Wrote", a.out)


if __name__ == "__main__":
    main()
