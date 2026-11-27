"""Find one speaker's speech in a recording with no speaker labels, by matching his reference voice.

  uv run -q -p 3.11 --with resemblyzer --with 'setuptools<70' --with mlx-whisper python extract_by_voice.py <audio> <ref.npy> <out-dir>

Whisper finds speech segments; each is scored against the reference embedding (from voicecheck.py
on a labelled recording). Adjacent matching segments are merged into parts. Writes parts/*.wav and
segments.json in the same format as build_set.py, so voicecheck.py and finalize.py work on it.
"""
import json, os, subprocess, sys
import numpy as np
import mlx_whisper
from resemblyzer import VoiceEncoder

audio_path, ref_path, out = sys.argv[1:4]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import ffmpeg  # noqa: E402
FF = ffmpeg()
# KEEP: calibrate on a speaker-labelled recording with calibrate.py. In the first use the target
# speaker's median was 0.90 and the closest other voice peaked at 0.77, so 0.80 kept others out.
# Override with the KEEP environment variable.
MIN_PART, MERGE_GAP = 5.0, 1.0
KEEP = float(os.environ.get("KEEP", "0.80"))
os.makedirs(os.path.join(out, "parts"), exist_ok=True)
pcm = subprocess.run([FF, "-v", "error", "-i", audio_path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
wav = np.frombuffer(pcm, np.float32)
tj = os.path.join(out, "whisper.json")
if not os.path.exists(tj):
    r = mlx_whisper.transcribe(wav, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="en",
                               condition_on_previous_text=False)
    json.dump([dict(start=s["start"], end=s["end"], text=s["text"].strip()) for s in r["segments"]], open(tj, "w"), indent=1)
segs = json.load(open(tj))
ref = np.load(ref_path)
enc = VoiceEncoder("cpu", verbose=False)
scored = []
for s in segs:
    a, b = s["start"], s["end"]
    if b - a < 1.0:
        continue
    x = wav[int(a * 16000):int(b * 16000)]
    if np.sqrt((x ** 2).mean()) < 1e-3:
        continue
    scored.append((a, b, float(enc.embed_utterance(x) @ ref), s["text"]))
mine = []
for a, b, sc, t in scored:
    if sc < KEEP:
        continue
    if mine and a - mine[-1][1] < MERGE_GAP:
        mine[-1] = (mine[-1][0], b, mine[-1][2] + " " + t)
    else:
        mine.append((a, b, t))
log = []
for a, b, t in [m for m in mine if m[1] - m[0] >= MIN_PART]:
    i = len(log)
    subprocess.run([FF, "-v", "error", "-y", "-ss", "%.3f" % max(0, a - 0.1), "-to", "%.3f" % (b + 0.15),
                    "-i", audio_path, "-ac", "1", "-ar", "48000", "-af",
                    "highpass=f=70,"
                    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.1,"
                    "silenceremove=stop_periods=-1:stop_duration=0.7:stop_threshold=-45dB:stop_silence=0.45,"
                    "apad=pad_dur=0.45", "-c:a", "pcm_s24le", os.path.join(out, "parts", "%03d.wav" % i)], check=True)
    log.append(dict(n=i, src_start=round(a, 2), src_end=round(b, 2), text=t))
json.dump(log, open(os.path.join(out, "segments.json"), "w"), indent=1)
hist = np.histogram([s[2] for s in scored], bins=[0, .5, .6, .65, .7, .72, .75, .8, 1])
print("segments scored %d; score histogram %s" % (len(scored), list(zip(hist[1][:-1].round(2), hist[0]))))
print("parts %d, %.1f min" % (len(log), sum(x["src_end"] - x["src_start"] for x in log) / 60))
