---
name: finpedia-shared-reel-craft
description: Reel and short-vertical-video craft for TheFinPedia content (format "reels" or "videos"). Based on the team's reel-fundamentals skill, adapted to the engine's compliance rules. Read at step 2 when an angle uses a reel, and at step 4 before writing scenes. Style only; facts and checks still win.
---

# Reel craft

Source: the team's `reel-fundamentals` skill (hook, one idea, structure, length, safe zones, text, audio, consistency, pacing, cover and caption). This file keeps that guidance and adds what a regulated mutual fund reel needs. Where they conflict, the engine's checks and the approved facts win.

## The eleven fundamentals, applied here

1. **Hook (first 1 to 3 seconds).** Open on the most interesting true thing the facts allow: the question, the tension between two numbers, or the common mix-up. Never open with a logo, a greeting or "hey guys". A hook may not state a figure that no locked fact backs (the engine blocks it).
2. **One idea per reel.** One locked message. If the brief needs two messages, make two runs.
3. **Structure.** Hook, then value, then payoff or invitation. Map to engine kinds: hook, point, proof, recap, optional cta. Something new on screen every 2 to 3 seconds.
4. **Length.** Shorter is better. About 15 to 30 seconds suits an explainer or tip (roughly 40 to 75 spoken words). The engine's current reel budget is higher (4 to 9 scenes, up to 150 words, about 60 seconds). Treat that as a ceiling, not a target.
5. **Format and safe zones.** 9:16, 1080 x 1920. Keep text and key visuals clear of roughly the top 15% and bottom 20%, and away from the right edge.
6. **Text and captions.** Many watch with sound off. Large, high contrast, a few words at a time. On-screen text and captions come from the script text and the cited fact. Any number on screen must equal the number in the cited fact.
7. **Audio.** Clear voiceover. Music must be licensed for commercial use and never drown speech. No trending audio unless its licence covers brand use.
8. **Visual consistency.** The co-branding studio holds the palette, fonts and style. Do not invent new ones in a script.
9. **Pacing and loops.** Quick cuts and steady movement. If it fits naturally, let the last line echo the hook. Do not force a loop that changes the meaning.
10. **Cover, caption, hashtags.** A clear cover frame with the core message. The caption adds context or asks a question and never contains a figure that is not in a cited fact. A few relevant hashtags. No hashtags that imply performance or advice.
11. **Consistency and learning.** After publishing, read watch time, replays, shares and saves. Feed what worked back to the content team as benchmarks (`config/context.yaml`), not into scripts directly.

## Regulated-content additions

- **SEBI disclosure first.** The first scene is the disclosure slate (placeholder text unchanged, filled at co-branding). Keep it brief and plain so it does not break the hook. The compliance owner decides how long it must stay on screen and where. Until they confirm, the engine only requires the placeholder scene to come first.
- **Hook comes right after the slate.** The "first 3 seconds" rule applies to the first content scene.
- **Spoken lines.** One idea per scene, at most about 35 words, written for the ear: short sentences, no parentheses, numbers said as people say them.
- **Every scene cites its fact.** The evidence table carries each scene's fact and source link, same as a carousel.
- **Disclaimer.** If any scene states a performance figure, the exact approved disclaimer is a scene of its own, word for word.
- **Avoid in reels.** Predictions, urgency ("before it's too late"), fear, "best/top" language, comparisons that rank schemes, and "myth vs truth" framing unless both the myth and the truth are in approved facts.

## Story shapes that work for MFD content

Use only if the facts support the shape:

1. **Two numbers, one month**: hook the tension, state each number, say what each means, recap.
2. **Client question and answer**: the question, the plain answer from a fact, what the source does not say.
3. **What changed, what stayed**: the one change, then what a fact says is unchanged.
4. **Three-step explainer**: define, show the parts, recap (for product literacy topics such as TER or the riskometer).
5. **Before/after of a rule**: only when both versions are sourced.

## Planning output (step 2 to 4)

For a reel angle, add to the plan: single idea, shape, target length in seconds, scene list with beat kinds, on-screen text for each scene (from script text), audio direction, cover frame idea, caption, hashtags. Facts and numbers come from the locked brief only.

## Review checklist (pass or fail, one fix per failure, hook first)

1. Disclosure slate first, placeholder unchanged.
2. First content scene hooks within about 3 seconds, no greeting or logo opener.
3. One idea; recap matches the locked message.
4. Length within the budget and ideally within 15 to 30 seconds.
5. New visual or information every 2 to 3 seconds.
6. Text inside safe zones, large, a few words at a time, readable with sound off.
7. Every number on screen and in the caption appears in a cited fact.
8. Audio licensed; speech clear.
9. Cover, caption and hashtags carry no claim a fact does not back.
10. No advice, forecast, ranking or urgency language.

## Open decisions for the content team

- Should the engine add a shorter reel profile (for example 3 to 6 scenes, up to about 75 words) next to the current 150-word budget?
- How long and where must the disclosure slate stay on screen in a reel? (Compliance owner.)
- Which music source is approved for brand reels?

## Learned on the first short reel (rmwdezgf7)
- Keep it under 20 seconds: 6 cards, 44 on-screen words, a cut on every 4 to 6 beats of a 96 BPM bed.
- Hook card is a scene, not a number ("Salary day." over a phone with a generic debit message); the question card follows; numbers come after.
- Numbers land on the beat with a small "ka-chunk" and a registration kick; the closing card returns to the opening image so the reel loops.
- The persistent disclosure strip sits just above the bottom 20 % UI zone; text stays below the top 15 %.

## Learned on the second reel (rmwdezgf7, silent film)
- A reel is its own piece: re-write the story for motion and choose a style for the reel, even when a carousel on the same topic exists.
- A visual metaphor can carry the turn with no words (one film frame vs the whole strip = one month vs the year).
- Closing lines must observe, not instruct: "Look at more than one." passed; "Watch the whole film" was read as advice to stay invested.

## Format fit: how much data is there? (decided by the content lead, 12 Nov 2026)
Check the locked facts before you propose a format:
- **Few data points (one or two key numbers):** best as a **minimalist** post or a **carousel**. A reel made from this feels thin.
- **Many data points and a lot of information:** a **reel** fits, because the motion has something to carry.
- **A reel is still wanted, but data is thin:** the reel needs a **story** to flesh it out: an allegory, a metaphor or a small scene that carries the idea. The story has to be written first, and the facts sit inside it. Never pad with numbers the research did not lock.
Say which case applies in the angle's `format` reason, and flag it to the topic approver when a reel is requested on thin data.
