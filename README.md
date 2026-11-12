# TheFinPedia Content Engine: steps 1 to 4

Research, ideation, topic approval, storyline and script. Claude runs it; this folder holds the rules, the skills and the enforcement.

```
1 Research ──► [human: fact review] ──► 2 Ideation ──► [human: angle pick]
   ──► 3 Topic approval [named approver locks the message] ──► 4 Script ──► [independent review] ──► [human sign-off] ──► handoff to step 5
```

## To use it

Tell Claude: "Run the content engine for <topic>" (or "run discovery"). Claude reads `ORCHESTRATOR.md`, follows the skill for each step, and stops at every human checkpoint.

## Before the first real run (three files need a human)

1. `config/approvers.yaml`: name who may review facts, pick angles, and approve topics and scripts. Empty on purpose; the engine refuses to proceed without names.
2. `config/research-sources.yaml`: the content team confirms or edits the source list (drafted from the sources they named).
3. `config/compliance-rules.yaml`: the compliance owner pastes the exact disclaimer wording from the official documents. Until then, a script containing a performance figure is blocked.

Also confirm the length budgets in `config/content-types.yaml` (starter values).

## How accuracy is enforced

- Every fact needs an approved source, a short evidence excerpt, a date on every figure, and a human's approval.
- The brief is compiled by the engine from the chosen angle and approved facts; the message is then frozen.
- Every script beat cites locked facts. Numbers, dates, names and quantities must appear in those facts. Out-of-scope words, banned phrases, unapproved scheme names and reworded messages are blocked.
- An independent reviewer checks each beat against its fact, and a person signs off against an evidence table.
- Any edit after approval cancels the approval. Every decision is in a tamper-evident log.

## Tests

`python3 -I -m unittest discover -s tests -v` (49 tests, invented fixture data only).
