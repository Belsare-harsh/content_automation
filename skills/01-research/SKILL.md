---
name: finpedia-01-research
description: Step 1 of the TheFinPedia content engine. Topic discovery and sourced research that ends in a human-reviewed fact ledger. Use at the start of every run.
---

# Step 1: Research & Topic Discovery

Goal: a short list of facts, each traced to an approved source and each approved by a human. Nothing later may say more than this list says.

## Context and focus

Before searching, read `config/context.yaml`. If it lists `content_pillars`, discovery mode scores candidate topics against them first. If the human gave notes on how past topics performed, use them to rank candidates and say so in the shortlist. Do not invent performance history.

Research widely, then pass on only the highest-impact points: the research brief opens with at most five findings, ranked by how much they change what the audience should understand. Everything else stays in the ledger for reference.

Domain framing: read `skills/shared-mf-domain/SKILL.md` to choose the right official sources and terms. In Discovery mode use `skills/shared-market-watch/SKILL.md`. Neither is a source of facts.

## 1a. Intake (human touchpoint)

Ask for, in one message: the topic (or "discovery" if none), who it is for, what is in and out of scope, and whether they have internal material (ASMF exports, team documents). ASMF is desktop-only, so a human exports from it and drops the file in `runs/<run>/01_research/inputs/`. Read anything they supply; record it as `source.tier = "internal"` with `provided_by` and `file`.

Start the run: `python3 tools/engine.py new --topic "<topic>" --mode topic_driven|discovery --by "<name>"`.

## Discovery mode (no topic yet)

1. Read `config/research-sources.yaml`. Search only the tier 1 domains (WebSearch with `allowed_domains`) for what changed in the last 30 days: circulars, data releases, rate changes, notices. Use tier 3 media only to notice what is being talked about.
2. Produce 5 to 8 candidates: topic, why it matters now, the primary page that shows it, who it affects (MFDs, RIAs, their clients), and a risk note if it would need a performance claim or a named scheme.
3. **Stop.** Show the candidates. The human picks one (or none) and states scope. Only then write `topic.json` with `mode: "discovery"` and the candidates in `discovery_candidates`.

## 1b. Deep research

1. Break the topic into the questions a script would need answered. Write them down first.
2. For each question, search tier 1 domains first, then tier 2. Fetch the actual page (WebFetch); do not rely on a snippet.
3. Write each finding into `01_research/fact_ledger.json` (schema: `schemas/fact_ledger.schema.json`):
   - `statement`: your own plain-language paraphrase, one claim per fact.
   - `evidence_excerpt`: the short passage that supports it, 25 words or fewer. Never paste paragraphs.
   - `source`: tier, publisher, page title, exact https URL, access date.
   - `numbers`: every figure in the statement, each with the date it is true for (`as_of`). A figure with no date cannot be used.
   - `status`: `proposed` for everything you add. Media-sourced findings are `lead_only`; then go find the primary source.
   - `added_by`: `ai`.
4. If two sources disagree, add an entry to `conflicts` describing it. Do not pick a winner; a human resolves it.
5. List what you could not find in `open_questions`.
6. Write `research_brief.md`: one page, facts grouped by question, each with its id and a link. This is what the human reads.
7. `python3 tools/engine.py check <run>` and fix every BLOCK.

## 1c. Fact review (human touchpoint, the important one)

Show the human the fact table (id, statement, source link, as_of date, status). Ask them to approve, reject or hold each fact, resolve conflicts, and add anything you missed. They may add facts themselves (`added_by: "human"`).

Record only what they tell you: `python3 tools/engine.py facts <run> --by "<name>" --approve F001,F002 --reject F003 --note "<their note>"`. Then, when they say the research is good: `approve <run> G1 --by "<name>" --decision approve`, then `advance`.

## Accuracy rules for this step

- Prefer the regulator's own wording over any summary of it.
- A figure is only as good as its date. If the page does not state the date, say so in `review_note` and let the human decide.
- If the primary source cannot be found, the fact stays `lead_only`. Do not upgrade it.
- A thin result is a valid result. Say "only 3 approved facts, not enough" rather than padding.
