# Cloud worker runbook

The Content Review Console (claude.ai artifact `60b303c5-33e2-4304-903e-18274fe7198b`) is the source of truth for console runs.
People sign gates there. The console drafts angles and scripts by itself. It also queues the steps that need web
search or rendering as documents in the `jobs` collection. An hourly scheduled task runs this runbook to do those jobs.

You are that worker. Nobody is watching. Do not ask questions; do the job, record what happened in the job document, and stop.

## 0. Setup

```
cd <this repo> && sh worker/setup.sh
```
Read `ORCHESTRATOR.md` (rules you never break) and the skill for each step you run.

## 1. Find work

1. `db_list` collection `jobs` on the console artifact.
2. Pick documents with `status: "queued"`, oldest `requested_at` first, at most **2 jobs** per run of this task.
3. If none are queued, stop at once with the message "No queued jobs." Do not push a notification.

## 2. For each job

1. Claim it: `db_write` op `update` on `jobs/<id>` with the version from the list, data
   `{"status": "working", "started_at": <now ISO>}`. If the version check fails, someone else took it; skip it.
2. Read the run: `runs/<run_id>` plus its `facts`, `angles`, `beats`, `media/design` documents, and the config
   documents `config/rules`, `config/sources`, `config/writer`, `config/context`.
3. Do the step (section 3).
4. Finish: `update` `jobs/<id>` with `{"status": "done", "finished_at": <now>, "note": "<one line: what is ready and which gate to sign>"}`.
   On failure after three honest attempts: `{"status": "failed", "note": "<what is stuck, in plain words>"}`. Never loosen a rule to finish.
5. End your final message with one line per job, for example: `rmwdad83i research: 9 facts ready for Gate 1.`
   That line is what the phone notification shows.

## 3. Steps

### research (step 1)
- Follow `skills/01-research/SKILL.md` section 1b, with the run's `topic`, `audience`, `scope` and `intake.focus`.
  In discovery mode, follow its discovery section and write the candidates to `runs/<id>` as `open_questions` instead of stopping.
- Use **only** the domains in `config/sources` `tier1` for facts (WebSearch with `allowed_domains`); `tier3_lead_only` are leads.
- Write each fact as `runs/<id>/facts/F001`, `F002`… with:
  `{id, status: "proposed", statement, excerpt (verbatim from the page), nums: [every figure in the statement as written], url, title, tier: "tier1", asof: "YYYY-MM-DD"}`.
- Record conflicts between sources in `runs/<id>` `conflicts: [{fact_ids:[..], description}]` and gaps in `open_questions`.
- Then `update` `runs/<id>`: `{"status": "in_progress", "step": 1}`.
- Never approve a fact. People approve at Gate 1, and the console then drafts the angles itself.

### design (step 5)
- Requires `gates.G4` on the run; otherwise fail the job with "Gate 4 is not signed."
- Save the run as one dump file `{"meta":…, "angles":[…], "beats":[…], "facts":[…]}` and run:
  ```
  python3 tools/console_bridge.py script dump.json work/script.json
  python3 tools/design.py from-script work/script.json work/design
  python3 tools/console_bridge.py design-doc work/design/design.json work/design-doc.json
  ```
- Check: `validators.check_design_data(design, script, Path("config"))` must return no BLOCK findings.
- Write the doc to `runs/<id>/media/design` with `db_write` `set`.
- Plain style is the default. An art style (risograph, silent film) needs image hosting. Use one only if the run's
  `style` field asks for it: publish the page images to the console artifact with `publish_files` (patch mode,
  `media/<id>/…`) and set each page's `img_src`.

### video (step 6, reels and videos only)
- Requires `gates.G5`. Save `media/design` as `work/design.json`.
- `python3 tools/animate.py from-design work/design.json work/video` (Remotion; takes several minutes).
- Keep the MP4 under 20 MB (raise `--crf` if needed). Publish it to the console artifact with `publish_files`
  (patch mode, `as: media/<id>/video.mp4`, base_version from `get_artifact`), then
  `python3 tools/console_bridge.py video-doc work/video/video.json /media/<id>/video.mp4 work/video-doc.json`
  and `set` it on `runs/<id>/media/video`.
- `validators.check_video_data` must return no BLOCK findings.

## 4. Never
- Approve a fact, pick an angle, or sign a gate.
- Write numbers, names or claims that are not in an approved fact.
- Touch a run that has no queued job.
- Edit the console page itself, except publishing media files as described above.
