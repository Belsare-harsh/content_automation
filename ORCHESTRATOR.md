# Orchestrator: how Claude runs steps 1 to 6

Claude is the engine. Claude does the thinking and writing; `tools/engine.py` decides whether work may move on.
Read this file at the start of every run, then follow the skill for the current step.

## The loop

1. `python3 tools/engine.py status <run>` shows the current step, what is blocking, and who last decided.
2. Do the step using its skill (`skills/0N-.../SKILL.md`).
3. `python3 tools/engine.py check <run>` until no BLOCK findings remain. Warnings go to the human.
4. Show the human what they must decide, in plain words, with the evidence next to it.
5. The human decides. Claude records it with the engine, using the human's own name. Then `advance`.

## Where a human must decide (this is not optional and not automatable)

| Checkpoint | Step | What the human does | Engine command |
|---|---|---|---|
| 1a Topic pick | 1 | States the topic, or picks one from discovery candidates. Adds scope notes. May drop in ASMF exports or documents. | writes `topic.json` |
| 1b Fact review | 1 | Approves, rejects or marks lead-only every fact. Resolves source conflicts. May add facts or sources of their own. | `facts`, then `approve G1` |
| 2 Angle pick | 2 | Picks one angle and edits it if needed. | `select`, then `approve G2` |
| 3 Topic approval | 3 | The approver reads the one-page locked brief and approves or rejects. The message is frozen at this moment. | `lock`, then `approve G3` |
| 4 Script sign-off | 4 | Reads the script next to its evidence table and confirms it says only what was approved. | `approve G4` |
| 5 Design sign-off | 5 | Looks at every page preview next to the script. | `approve G5` |
| 6 Video sign-off | 6 | Watches the video (reels and videos only; skipped for image formats). | `approve G6` |

## Rules Claude never breaks

- Never mark a fact approved, pick an angle, or approve a gate on the human's behalf. Only record a decision the human has stated in this conversation, under that person's name. If the name is unknown, ask once.
- Never edit `approvals.jsonl` or `state.json` by hand. Never edit a file after it was approved without sending the run back with `reopen`.
- Never use a source that is not in `config/research-sources.yaml`. Media sources are leads, never facts.
- Never put a number, date, scheme name or claim in a script that is not in a locked fact.
- Never reword the locked core message. Copy it exactly.
- Never write or paraphrase disclaimer text. It comes from `compliance-rules.yaml`, written by the compliance owner.
- If a check keeps failing after three honest fix attempts, stop and tell the human what is stuck. Do not loosen a rule to get through.
- A failure goes back to the step that caused it (`reopen`), never forward. A wrong fact found in step 4 means reopening step 1.

## What lives where

```
runs/<run-id>/
  state.json            current step (engine-owned)
  approvals.jsonl       hash-chained record of every human decision (engine-owned)
  01_research/          topic.json, fact_ledger.json, research_brief.md, inputs/ (human-supplied files)
  02_ideation/          angles.json
  03_approval/          locked_brief.json (compiled by the engine, never hand-written)
  04_script/            storyline.json, script.json, semantic_review.json, evidence_table.md
  handoff.json          written when step 4 is approved; the only input step 5 may use
  05_design/            design.json, fabric.json (Cobranding Studio), previews/*.png      tools/design.py
  06_animation/         props.json, video.mp4, video.json (reels/videos only)             tools/animate.py
  handoff_media.json    written when the last built step is approved; input for step 7 (not built yet)
```

## Proving the guards still work

`python3 -I -m unittest discover -s tests` must pass before any real run after a change to `tools/` or `config/`.
