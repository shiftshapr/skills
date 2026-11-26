"""Split a 16k mono wav into speech chunks at silences and transcribe each chunk alone.
usage: uv run --with mlx-whisper python chunks.py <ffmpeg> <wav> <out.json>
"""
import json, re, subprocess, sys
import numpy as np
import mlx_whisper

ff, wav, out = sys.argv[1:4]
err = subprocess.run([ff, "-hide_banner", "-i", wav, "-af", "silencedetect=noise=-38dB:d=0.2",
                      "-f", "null", "-"], capture_output=True, text=True).stderr
ss = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
se = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
raw = subprocess.run([ff, "-v", "error", "-i", wav, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                     capture_output=True).stdout
audio = np.frombuffer(raw, np.float32)
dur = len(audio) / 16000
sil = list(zip(ss, se + [dur] * (len(ss) - len(se))))
chunks, t = [], 0.0
for a, b in sil:
    if a - t > 0.12:
        chunks.append((t, a))
    t = b
if dur - t > 0.12:
    chunks.append((t, dur))
res = []
for a, b in chunks:
    seg = audio[int(max(0, a - 0.08) * 16000):int(min(dur, b + 0.08) * 16000)]
    r = mlx_whisper.transcribe(seg, path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                               language="en", condition_on_previous_text=False,
                               initial_prompt="Um, uh, I- I'm, like, the the, so so.")
    txt = r["text"].strip()
    res.append(dict(start=round(a, 3), end=round(b, 3), text=txt))
    print("%7.2f-%7.2f  %s" % (a, b, txt), flush=True)
json.dump(res, open(out, "w"), indent=1)
