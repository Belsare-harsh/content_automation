---
name: 05-design
description: Step 5 of the TheFinPedia content engine. Turn a script signed at Gate 4 into page designs (Fabric.js for the Cobranding Studio, Figma for designers, PNG previews), check them, and bring them to a named person for Gate 5.
---

# Step 5: Design & visuals

Input is the approved script only (`04_script/script.json`, after `handoff.json` exists). Never take words from anywhere else.

## Do

1. `python3 tools/design.py build <run>` builds `05_design/design.json`, `fabric.json` and `previews/*.png` from `config/brand.yaml`.
2. `python3 tools/engine.py check <run>` until no BLOCK findings remain.
3. Look at every preview yourself (open the PNGs). Check what the checks cannot: the page reads in the intended order, the highlighted figure is the one that matters, nothing looks crowded or misleading.
4. If Figma is wanted, push the same pages to Figma (see "Figma" below). Figma is for designers to polish layout and imagery; it never changes words.
5. Show the person the previews, the script beside them and the warnings. They decide G5: `engine.py approve <run> G5 --by NAME --decision approve|reject`.

## Art direction (styles)

Step 5 may use an art style instead of the plain layout (`config/styles.yaml`). Choose it from the run's SOUL brief: who the reader is, the emotional job and the schema. Record the choice and one line of reasoning in the page plan.

1. Write `PLAN.json`: the style, and for each beat a scene from the style's scene list (and the highlight figure, which must be a phrase from that beat).
2. `python3 tools/styled_design.py build <run> PLAN.json` renders art and type in separate passes, then writes `design.json` and runs the same checks. `fabric.json` carries the art PNG as a locked background and the words as text layers, so co-branding can still fill only the disclosure.
3. Open every `P0n-final.png` at full size. Check what code cannot: does the scene support the line without adding a claim, is any decoration readable as a chart or a count, is the disclosure strip legible, is any overprint muddy.
4. If a scene is missing, add it to the style's `page.html` scenes, following that style's rules in `config/styles.yaml`.

Lessons from the first styled run (rmwdezgf7, risograph, 7 pages):
- A shared visual motif across pages (the sun moving from morning to dusk) gives the carousel one arc and ties the hook to the action without any extra words.
- Pinholes and halftone make small type illegible: print type in its own pass, solid.
- Fonts: check the rupee sign (U+20B9) is in the font file before rendering. Jost lacks it; Bricolage Grotesque latin-ext has it.
- A full blue-over-sunflower overprint turned muddy olive; a blue tint over solid sunflower stays warm.

## Rules

- Words on a page are the beat's text, word for word. A highlight may repeat a figure from that same beat; nothing else is ever written.
- The SEBI disclosure strip keeps its placeholders. Names and registration numbers are filled per distributor at co-branding (step 9).
- The logo slot stays empty; it is filled at co-branding.
- If a beat does not fit, do not cut words in design. Send the run back to step 4 (`reopen --step 4`).
- Images, icons and illustrations: only if licensed and only as decoration. They may not show a number, a claim, a logo of another company or a real person. Not built yet; designers add them in Figma for now, and the checks still run on the words.
- Any edit after G5 voids the approval.

## Figma

Use the connected Figma account: one frame per page, named by page id, text layers named by layer id, with the brand colours and fonts. After designers edit, export back to `design.json` only through a script that keeps text layers identical; if any text changed, the checks block it.

## Open decisions (for the content team)

- Real brand: colours, fonts, logo, Harsh's SEBI base templates (brand.yaml says placeholder).
- Where the disclosure strip must sit (every page or first page) and its minimum size: compliance owner.
- Who signs G5: today content_lead (Ratnesh, Milind). A designer reviewer role may be added.
