#!/usr/bin/env python3
"""TheFinPedia content engine, steps 1-6 (7-10 not built yet). Enforces order, checks and named human approvals.

Claude does the drafting work between these commands. This program decides whether the work may move on.

  engine.py new      --topic "..." --mode topic_driven|discovery --by NAME
  engine.py status   RUN
  engine.py check    RUN [STEP]
  engine.py facts    RUN --by NAME [--approve F001,F002] [--reject F003] [--lead-only F004] [--note TEXT]
  engine.py select   RUN --angle A2 --by NAME [--edits TEXT]
  engine.py lock     RUN
  engine.py approve  RUN GATE --by NAME --decision approve|reject [--note TEXT]
  engine.py advance  RUN
  engine.py reopen   RUN --step N --by NAME --note TEXT     (send back to the step that caused a problem)
  engine.py verify-log RUN
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validators as V  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


class EngineError(Exception):
    pass


# ------------------------------------------------------------------ paths and state

class Ctx:
    def __init__(self, runs_dir: Path, config_dir: Path):
        self.runs_dir = Path(runs_dir)
        self.config_dir = Path(config_dir)
        self.gates = V.load_yaml(self.config_dir, "gates.yaml")

    def run_dir(self, run_id: str) -> Path:
        d = self.runs_dir / run_id
        if not (d / "state.json").exists():
            raise EngineError(f"No such run: {run_id}")
        return d

    def state(self, run_id: str) -> dict:
        return V.load_json(self.run_dir(run_id) / "state.json")

    def save_state(self, run_id: str, st: dict):
        (self.run_dir(run_id) / "state.json").write_text(json.dumps(st, indent=2), encoding="utf-8")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def today() -> str:
    return dt.date.today().isoformat()


# ------------------------------------------------------------------ approvals log (hash chained)

def log_path(rd: Path) -> Path:
    return rd / "approvals.jsonl"


def read_log(rd: Path) -> list[dict]:
    p = log_path(rd)
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def _entry_hash(e: dict) -> str:
    body = {k: v for k, v in e.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def append_log(rd: Path, entry: dict) -> dict:
    entries = read_log(rd)
    entry = {"seq": len(entries) + 1, "ts": now(), **entry, "prev_hash": entries[-1]["hash"] if entries else "GENESIS"}
    entry["hash"] = _entry_hash(entry)
    with log_path(rd).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


def verify_log(rd: Path) -> list[str]:
    problems, prev = [], "GENESIS"
    for e in read_log(rd):
        if e["prev_hash"] != prev:
            problems.append(f"entry {e['seq']}: chain broken")
        if _entry_hash(e) != e["hash"]:
            problems.append(f"entry {e['seq']}: content altered")
        prev = e["hash"]
    return problems


# ------------------------------------------------------------------ helpers

def step_info(ctx: Ctx, n: int) -> dict:
    return ctx.gates["steps"][n]


def artifact_hashes(ctx: Ctx, rd: Path, n: int) -> dict:
    info = step_info(ctx, n)
    out = {}
    for a in info["artifacts"]:
        p = rd / info["folder"] / a
        out[f"{info['folder']}/{a}"] = V.sha256_file(p) if p.exists() else None
    return out


def step_applies(ctx: Ctx, rd: Path, n: int) -> bool:
    only = step_info(ctx, n).get("only_for_outputs")
    if not only:
        return True
    fmt = V.load_json(rd / "03_approval" / "locked_brief.json")["format"]
    out = V.load_yaml(ctx.config_dir, "content-types.yaml")["types"].get(fmt, {}).get("output")
    return out in only


def run_checks(ctx: Ctx, rd: Path, n: int) -> list[V.Finding]:
    findings: list[V.Finding] = []
    for name in step_info(ctx, n)["checks"]:
        findings += V.CHECKS[name](run_dir=rd, config_dir=ctx.config_dir)
    return findings


def print_findings(findings):
    if not findings:
        print("  all checks passed")
        return
    for f in findings:
        mark = "BLOCK" if f.level == "block" else "warn "
        print(f"  [{mark}] {f.code:<22} {f.where}: {f.message}" + (f"  -> {f.fix}" if f.fix else ""))


def require_role(ctx: Ctx, name: str, roles: list[str], action: str):
    cfg = V.load_yaml(ctx.config_dir, "approvers.yaml")["roles"]
    allowed = {p for r in roles for p in (cfg.get(r) or [])}
    if not allowed:
        raise EngineError(f"No one is listed for role(s) {roles} in config/approvers.yaml. Add names before {action}.")
    if name not in allowed:
        raise EngineError(f"'{name}' is not allowed to {action}. Allowed: {sorted(allowed)}")
    return next(r for r in roles if name in (cfg.get(r) or []))


# ------------------------------------------------------------------ commands

def cmd_new(ctx: Ctx, a):
    slug = re.sub(r"[^a-z0-9]+", "-", a.topic.lower()).strip("-")[:40] or "run"
    run_id = f"{dt.date.today():%Y%m%d}-{slug}"
    rd = ctx.runs_dir / run_id
    if rd.exists():
        raise EngineError(f"Run {run_id} already exists.")
    for n in sorted(ctx.gates["steps"]):
        (rd / step_info(ctx, n)["folder"]).mkdir(parents=True)
    (rd / "01_research" / "inputs").mkdir()
    st = {"run_id": run_id, "topic_hint": a.topic, "mode": a.mode, "created": now(), "created_by": a.by,
          "step": 1, "status": "in_progress", "done": []}
    (rd / "state.json").write_text(json.dumps(st, indent=2), encoding="utf-8")
    print(f"Created run {run_id}. Step 1: {step_info(ctx, 1)['name']}")
    return run_id


def cmd_status(ctx: Ctx, a):
    st = ctx.state(a.run)
    rd = ctx.run_dir(a.run)
    print(f"Run {st['run_id']}  mode={st['mode']}  status={st['status']}")
    if st["status"] in ("complete", "ready_for_review"):
        print(f"Steps {', '.join(map(str, st['done']))} complete. Next: step 7 (compliance & QA review), not built yet.")
        return
    n = st["step"]
    info = step_info(ctx, n)
    gate = info["gate"]
    print(f"Current step {n}: {info['name']}   gate {gate}: {ctx.gates['gates'][gate]['title']}")
    findings = run_checks(ctx, rd, n)
    blocks = [f for f in findings if f.level == "block"]
    print(f"Open blocking findings: {len(blocks)}")
    print_findings(findings)
    last = [e for e in read_log(rd) if e["gate"] == gate]
    print("Gate record:", f"{last[-1]['decision']} by {last[-1]['by']} at {last[-1]['ts']}" if last else "none yet")


def cmd_check(ctx: Ctx, a):
    st = ctx.state(a.run)
    rd = ctx.run_dir(a.run)
    n = int(a.step) if a.step else st["step"]
    print(f"Checks for step {n}: {step_info(ctx, n)['name']}")
    findings = run_checks(ctx, rd, n)
    print_findings(findings)
    return 1 if any(f.level == "block" for f in findings) else 0


def cmd_facts(ctx: Ctx, a):
    rd = ctx.run_dir(a.run)
    st = ctx.state(a.run)
    if st["step"] != 1:
        raise EngineError("Facts can only be reviewed during step 1.")
    require_role(ctx, a.by, ctx.gates["gates"]["G1"]["roles"], "review facts")
    p = rd / "01_research" / "fact_ledger.json"
    data = V.load_json(p)
    by_id = {f["id"]: f for f in data["facts"]}
    changes = []
    for arg, status in ((a.approve, "approved"), (a.reject, "rejected"), (a.lead_only, "lead_only")):
        for fid in [x.strip() for x in (arg or "").split(",") if x.strip()]:
            if fid not in by_id:
                raise EngineError(f"No fact {fid}")
            f = by_id[fid]
            f["status"], f["reviewed_by"] = status, a.by
            if a.note:
                f["review_note"] = a.note
            changes.append(f"{fid}->{status}")
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    append_log(rd, {"run_id": a.run, "gate": "G1", "step": 1, "decision": "fact_review", "by": a.by, "note": ", ".join(changes)})
    print("Recorded:", ", ".join(changes) or "nothing")


def cmd_select(ctx: Ctx, a):
    rd = ctx.run_dir(a.run)
    if ctx.state(a.run)["step"] != 2:
        raise EngineError("Angle selection happens in step 2.")
    role = require_role(ctx, a.by, ctx.gates["gates"]["G2"]["roles"], "select an angle")
    p = rd / "02_ideation" / "angles.json"
    data = V.load_json(p)
    if a.angle not in {x["id"] for x in data["angles"]}:
        raise EngineError(f"No angle {a.angle}")
    data["selected"] = {"angle_id": a.angle, "selected_by": a.by, "selected_on": today(), **({"edits": a.edits} if a.edits else {})}
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    append_log(rd, {"run_id": a.run, "gate": "G2", "step": 2, "decision": "angle_selected", "by": a.by, "role": role, "note": f"{a.angle} {a.edits or ''}".strip()})
    print(f"Angle {a.angle} selected by {a.by}.")


def cmd_lock(ctx: Ctx, a):
    rd = ctx.run_dir(a.run)
    st = ctx.state(a.run)
    if st["step"] != 3:
        raise EngineError("Compile the brief in step 3.")
    findings = V.check_angles(run_dir=rd, config_dir=ctx.config_dir, need_selection=True)
    if any(f.level == "block" for f in findings):
        print_findings(findings)
        raise EngineError("Angles do not pass; cannot compile the brief.")
    angles = V.load_json(rd / "02_ideation" / "angles.json")
    ledger = V.load_json(rd / "01_research" / "fact_ledger.json")
    angle = next(x for x in angles["angles"] if x["id"] == angles["selected"]["angle_id"])
    topic = V.load_json(rd / "01_research" / "topic.json")
    used = {fid for k in angle["key_points"] for fid in k["fact_ids"]}
    lb = {
        "run_id": a.run, "angle_id": angle["id"], "topic": topic["topic"], "format": angle["format"],
        "core_message": angle["core_message"], "key_points": angle["key_points"], "audience": angle["audience"],
        "required_terms": angle["required_terms"], "out_of_scope": angle["out_of_scope"],
        "allowed_entities": angle["allowed_entities"],
        "facts": [f for f in ledger["facts"] if f["id"] in used],
        "compiled_from": {
            "fact_ledger_sha256": V.sha256_file(rd / "01_research" / "fact_ledger.json"),
            "angles_sha256": V.sha256_file(rd / "02_ideation" / "angles.json"),
            "selected_by": angles["selected"]["selected_by"], "compiled_on": now(),
        },
    }
    (rd / "03_approval" / "locked_brief.json").write_text(json.dumps(lb, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Compiled locked_brief.json: 1 message, {len(lb['key_points'])} key points, {len(lb['facts'])} facts. Awaiting Gate G3.")


def cmd_approve(ctx: Ctx, a):
    rd = ctx.run_dir(a.run)
    st = ctx.state(a.run)
    n = st["step"]
    info = step_info(ctx, n)
    if a.gate != info["gate"]:
        raise EngineError(f"The current step is {n}; its gate is {info['gate']}, not {a.gate}.")
    role = require_role(ctx, a.by, ctx.gates["gates"][a.gate]["roles"], f"decide {a.gate}")
    if a.decision == "reject" and not a.note:
        raise EngineError("A rejection needs a note saying what must change.")
    if a.decision == "approve":
        findings = run_checks(ctx, rd, n)
        if any(f.level == "block" for f in findings):
            print_findings(findings)
            raise EngineError(f"{a.gate} refused: blocking findings remain.")
        if a.gate == "G4":
            sod = V.load_yaml(ctx.config_dir, "approvers.yaml").get("separation_of_duties", {})
            if sod.get("gate4_differs_from_gate3"):
                g3 = [e for e in read_log(rd) if e["gate"] == "G3" and e["decision"] == "approve"]
                if g3 and g3[-1]["by"] == a.by:
                    raise EngineError("Separation of duties: the script sign-off must be a different person from the topic approver.")
    e = append_log(rd, {"run_id": a.run, "gate": a.gate, "step": n, "decision": a.decision, "by": a.by, "role": role,
                        "note": a.note or "", "artifact_hashes": artifact_hashes(ctx, rd, n)})
    print(f"{a.gate} {a.decision} recorded for {a.by} (log #{e['seq']}).")


def cmd_advance(ctx: Ctx, a):
    rd = ctx.run_dir(a.run)
    st = ctx.state(a.run)
    if st["status"] in ("complete", "ready_for_review"):
        raise EngineError("Nothing to advance: the built steps are complete.")
    n = st["step"]
    info = step_info(ctx, n)
    gate = info["gate"]
    decisions = [e for e in read_log(rd) if e["gate"] == gate and e["decision"] in ("approve", "reject")]
    if not decisions or decisions[-1]["decision"] != "approve":
        raise EngineError(f"{gate} has no standing approval. A named person must approve first.")
    if decisions[-1]["artifact_hashes"] != artifact_hashes(ctx, rd, n):
        raise EngineError(f"Files changed after {gate} was approved. The approval no longer applies; get it approved again.")
    findings = run_checks(ctx, rd, n)
    if any(f.level == "block" for f in findings):
        print_findings(findings)
        raise EngineError("Checks no longer pass.")
    if problems := verify_log(rd):
        raise EngineError("Approval log integrity problem: " + "; ".join(problems))
    st["done"].append(n)
    if n == 4:
        handoff = {
            "run_id": a.run, "completed": now(), "format": V.load_json(rd / "03_approval" / "locked_brief.json")["format"],
            "files": {k: v for s in (1, 2, 3, 4) for k, v in artifact_hashes(ctx, rd, s).items()},
            "approvals": [{k: e[k] for k in ("seq", "ts", "gate", "decision", "by", "role", "note") if k in e}
                          for e in read_log(rd) if e["decision"] in ("approve", "reject", "angle_selected")],
            "next_step": "5: Design & Visuals. Input is script.json and locked_brief.json only.",
        }
        (rd / "handoff.json").write_text(json.dumps(handoff, indent=2), encoding="utf-8")
        print("Steps 1-4 complete. handoff.json written for step 5.")
    nxt = n + 1
    while nxt in ctx.gates["steps"] and not step_applies(ctx, rd, nxt):
        st.setdefault("skipped", []).append(nxt)
        print(f"Step {nxt} ({step_info(ctx, nxt)['name']}) does not apply to this format; skipped.")
        nxt += 1
    if nxt in ctx.gates["steps"]:
        st["step"] = nxt
        print(f"Advanced to step {nxt}: {step_info(ctx, nxt)['name']}")
    else:
        st["status"] = "ready_for_review"
        media = {"run_id": a.run, "completed": now(),
                 "files": {k: v for s in st["done"] for k, v in artifact_hashes(ctx, rd, s).items()},
                 "next_step": "7: Compliance & QA review (not built yet)."}
        (rd / "handoff_media.json").write_text(json.dumps(media, indent=2), encoding="utf-8")
        print("Design steps complete. handoff_media.json written for step 7.")
    ctx.save_state(a.run, st)


def cmd_reopen(ctx: Ctx, a):
    """Send a run back to the step that caused a problem. Later work is not deleted, but must be re-checked and re-approved."""
    rd = ctx.run_dir(a.run)
    st = ctx.state(a.run)
    n = int(a.step)
    if n not in ctx.gates["steps"] or (st["status"] not in ("complete", "ready_for_review") and n > st["step"]):
        raise EngineError("You can only reopen the current step or an earlier one.")
    roles = [r for r in V.load_yaml(ctx.config_dir, "approvers.yaml")["roles"]]
    role = require_role(ctx, a.by, roles, "reopen a step")
    st["step"], st["status"] = n, "in_progress"
    st["done"] = [d for d in st["done"] if d < n]
    ctx.save_state(a.run, st)
    append_log(rd, {"run_id": a.run, "gate": step_info(ctx, n)["gate"], "step": n, "decision": "reopened", "by": a.by, "role": role, "note": a.note})
    for name in (["handoff.json"] if n <= 4 else []) + ["handoff_media.json"]:
        if (rd / name).exists():
            (rd / name).unlink()
    print(f"Run reopened at step {n}: {step_info(ctx, n)['name']}. Reason logged.")


def cmd_verify(ctx: Ctx, a):
    rd = ctx.run_dir(a.run)
    problems = verify_log(rd)
    print("Approval log intact." if not problems else "PROBLEMS: " + "; ".join(problems))
    return 1 if problems else 0


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--runs-dir", default=str(ROOT / "runs"))
    p.add_argument("--config-dir", default=str(ROOT / "config"))
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new"); s.add_argument("--topic", required=True); s.add_argument("--mode", choices=["topic_driven", "discovery"], default="topic_driven"); s.add_argument("--by", required=True)
    for name in ("status", "lock", "advance", "verify-log"):
        s = sub.add_parser(name); s.add_argument("run")
    s = sub.add_parser("check"); s.add_argument("run"); s.add_argument("step", nargs="?")
    s = sub.add_parser("facts"); s.add_argument("run"); s.add_argument("--by", required=True); s.add_argument("--approve"); s.add_argument("--reject"); s.add_argument("--lead-only", dest="lead_only"); s.add_argument("--note")
    s = sub.add_parser("select"); s.add_argument("run"); s.add_argument("--angle", required=True); s.add_argument("--by", required=True); s.add_argument("--edits")
    s = sub.add_parser("reopen"); s.add_argument("run"); s.add_argument("--step", required=True); s.add_argument("--by", required=True); s.add_argument("--note", required=True)
    s = sub.add_parser("approve"); s.add_argument("run"); s.add_argument("gate", choices=["G1", "G2", "G3", "G4", "G5", "G6"]); s.add_argument("--by", required=True); s.add_argument("--decision", choices=["approve", "reject"], required=True); s.add_argument("--note")
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    ctx = Ctx(Path(a.runs_dir), Path(a.config_dir))
    fn = {"new": cmd_new, "status": cmd_status, "check": cmd_check, "facts": cmd_facts, "select": cmd_select, "lock": cmd_lock,
          "approve": cmd_approve, "reopen": cmd_reopen, "advance": cmd_advance, "verify-log": cmd_verify}[a.cmd]
    try:
        rc = fn(ctx, a)
    except EngineError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"REFUSED: a file this step needs has not been written yet ({Path(e.filename).name}).", file=sys.stderr)
        return 2
    return rc if isinstance(rc, int) else 0


if __name__ == "__main__":
    sys.exit(main())
