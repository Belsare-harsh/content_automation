---
name: finpedia-03-topic-approval
description: Step 3 of the TheFinPedia content engine. Compiles the chosen angle into a locked brief and gets a named approver to freeze the message. Use after Gate 2.
---

# Step 3: Topic Approval and the Message Lock

Goal: one frozen statement of what this piece says and may say. Everything in step 4 is measured against it.

## Procedure

1. Compile, do not write: `python3 tools/engine.py lock <run>`. The engine builds `03_approval/locked_brief.json` from the selected angle and the approved facts it cites. Claude does not hand-edit this file.
2. Run `python3 tools/engine.py check <run>`.
3. Show the approver a one-page summary, in plain words:
   - **Message** (exact words, which cannot change after approval)
   - **Key points**, each with its facts (statement, source link, date)
   - **Format** and **audience**
   - **Must use** (required terms) and **must not touch** (out of scope)
   - **Allowed names** (schemes or fund houses) and **risks**, including whether a disclaimer will be required
4. **Stop.** The named topic approver approves or rejects. A rejection needs a note.
5. Record only what they say: `approve <run> G3 --by "<name>" --decision approve|reject --note "..."`, then `advance`.

## After approval

The message is frozen. A change of wording, a new key point or a new fact means `reopen` to step 2 (or 1), a fresh lock, and a fresh approval. The engine checks that the locked brief still matches the research and angle it was built from, so a quiet edit upstream makes the lock stale and blocks the run.

## Rules

- Approval is by a person named in `config/approvers.yaml`. If that file is empty, say so and ask who may approve; do not proceed.
- Do not soften or "improve" the message at this stage. If it reads badly, the approver edits the angle in step 2.
