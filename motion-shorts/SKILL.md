---
name: motion-shorts
description: Make vertical animated explainer shorts (1080x1920, 15-60 s) for Reels, TikTok and Shorts in code with Remotion - word-by-word kinetic text over a generated visual (the included template draws a constellation that connects outward from "you" while the sky turns from night to dawn), timed to a script, ready for music and voiceover. Use when the creator wants an animated short for an idea, an explainer scene for a talking-head video, or to turn an essay into a short.
---

# Motion shorts

Animated shorts written as code: every frame is a React component, so timing, text and
visuals are exact and easy to change. `template/` is a working 24-second short to start
from (`src/Constellation.tsx`): a starfield with a glowing "you" node, near nodes that appear
and fade, a field that connects outward in waves, a night-to-dawn sky, a slow camera push,
and script text springing in word by word.

Needs Node 20.19+ and npm. Remotion is free for individuals and companies of up to three
people; larger organisations need a company licence (check remotion.dev/license).

## 1. Script first

Write the short as beats before touching code. A beat is 2-4 seconds and a few short lines.
- **Hook in the first second**, no title card. "Right now, someone is on the same page as you."
- One idea per beat; concrete examples beat abstractions ("Same book. Same cause. Same 2am
  rabbit hole.").
- A turn ("What if it could?") just before the **key frame**: the title or the claim, where
  the visual and the music peak together.
- End on a question that invites comments, then the link in small type.
- Write a voiceover version and an on-screen-text version; they are rarely the same words.

## 2. Build

1. Copy `template/` into the video project folder (a durable place, not a scratchpad), then
   `npm install`.
2. Edit `BLOCKS` in `src/Constellation.tsx`: `from`/`to` in seconds, `gold` for the words
   that carry the idea, `delay` to stagger lines, `size` for emphasis. Match the visual's
   timings (`at` values on the near nodes, the edge growth start at 14.6 s, the sky change
   from 13.5 to 20.5 s) to the beats.
3. Preview with `npx remotion studio`, or render single frames to check layout:
   `npx remotion still ConstellationShort out/f540.png --frame=540` (frame = seconds x 30).
   Look at every frame you render before showing it.
4. Render: `npx remotion render ConstellationShort out/short.mp4` (24 s renders in about a
   minute).

Layout rules for vertical shorts:
- Keep text in the upper-middle band; the bottom fifth is covered by captions, buttons and
  the description in every app, and the right edge by like/comment buttons.
- 84 px bold for body lines, 110-130 px for the turn and the title, side padding 64 px.
  Check that no line wraps awkwardly.
- Leave the visual's busiest part out of the text band (the template keeps the field clear
  between y = 470 and 1060).

## 3. Other looks

- **Hand-drawn**: Rough.js (MIT) draws sketchy shapes in SVG and works inside a Remotion
  component; good for diagrams in an explainer.
- **Landscape, multi-minute explainers** with narration: the open-source
  `anything2explainer` skill (Remotion + Kokoro TTS) makes polished 16:9 explainers but its
  size is hard-coded to 1280x720, it opens with a slow title card, and its licence is
  PolyForm Noncommercial (fine for non-profit and personal work, not for commercial use).
  Borrow its scene ideas, not its frame size, for shorts.
- Read third-party skills and repos before installing them, and install from the repo, not
  a one-line `curl | sh`.

## 4. Finish

- **Music**: hand the render to the `music-to-picture` skill and name the key frame (for
  example "title at 17.5 s").
- **Voiceover**: record it, or use a voice clone built with `voice-clone-dataset`; keep the
  music low under the voice.
- **Covers**: pick a frame where the on-screen text makes a claim on its own; check it in a
  4:5 crop.
- **Post**: `social-post`.
