# Independent script review (give this, with locked_brief.json and script.json, to a fresh agent)

You are reviewing a script for a financial education post. You have not seen how it was written. You have only two files: the locked brief (the approved message, key points and facts) and the script.

For every beat except disclaimer beats, decide one verdict and give evidence:

- `supported`: every claim in the beat is stated by, or a faithful plain-language restatement of, one of the locked facts the beat cites. Nothing is added or strengthened.
- `unsupported`: the beat says something no cited fact says (a number, date, cause, comparison, example, or implication).
- `overreach`: the beat takes a supported idea and makes it stronger, broader or more certain (for example "usually" became "always", "can" became "will", one case became a rule).
- `off_topic`: the beat is accurate but does not serve its key point or the core message.

Rules for you:
- Judge only against the locked facts. Do not use outside knowledge to decide something is true.
- Be strict. If you are unsure, do not mark `supported`.
- `evidence` must name the fact id and quote or point to the specific words that support the verdict, or state exactly what is missing.
- Return JSON only, in this shape:

```json
{"beats": [{"id": "B01", "verdict": "supported", "evidence": "F001: 'fixed amount at regular intervals' restated faithfully"}]}
```
