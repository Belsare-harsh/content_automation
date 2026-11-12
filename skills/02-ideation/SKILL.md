---
name: finpedia-02-ideation
description: Step 2 of the TheFinPedia content engine. Turns approved facts into 3 to 5 distinct content angles for a human to choose from. Use after Gate 1.
---

# Step 2: Content Ideation & Strategy

Goal: give a human real choices, each one built only from facts they already approved. The human picks; Claude never does.

## Context

Read `config/context.yaml` (audience, tone, pillars) before writing angles. It shapes the audience and wording of an angle. It never adds facts.

Writing craft: read `skills/shared-mf-domain/SKILL.md` and `skills/shared-content-writer/SKILL.md` so angles use the right concept and plain wording. For a reel or video angle also read `skills/shared-reel-craft/SKILL.md`. They shape framing only and never add a fact.

## Inputs

Approved facts in `01_research/fact_ledger.json`, the topic and scope notes in `topic.json`, the content types in `config/content-types.yaml`.

## Produce `02_ideation/angles.json` (schema: `schemas/angles.schema.json`)

Write 3 to 5 angles. They must differ in the **message**, not in the wording. Each angle has:

- `core_message`: one sentence, 30 words or fewer, that a reader could repeat. Every word of it must be supportable by the key points below. No implied claims, no "best", no promise.
- `key_points`: at most 3 (`K1` to `K3`). Each says one thing and lists the approved `fact_ids` that prove it. If a point has no approved fact, it does not exist.
- `format`: one of the eight platform types (carousel, infographics, minimalist, reels, videos, presentation, podcasts, ebooks). Pick the format that suits the message, and say why in `why_now` or `risks`. Reels and videos are MP4 output for now.
- `audience`: the specific reader (for example "MFD explaining SIP to a first-time client").
- `required_terms`: 2 to 4 words that any on-topic script must use. These anchor the script to the topic.
- `out_of_scope`: words or subjects the script must not touch, taken from the human's scope notes plus anything adjacent that would drag the piece off course (tax, other products, predictions).
- `allowed_entities`: scheme or fund-house names the script may mention. Empty unless the human's facts name one and the human wants it named.
- `risks`: anything that needs care. A performance figure means a disclaimer is required. A named scheme means extra review at step 9.

Then `python3 tools/engine.py check <run>` and fix every BLOCK.

## Human touchpoint (stop here)

Show the angles side by side: message, key points with their facts, format, audience, risks. Say which you would lean toward and why in one line, then ask the human to choose. They may edit any angle (message, key points, terms, scope). Apply their edits exactly, re-run the check, and note what changed.

Record: `python3 tools/engine.py select <run> --angle A2 --by "<name>" --edits "<what they changed>"`, then `approve <run> G2 ...`, then `advance`.

## Rules

- Never cite a fact the human did not approve. If an angle needs a fact you do not have, say so and send the run back to step 1 (`reopen`) rather than stretching a weaker fact.
- Five weak angles are worse than three good ones.
- Do not write hooks, captions or script lines here. That is step 4.

## SOUL brief (required)

Give every angle a `soul` object (reader, phase, intent, job, schema) as set out in `skills/shared-soul-finance/SKILL.md`. One angle carries one intent. The SOUL brief shapes framing only; key points and facts follow the rules above.

## Format fit: how much data is there? (decided by the content lead, 12 Nov 2026)
Check the locked facts before you propose a format:
- **Few data points (one or two key numbers):** best as a **minimalist** post or a **carousel**. A reel made from this feels thin.
- **Many data points and a lot of information:** a **reel** fits, because the motion has something to carry.
- **A reel is still wanted, but data is thin:** the reel needs a **story** to flesh it out: an allegory, a metaphor or a small scene that carries the idea. The story has to be written first, and the facts sit inside it. Never pad with numbers the research did not lock.
Say which case applies in the angle's `format` reason, and flag it to the topic approver when a reel is requested on thin data.
