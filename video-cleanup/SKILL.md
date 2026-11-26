---
name: video-cleanup
description: Clean up raw talking-head phone videos (iPhone .MOV, vertical) for Instagram Reels, TikTok and YouTube Shorts. Removes retakes, false starts, fillers, stray words and non-strategic repeats, cuts only inside silences so the audio stays smooth, converts iPhone HDR to SDR, burns in captions and makes phone-sized previews. Use when the creator drops clips in a folder and wants them cut, cleaned up, captioned or made post-ready, or gives timestamps to fix in a cut.
---

# Video cleanup (talking-head shorts)

"The creator" is the person in the clips. Their top priority is **smooth audio**: a clip with
a leftover retake, an "um", a clipped word or a click at a join is not done.

Runs on a Mac with Apple silicon (Whisper runs through mlx-whisper). Needs `uv` and `npm`.

## 1. First run: setup

Ask the creator once, then write the answers into `settings.md` next to this file
(git-ignored if you keep the skill in a repo) and never ask again unless one is missing:

1. **Projects folder**: where video projects live (an external drive is best; big renders
   should not fill the internal disk). If it is on a drive that can be unplugged, check it is
   mounted before each job and stop and ask if it is not.
2. **Names Whisper will mishear**: their own name, project and product names. Copy
   `glossary.example.json` to `glossary.json` and fill it in.
3. **Review**: do they watch previews on a phone? (Then always make `--phone` copies.)

Then run `scripts/setup.sh` once.

## 2. Editing rules

- Remove every **retake and false start** ("I'm beginning, I'm beginning to write" → keep
  the last clean one).
- Remove **fillers and stray words**: um, uh, a dangling "that", "'Cause-", an empty
  "And so", mouth clicks and lip smacks.
- Remove **repeats** unless they are strategic and important to the video. Keep deliberate
  rhetoric: triplets ("less costly, less time intensive, less resource intensive"), lists
  ("10 hours or 20 hours or 40 hours"), emphasis ("way, way, way back"), the punchline
  ("It's time to build... build good"). Drop restatements ("now is the time" + "you can
  build it now").
- A clip should **stand alone**; cut references to other clips ("Again, ...").
- When a cut leaves a sentence reading oddly, flag it to the creator rather than guessing.

## 3. Pipeline

Scripts live in this skill's `scripts/` folder (`$V` below). Work files go in
`<clips folder>/cuts/work/`, which is durable (not a scratchpad). If raw clips arrive in
Downloads, copy the folder into the projects folder and work on the copy; leave the
originals until the creator says to delete them.

1. **Setup** (idempotent, seconds): `$V/setup.sh` installs a full ffmpeg build (zscale for
   HDR, libass for captions) into the skill's `bin/` and prints its path. Homebrew's ffmpeg
   lacks both; the renderer takes `-` to mean this one.
2. **Prepare** (one command, about 45 s per minute of video):
   `uv run -q --with mlx-whisper --with numpy python $V/prepare.py "<clips folder>"`
   writes per clip a 16 kHz wav, a word transcript (`<src>_w.json`), a phrase-by-phrase
   transcript split at pauses (`<src>_chunks.json`), and `inventory.txt` (length, codec,
   HDR flag, every phrase with source times). Pick the best take per topic from it.
3. **Find retakes in the phrase list, not the full transcript.** Whisper silently cleans
   up stutters, restarts and fillers in a whole-file transcript. The phrase list (each
   phrase transcribed alone with a disfluency prompt) exposes "I'm beginning." / "a lot
   of, a lot of reasons" / "Um," / "Dad." (=that). Tiny phrases read as "Thanks", "Thank
   you" or garbage are mouth noise: cut them. Words with implausibly long timings in
   `_w.json` (a "to" lasting 3.6 s) also hide retakes. Never batch files or leave
   `condition_on_previous_text` on: text leaks between clips and "Thank you" loops appear.
4. **Choose drops** in source seconds, each edge **inside a silence**, never mid-word.
   For tight spots run `$V/envelope.py <wav> a:b` (20 ms RMS in dB). Room tone on iPhone
   indoor clips sits around -48 to -52 dB, speech -25 to -35 dB; put the edge in the dip.
   - **Never end a keep right where a word's energy stops**: it is heard as a clipped word.
     Leave at least about 60 ms after the word falls to room tone (for sibilants, check a
     3.5 kHz high-passed envelope too), and keep the edge on the 1/30 s frame grid (66.1667,
     not 66.15, which snaps back to 66.133).
   - **Watch for run-together words** ("gates.So", "interaction-So"): the next word's first
     sound can start 10-20 ms after the end, so a 30 ms fade pulls in its "s" and the word
     is heard as "interactions". Cut on the last frame before the next onset and set a
     per-join `"xfade": {"<keep end>": 0.015}` in the edl so the fade covers only the decay.
   - The renderer prints `CHECK` lines for joins that end mid-word or may leak the next
     sound into the fade. Review every one (envelope at 10 ms, full and high band).
5. **Write `edl.json`** in `<clips folder>/cuts/` (format in the `render_cuts.py`
   docstring): one `[start, end, "reason"]` per drop, `holds` for deliberate pauses, `xfade`
   per join, and `caption_fixes` ({"exploring Gates": "exploring gates"}) for one-off
   caption text. Names Whisper mishears go in `glossary.json` so every future video gets
   them; add to it whenever a caption gets a name wrong. Never add a mis-transcription as
   an alias anywhere else.
6. **Render**: `cd "<clips folder>/cuts" && python3 $V/render_cuts.py - edl.json work --phone [name]`
   (about 1 min per clip; `--preview` renders 8 s to check colour and captions first). It:
   - tightens pauses over 0.4 s to 0.3 s, except `holds` (beats the creator asked to keep);
   - crossfades every join over 30 ms, so room tone never dips and words decay naturally
     (segments run 30 ms past the cut so length and lip sync stay exact);
   - builds captions by transcribing the finished cut itself, with no name prompt (a name
     prompt made Whisper change words), then fixes names from the glossary;
   - tone-maps HLG to SDR BT.709 (npl=203, hable), normalises to -14 LUFS with two-pass
     linear loudnorm (no pumping), burns captions (Avenir Next Heavy 116 px, lower third
     clear of the platform UI) and encodes H.264 CRF 21.
7. **Verify**: re-transcribe every output with `chunks.py` and compare with the captions;
   check `silencedetect` shows no gap over about 0.45 s; check video and audio stream
   durations match within about 2 frames (drift means lip-sync loss); look at a contact
   sheet of frames. State plainly that you checked by transcription and measurement, not by
   listening.
8. **Timestamps from the creator** ("remove 0:08-0:18", "clipped at 0:25", "let it breathe
   at 0:52") are seconds in the latest preview. Run
   `python3 $V/maptime.py edl.json <clip> work 0:08-0:18 0:25`: it prints the words there,
   widens a range to whole sentences (say so when it did), and suggests a drop with
   frame-grid edges. Check those edges with `envelope.py` before rendering.
9. **Previews**: phone viewers often cap uploads around 30 MB. `--phone` writes 720x1280
   copies to `previews/`; send those for review and post the full-quality files.

## 4. Posting

Hand finished clips to the `social-post` skill (captions, hashtags, titles, replies).
