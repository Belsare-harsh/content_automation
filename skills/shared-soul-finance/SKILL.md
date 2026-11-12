---
name: shared-soul-finance
description: How the engine applies the team's soul-finance-content method (SOUL + Shield) inside steps 2 and 4. Gives every angle a real reader, one intent, a human scene and one honest proof, without loosening any fact or compliance check.
---

# SOUL inside the engine

Source: the team's `soul-finance-content` skill. This file says how it fits the engine's rules. Where the two differ, the engine's checks win and the difference is listed at the end for the content team.

## Step 2 (ideation): every angle carries a SOUL brief

Add a `soul` object to each angle:

- `reader`: one line, a real person in a real situation ("A 32-year-old salaried employee in Pune, two years into a monthly SIP, sees the debit message on salary day").
- `phase`: the sentiment phase (rally, euphoria, first dip, fear, capitulation, disbelief recovery, sideways boredom, event shock). Use it to choose tone only; never state it as a fact in the copy unless a fact says so.
- `intent`: "After this, [reader] will believe [new] instead of [old] and will [one action]."
- `job`: one of calm, cool down, re-engage, celebrate, explain.
- `schema`: misunderstanding reveal, light-bulb moment, myth vs fact (both sides must be approved facts), data zoom, pause question, identity or milestone.

One angle = one intent. If the topic has two messages, offer two angles.

## Step 4 (script): the six beats map onto the engine's beat kinds

| SOUL beat | Engine kind | Rule that still applies |
|---|---|---|
| Everyday hook (an Indian scene: salary day, family, shop, hometown) | hook | Uses a required term. A scene or question may be hypothetical, but it may not assert or imply a fact no locked fact backs (for example, "everyone is quitting"). |
| Hidden tension | hook or first point | Same as above. |
| Turn | point | Cites a locked fact. |
| Proof: one belief-flipping number, human unit | point / proof | The number must be in a cited fact, word for word. No rounding ("999.87 lakh", not "10 crore") unless the rounded figure is itself in a fact. |
| Tiny action | cta | Read, save, share, review your goal date, or talk to your distributor before changing anything. It must not tell the reader to start, stop or continue an investment when the scope rules that out. |
| Identity line | cta or recap-adjacent | Original wording. The recap still repeats the locked message exactly. |

Before handing over, score the script on the six SOUL checks (0 to 2 each: specific reader, one intent, human moment, honest proof, smallest action, feeling after). Aim for 10 or more out of 12 and record the score in the evidence table. The score is a craft prompt for the reviewer, not a gate: the engine's checks and the independent fact review still decide.

## Lessons from the first run (rmwdezgf7, October 2026 SIP data)

- A first-draft hook ("a scary headline pops up. Is everyone else quitting?") was rejected by the independent reviewer: it implied a fact no source supported. Curiosity hooks work better than fear hooks here: "Ever wondered how many others got one this month?"
- A first-draft action ("Before you change your SIP, talk to your distributor") was rejected as advice to continue an investment, which the scope excluded. "Save this for your next salary-day conversation about SIPs" passed.
- Reuse the hook's scene in the closing line; it gives the piece one shape.

## Differences from soul-finance-content (content team / compliance owner to decide)

1. Disclosure placement: the skill puts the disclosure on the last carousel slide and in the caption; the engine puts the SEBI disclosure first (and a strip on every page). Both can apply; the compliance owner decides.
2. Standard risk line ("Mutual Fund investments are subject to market risks, read all scheme related documents carefully."): the skill adds it to MF content. The engine never writes disclaimer text itself; the compliance owner must add the confirmed wording to `config/compliance-rules.yaml`, after which the engine can require it.
3. Tone: the skill uses empathy, comedy and pride; the engine's earlier voice rules said "no reassurance". Reconciled: emotion comes from the scene and framing, never from a promise about outcomes.
4. Regional-language variants: the skill offers one for Bharat-first readers. The engine has no translation check yet; a translated script needs its own independent review.
