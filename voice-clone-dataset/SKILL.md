---
name: voice-clone-dataset
description: Build a clean 30-minute-plus recording of one person's voice for a voice clone (ElevenLabs Professional Voice Clone or similar) from recordings they already have - Zoom calls with speaker-labelled transcripts, talks, YouTube videos - keeping only their own speech, cutting around interruptions, checking every piece with a speaker-voice match, and levelling it to the upload spec. Use when the creator wants a voice clone, a voice dataset, or "the best of my voice" from existing videos.
---

# Voice clone dataset

Goal: one file of **only the target speaker**, 30 minutes or more, clean and consistent,
ready to upload to a voice-cloning service. Only make a dataset of the person asking, or of
someone who has clearly agreed: cloning services also ask the speaker to verify their voice.

Runs on a Mac with Apple silicon. Needs `uv` and ffmpeg (the `video-cleanup` skill's
`setup.sh` installs a full build that these scripts find on their own; or set `FFMPEG`).
Scripts are in `scripts/` (`$S` below). Keep the work folder somewhere durable.

Python tools run through uv:
`R="uv run -q -p 3.11 --with resemblyzer --with setuptools<70 --with numpy"` (add
`--with mlx-whisper` for `extract_by_voice.py`).

## 1. Find sources, best first

1. **Calls with a speaker-labelled transcript**: Zoom cloud recordings come with an audio
   file and a `.vtt` whose cues start with `Name:`. These are the best sources: every turn is
   labelled. Ask the creator to download the transcript for each recording you will use.
2. **Solo talks and videos** (their own YouTube channel, course videos): one voice, but check
   it is really them. Narrated videos can be an AI voice or someone else.
3. **Calls without labels**: usable only through the voice match below, and least reliable:
   in testing, segments above the threshold still mixed in other speakers' lines.

Skip AI-generated podcasts about their work (the voices are not theirs) and anything with
music under the voice. Prefer one recording setup throughout: a clone takes on the mic and
room of its training audio. A phone-mic clip mixed into Zoom audio blurs the result.

## 2. Labelled calls

`python3 $S/build_set.py <audio> <vtt> "<Name as in the VTT>" <set-dir>`

Merges the speaker's consecutive cues into turns, cuts each turn around anyone else's cue
(plus a 0.6 s guard) instead of dropping the whole turn, keeps pieces of 5 s or more, trims
pauses over 0.7 s, and writes `parts/*.wav` and `segments.json` (what each piece says and
where it came from). Splitting around interruptions roughly doubled the usable audio in
testing.

## 3. Check every piece against the speaker's voice

`$R python $S/voicecheck.py <set-dir>/parts`

Scores each 1.5 s window of each piece against the median voice of all pieces and saves
`ref_embedding.npy` beside the set. Expect the speaker around 0.8; anything near 0.55 is
someone else. **Transcripts mislabel**: in testing, a fitness class leaking into the
speaker's mic during a break was labelled as them, and only the voice check caught it.
Read `segments.json` for every flagged piece.

## 4. Calibrate before trusting the match on new sources

`$R python $S/calibrate.py <audio> <vtt> "<Name>" <ref_embedding.npy>`

On a labelled call, prints each speaker's scores against the reference. Set the threshold
above every other speaker's maximum (in testing: target median 0.90, closest other voice up
to 0.77, so 0.80). Voices of the same gender and accent overlap most.

## 5. Unlabelled and solo sources

- `$R python $S/scan.py <ref_embedding.npy> <files...>` scores 10 s windows across whole
  files. A solo talk by the speaker scores high almost everywhere; a video that scores low
  throughout is not them.
- `KEEP=0.80 $R --with mlx-whisper python $S/extract_by_voice.py <audio> <ref.npy> <set-dir>`
  transcribes, keeps segments scoring at or above `KEEP`, merges neighbours and writes a set
  in the same format. Then run `voicecheck.py <set-dir>/parts <labelled-set>/parts` (the
  second argument makes the labelled set the reference) and read every piece's text: a line
  addressed to the speaker by name ("David, this makes sense...") means another voice got in.

## 6. Join and level

`python3 $S/finalize.py <out-name> <set-dir> [<set-dir> ...]`

Keeps pieces whose every window scores at least 0.6 and whose mean is at least 0.7, joins
them, levels to -20 LUFS with peaks under -3 dB (inside ElevenLabs' requested range), and
writes `<out-name>.wav` (24-bit 48 kHz), a 192 kbps `.mp3`, the join list and
`<out-name>_dropped.txt` with the reason for each dropped piece.

## 7. Verify and hand over

- Transcribe the final file and read it for other people's words, names used in address,
  music or breaks.
- Report: total length, sources and minutes from each, what was dropped and why, and that
  you checked by transcript and voice match, not by listening.
- Upload guidance: ElevenLabs' professional clone wants at least 30 minutes, ideally more
  (up to about 3 hours); an instant clone needs only 1-2 minutes, good for a quick test. The
  service asks the speaker to read a verification phrase. Nothing is uploaded without the
  creator doing it or saying to.
- Best quality comes from 30-60 minutes of the speaker reading aloud in a quiet room on the
  mic they will use for voiceovers. Say so when the dataset is built from call audio.
