# Skills

Skills for Claude that I use and share. Each folder holds one skill: a `SKILL.md`, plus any
scripts or templates it uses.

| Skill | What it does |
|---|---|
| [substack-lens-replies](substack-lens-replies/SKILL.md) | Daily Substack outreach, end to end: finds posts from your inbox and keyword search, comments with one real question through your project's lens, follows up on replies, hearts, drafts proposals, files notifications, keeps a tracker doc and emails a summary. |

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

## Using a skill

Download the skill's folder (or just its `SKILL.md` when it has no scripts) and add it to
Claude as a skill, if your plan or organization allows custom skills. In Claude Code, put the
folder in `~/.claude/skills/`. Skills that need your details (name, accounts, folders) ask for
them on the first run and keep them in a settings section or file of their own; nothing
personal ships in this repo.
