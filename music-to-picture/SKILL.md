---
name: music-to-picture
description: Choose, generate and fit music to a short video - write a Suno prompt for the mood, compare candidate tracks by measuring their loudness shape, find the biggest quiet-to-loud moment, place it on the video's key frame (a title, a reveal, a punchline), keep the lead-in quiet, optionally add a bass drop, and mix it in without re-encoding the picture. Use when a short needs music, when the creator shares tracks to try, or says the music is not dramatic enough.
---

# Music to picture

A short's music works when its one big moment lands on the video's one big moment. This skill
finds that moment in a track by measurement and puts it on the right frame.

Script: `scripts/music_fit.py` (`$M` below). It needs only Python 3 and ffmpeg (the
`video-cleanup` skill's build is found automatically, or set `FFMPEG`). Keep music in the
video project's own `music/` folder.

## 1. Brief the music

Name the video's key frame first (for example "the title card at 17.5 s, as the sky turns
gold"), then the arc: what plays under the setup, the build, the hit, the tail.

Direction ideas for optimistic, cosmic or big-idea shorts:
- **Cosmic sunrise** (the *2001* idea): low organ drone, rising brass, timpani, one huge
  chord. Use the shape, never the famous recordings: they are copyrighted and get muted or
  claimed, and the Strauss fanfare now reads as a joke.
- **Warm 1980s synth** (Vangelis-like): cosmic but human.
- **Piano and strings** (Richter, Arnalds-like): the most emotional; sits well under a voice.
- **Uplifting ambient electronic** (Tycho, M83-like): current and feed-friendly.

Suno rejects artist and composer names, so describe the sound. First drafts tend to be too
polite: if the creator says "not dramatic enough", push the style words (fortissimo,
monumental, thundering timpani, giant choir, extreme dynamic contrast), put the climax only
one or two sections in, and generate four to six takes. A prompt that worked:

Style (Instrumental on):
```
epic cinematic trailer, massive full orchestra fortissimo, thundering timpani, huge brass fanfare, pipe organ pedal, giant choir, deep sub drops, extreme dynamic contrast, from silence to overwhelming, awe, triumphant, goosebumps, monumental
```
Lyrics box (structure tags only):
```
[Intro: almost silent, single deep organ note, rumbling sub]
[Brass: three-note rising fanfare, loud, bold]
[Timpani: pounding, alternating hits]
[Climax: enormous full orchestra and choir, fortissimo, blazing major chord]
[Outro: final chord rings for a long time]
[End]
```
Under a voiceover, add `sparse, quiet, leaves space for narration`.

**Licensing**: post only tracks made on a paid Suno plan (free-plan songs are not licensed
for commercial use, and promoting anything can count). Never use commercial recordings.

**Getting the file**: Suno's share links serve an encrypted stream, so they cannot be
downloaded or measured. Ask the creator to download each candidate (song menu > Download >
WAV or MP3). Do not try to get around the encryption.

## 2. Measure the candidates

`python3 $M chart music/a.wav music/b.wav`

Prints each track's loudness every 4 s, its dynamic range and its five biggest 2-second
jumps. Most generated tracks stay loud almost the whole way; what you want is one window
with a quiet stretch followed by the biggest jump in the track. Then:

- `python3 $M zoom music/a.wav 140 170` to see the build in quarter seconds;
- `python3 $M onset music/a.wav 162.4` to find where the hit really starts (50 ms steps).

Choose by the size of the jump into the hit, not by overall loudness. Say you judged by
measurement and that the creator's ear decides.

## 3. Fit and mix

`python3 $M mix <video> <track> <track-hit> <video-hit> <out.mp4> --build 3.4:5.0 [--bass]`

- Places the track so `<track-hit>` plays at `<video-hit>`; the picture is copied, never
  re-encoded.
- `--lead 0.42` holds the music low until the build, then ramps to full over `--build`, so the
  setup stays quiet and the hit has further to climb. If a loud accent sits early in the
  window, start the ramp after it.
- `--bass` adds a sub drop on the hit (a 95 to 36 Hz sweep fading over about 4 s, plus a short
  thump): about 3 dB more punch over the first 1.5 s on headphones. Phone speakers cannot
  play it, and most short-video viewers are on phones, so it is a bonus, not the fix.
- Then check the shape: `python3 $M levels <out.mp4> 5:16 16:17.5 17.5:19 19:22`.
  A good result in testing: setup about -23 dB, build -21 dB, hit -8 dB.

**What did not work**: cutting the music to silence for half a second before the hit, to make
it land harder. The creator rejected it. Keep the build continuous into the hit.

## 4. Hand over

Send the preview, say what lands where (a short table: video time, on screen, music), that it
was judged by measurement and not by listening, and offer one change at a time ("make it
bigger" next means the bass drop or a stronger take, not silence). When the creator picks a
final, name it `<project>-final.mp4` and delete the rejected mixes so only one current
version exists.
