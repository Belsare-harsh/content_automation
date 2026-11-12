---
name: finpedia-04-storyline-script
description: Step 4 of the TheFinPedia content engine. Writes the storyline and script strictly from the locked brief, proves every line against its source, and gets human sign-off. Use after Gate 3.
---

# Step 4: Storyline & Scriptwriting

Goal: a script that says exactly what was approved and nothing else. The message stays accurate and on the topic because every line is tied to a locked fact and checked three ways: by rules, by an independent reader, and by a person.

Writing craft: before drafting, read `skills/shared-content-writer/SKILL.md` (voice, hooks, beat craft) and `skills/shared-mf-domain/SKILL.md` (concepts, plain words). For reels and videos also read `skills/shared-reel-craft/SKILL.md`. Shape the script with the SOUL beats and score it as in `skills/shared-soul-finance/SKILL.md`. They change how a line reads, never what it claims. The facts and the checks below always win.

## Inputs (only these)

`03_approval/locked_brief.json`, `config/content-types.yaml` (length budget for the format), `config/compliance-rules.yaml`. Do not use the open web in this step. If a fact is missing, that is a step 1 problem: `reopen`.

## 4a. Storyline (`04_script/storyline.json`)

An ordered arc of acts: `hook`, then `point` and `proof` acts, then `recap`, then optionally `cta`. Each act has a one-line `purpose` and the locked `key_point` it serves (`null` for hook, recap, cta). Copy `core_message` from the lock exactly and set `locked_brief_sha256` to the SHA-256 of `locked_brief.json`. Every key point needs at least one act. Run `check`.

## 4b. Script (`04_script/script.json`, schema `schemas/script.schema.json`)

Write beat by beat. Each beat has an id (`B01`...), a `kind`, the `text`, its `key_point`, and the `fact_ids` it relies on.

How to write each kind:

- **hook**: opens on the topic using at least one required term. It poses the question or tension the key points resolve. It may not state a figure or claim that no locked fact backs.
- **point**: one claim, taken from one locked fact, in plain words. Reuse the fact's own terms; do not upgrade them ("usually" stays "usually", "can" stays "can").
- **proof**: makes the point concrete using the same fact. No new numbers, examples with invented figures, or comparisons.
- **recap**: restates the core message in the same terms, using required terms.
- **cta**: an invitation (save, share, ask your distributor). No promise, no urgency, no figure.
- **disclaimer**: only when the script states a performance figure. Text is copied verbatim from `compliance-rules.yaml` and carries its `disclaimer_id`. Never write or reword it. If the wording on file is empty, stop and tell the human the compliance owner must supply it.

- **disclosure**: the first beat of every script when `sebi_disclosure.required` is true in `compliance-rules.yaml`. Its text is the `slot_text` from that file, character for character, with the `{{...}}` placeholders left as they are. It cites no fact. Never write a real name or registration number. They are filled in per distributor at co-branding. It does not count toward length and is not sent to the independent reviewer.

Hard rules (the engine blocks all of these):
- The script's `core_message` equals the locked message word for word.
- Every number, date and quantity in a beat appears in a fact that beat cites.
- Only locked facts may be cited, and every point or proof cites at least one.
- Nothing in `out_of_scope`; no scheme or fund-house name outside `allowed_entities`.
- No banned phrase (guarantees, assured returns, "best fund", and so on).
- Beat count and word counts stay inside the format's budget. Cut; do not squeeze.
- Every locked key point is delivered.

Write for the format: short slides for carousels, spoken sentences for reels and videos. Keep each sentence to one idea.

## 4c. Check and fix

`python3 tools/engine.py check <run>`. Fix every BLOCK at its cause by rewriting the beat from its fact. Do not edit the lock, the rules or the checks. After three rounds still stuck, stop and show the human what is stuck.

## 4d. Independent review

The drafter must not mark its own work. Start a fresh agent that has not seen the drafting, give it only `locked_brief.json`, `script.json` and `review-prompt.md` from this folder, and have it return a verdict per beat. Save the result as `04_script/semantic_review.json` with `independent: true`, the reviewer's name, and the SHA-256 of `script.json`. Any verdict other than `supported` means rewrite that beat and review again from scratch. The engine blocks a review that does not match the current script.

## 4e. Evidence table and human sign-off

Write `04_script/evidence_table.md`: one row per beat with the beat text, the locked fact it rests on, the source link, and the reviewer's note. Include any warnings from `check`. Show it to the human next to the script.

The named content lead reads it and decides. Record only what they say: `approve <run> G4 --by "<name>" --decision approve|reject --note "..."`, then `advance`. Advancing writes `handoff.json` for step 5.

## What step 4 will not do

It will not add facts, soften the message, name a scheme the approver did not allow, or write compliance wording. If the script needs any of those, the run goes back to the step that owns the problem.

## Thin data, reel format
If the run is a reel and the locked facts are few (see "Format fit" in 02-ideation), write the allegory or story first (a scene, a metaphor, characters), then place the facts inside it. The story carries the length; the facts carry the proof. The first silent-film reel (rmwdezgf7) was judged weak because two numbers were stretched across 19 seconds without a story.

