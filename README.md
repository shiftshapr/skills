# Skills

Skills for Claude that I use and share. Each folder holds one skill: a `SKILL.md`, plus any
scripts or templates it uses.

| Skill | What it does |
|---|---|
| [substack-lens-replies](substack-lens-replies/SKILL.md) | Daily Substack outreach, end to end: finds posts from your inbox and keyword search, comments with one real question through your project's lens, follows up on replies, hearts, drafts proposals, files notifications, keeps a tracker doc and emails a summary. |
| [stash-secret](stash-secret/SKILL.md) | Puts backup codes, recovery keys and wallet seed words into the macOS Passwords app without Claude ever reading them: queues them in an import file you import by hand, then deletes it. |

## Video

These five work together: record or animate, clean up, add music, post, and keep up the
conversation.

| Skill | What it does |
|---|---|
| [video-cleanup](video-cleanup/SKILL.md) | Turns raw talking-head phone clips into post-ready vertical shorts: removes retakes, fillers and repeats, cuts only inside silences so the audio stays smooth, converts iPhone HDR, burns in captions, makes phone previews. |
| [motion-shorts](motion-shorts/SKILL.md) | Animated explainer shorts written in code with Remotion, with a working 24-second template: kinetic text over a constellation that connects as the sky turns from night to dawn. |
| [music-to-picture](music-to-picture/SKILL.md) | Briefs music (Suno prompts included), measures candidate tracks, finds the biggest quiet-to-loud moment and lands it on the video's key frame, with an optional bass drop. |
| [voice-clone-dataset](voice-clone-dataset/SKILL.md) | Builds a 30-minute-plus recording of one person's voice for a voice clone from calls and talks they already have, checking every piece with a speaker-voice match. |
| [social-post](social-post/SKILL.md) | Drafts per-platform captions and covers, posts to YouTube Shorts and TikTok after approval, prepares Instagram for posting by hand, and drafts replies through whole comment threads. |

The video skills run on a Mac with Apple silicon (Whisper runs through mlx-whisper) and need
`uv`, `npm` and Node 20+. `video-cleanup/scripts/setup.sh` installs the full ffmpeg build the
others reuse.

### Third-party tools the video skills use

Not included in this repo; install them from their own repos. Read a repo's code before
installing it, pin the version you reviewed, and prefer installing from the repo over a
one-line `curl | sh`.

| Tool | Licence | What it adds | Install | Notes |
|---|---|---|---|---|
| [Rough.js](https://github.com/rough-stuff/rough) | MIT | Pencil-sketch shapes | Already a dependency of the `motion-shorts` template | Fixed `seed` per shape, or the drawing flickers |
| [line-art-animation](https://github.com/JDhruv14/line-art-animation) | MIT | Animated ink-line people, animals and scenes (SVG + TypeScript) | Clone into `~/.claude/skills/line-art-animation` | Node 22.18+ for its examples |
| [hallmark](https://github.com/Nutlope/hallmark) | MIT | Design review that catches generic "AI slop" pages and visuals | Copy its `skills/hallmark` folder into `~/.claude/skills/` | Optional extras: an edit hook (`install-hook.mjs`) and AI image generation (needs a Together AI key). Both work without them |
| [reanimate](https://github.com/NiazMorshed2007/reanimate) | MIT | Records a reference animation, rebuilds it, compares frame by frame | Copy its `skills/reanimate` folder into `~/.claude/skills/`, then run `scripts/setup.sh` | Needs Bun; first run downloads Chromium and ffmpeg (about 250 MB). See the note below |
| [Blender MCP](https://github.com/ahujasid/mcp-for-blender) | MIT | Lets Claude drive Blender for 3D scenes | `claude mcp add -s user blender -e DISABLE_TELEMETRY=true -- uvx mcp-for-blender==<version>`, then `uvx mcp-for-blender==<version> install-addon` and enable the add-on in Blender | Sends an anonymous usage record unless `DISABLE_TELEMETRY=true`. The add-on's socket accepts commands from anything on the machine with no password: start the server in Blender only while using it |

**Cloning someone else's animation (reanimate).** This is general information, not legal
advice. Timing, easing, pacing and technique are ideas, which copyright does not protect, so
rebuilding how something moves with your own visuals is the normal, safe use. The specific
creative expression is protected: artwork, illustrations, characters, photos, icons,
distinctive layouts and overall look. A frame-by-frame copy with a few colours and words
swapped can still be a copy, and edits made afterwards do not reliably fix that. Clone
pixel-for-pixel only your own work, work you have a licence for, or openly licensed work.
Never copy logos, brand characters or anything that could pass as made or endorsed by the
original author. For anything sold, widely published or high-profile, check with a lawyer.

## Using a skill

Download the skill's folder (or just its `SKILL.md` when it has no scripts) and add it to
Claude as a skill, if your plan or organization allows custom skills. In Claude Code, put the
folder in `~/.claude/skills/`. Skills that need your details (name, accounts, folders) ask for
them on the first run and keep them in a settings section or file of their own; nothing
personal ships in this repo.
