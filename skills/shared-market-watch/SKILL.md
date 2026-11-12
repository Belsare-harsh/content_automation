---
name: finpedia-shared-market-watch
description: Scans official sources for what is new in Indian mutual funds and turns it into sourced topic leads for the content team. Use for Discovery mode or when asked what to write about. Claude has no live feed; every lead must come from a source fetched in this session.
---

# Market watch (topic leads)

Claude does not "keep up" with the market between sessions. Its knowledge stops at a cutoff, and rules, data and policy change after it. So trend awareness here means: **look at the official sources now, then propose leads with the evidence attached**. A lead with no link and date is not a lead.

## When to run

- Discovery mode at the start of a content cycle, or on request ("what should we write about this week").
- Before ideation, if the topic depends on something that may have changed since it was last researched.

## Scan checklist (use `config/research-sources.yaml` for the live list)

| Area | Source | Look for |
| --- | --- | --- |
| Industry data | amfiindia.com (monthly note, SIP page) | New month released? SIP contribution, accounts, assets, flows |
| Regulation | sebi.gov.in (Legal, Circulars, Board meetings, Consultation papers, Master circulars) | New or amended regulations, circulars affecting MFDs, AMCs or investors |
| Monetary and macro | rbi.org.in, mospi.gov.in | Policy decisions, inflation, growth releases |
| Markets | nseindia.com, bseindia.com | Index and participation data, only as reported |
| Tax and budget | incometax.gov.in, indiabudget.gov.in, finmin.nic.in | Changes with a stated effective date |
| Investor education | nism.ac.in, iepf.gov.in, pib.gov.in | Official explainers and announcements |

Media sites (Tier 3) may point to something to check. They are never the evidence.

## Output: a short lead list

For each lead (5 to 8 at most), give:

- `topic`: a plain statement of what is new.
- `why_now`: the dated trigger.
- `source`: the official link, with the date seen.
- `freshness`: days since the source was published or the period it covers.
- `pillar`: which content pillar it serves (see `config/context.yaml`).
- `fit`: who it helps (MFD explaining to clients, MFD staying compliant, etc.).
- `risk`: anything needing care (performance figures, a named scheme, an unclear effective date).
- `confidence`: whether the official page itself was read, or only a listing or a secondary report.

Rank by relevance to the MFD's week, not by novelty. A narrow amendment should be described as narrow.

## Discipline

- Check whether the newest period is out before choosing a period. If a newer one exists with no needed data, say so.
- If an official page could not be opened, say that, and mark any details from secondary reports as unverified.
- Never predict. A lead is "what was published", not "what will happen".
- Put leads in `config/topics` (console) as suggestions for a human to pick. Do not start a run on a lead without a person choosing it.
