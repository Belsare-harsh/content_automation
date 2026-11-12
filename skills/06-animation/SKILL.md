---
name: 06-animation
description: Step 6 of the TheFinPedia content engine, for reels and videos only. Render an MP4 with Remotion from the design signed at Gate 5, check it, and bring it to a named person for Gate 6.
---

# Step 6: Animation & video

Applies only when the format's output is mp4 (reels, videos). Image formats skip this step automatically.

## Do

1. `python3 tools/animate.py build <run>` writes `06_animation/props.json`, renders `video.mp4` with Remotion (`tools/remotion`), and writes `video.json`.
2. `python3 tools/engine.py check <run>` until no BLOCK findings remain.
3. Watch the video, or at least pull frames from every scene (`ffmpeg -ss <t> -i video.mp4 -frames:v 1 f.png`) and look at them.
4. Show the person the video and the warnings. They decide G6.

## Rules

- The video opens with the SEBI disclosure slate (placeholders unchanged), then one scene per approved design page, in order.
- Scene length follows reading time (`brand.yaml` → video). Never speed a scene up below the reading time; if it is too long, shorten the beat in step 4.
- Motion is limited to fades and line-by-line reveals. No zooms on figures that could exaggerate them, no stock footage of money, no countdowns or urgency.
- Audio: none yet. Music must be licensed with its source recorded; a voice-over must read the script word for word. Both are open decisions.
- Remotion licence: free for companies of up to 3 people; a larger company needs a Remotion company licence before production use.

## Open decisions

- Voice-over (human or AI) and approved music source.
- Disclosure slate length (2.5 s placeholder) and whether the strip also stays on every scene: compliance owner.

## Short styled reels (reels_short, under 20 seconds)

First made for rmwdezgf7 (risograph, 17.5 s). The path:
1. **Story (SOUL + reel fundamentals):** one idea, 4 to 7 text cards, hook on screen in the first frame. Every card's numbers cite a locked fact; the reviewer checks each card.
2. **Art direction:** insight, idea (a verb), 2 to 3 standout ingredients, all traced back to the idea (art-direction-proposition skill). The style comes from `config/styles.yaml`. Pick the reel's style from its own story metaphor; do not copy the carousel's style by default (user feedback on rmwdezgf7).
3. **Props:** `tools/remotion/src/riso/reel-<run>.json` (cards with fact_ids, cuts and hits in frames, slot, audio). `validators.check_reel_cards` must pass: length, words, reading time, numbers in cited facts, disclosure text.
4. **Music and sound:** an original score from CC0 samples (Lemo-Opuscar sampler: marimba, vibraphone, jazz bass, shaker, claves) plus procedural sound effects, cut to the same beat grid as the picture. No trending or copyrighted music. Keep the score script and credits next to the reel.
5. **Render:** `npx remotion render src/index.ts RisoReel out.mp4 --gl=swangle --browser-executable=$(which google-chrome)`; render stills of every scene first and look at them.

Lessons:
- An opening disclosure slate kills the hook. Use a persistent disclosure strip on every frame instead (pending the compliance owner's confirmation; `reels_short.disclosure` in content-types.yaml).
- One continuous camera move (a phone, then a window, then a lit city, back to the window) carries a data story without extra words, and makes the reel loop.
- Canvas text renders before web fonts load unless the composition waits (`delayRender` until `document.fonts.load` resolves with the rupee sign); otherwise some frames fall back to a serif.
- The reel check caught a date on the closing source card with no cited fact, and 46 words against a 45-word limit: fix the content, never the limit.

### Second reel: silent film (rmwdezgf7, "The Whole Film", 19.1 s)
- The user rejected reusing the carousel's risograph look for the reel. Re-write the reel script with the SOUL method as its own story, then pick a style that suits motion and the metaphor.
- Story shape that worked: hook card (the dip) -> the two numbers -> "Now zoom out one year." -> picture-only zoom across a strip of film frames -> the year-on-year numbers -> the line -> save CTA with source.
- Card text auto-fits (cards.ts); the disclosure plaque auto-fits. Check stills of every card at full size before the full render.
- Render: `npx remotion render src/index.ts SilentReel out.mp4 --gl=swangle --browser-executable=/usr/bin/google-chrome` (default concurrency on 2 CPUs).
- User feedback on v1: the art style was great; the transitions were not natural (mostly hard cuts between cards) and the script was weak. Next version: dissolves between cards, an iris or fade through black at the story turn, camera motion carried across cuts. Start from the content lead's own script.
- If the data is thin, the reel needs a story or allegory first (see "Format fit" in 02-ideation); otherwise suggest a minimalist post or a carousel instead.

