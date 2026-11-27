"""Check how well the reference voice separates the target speaker from everyone else.

  uv run -q -p 3.11 --with resemblyzer --with 'setuptools<70' --with numpy \
      python calibrate.py <audio> <vtt> "<speaker name as in the VTT>" <ref_embedding.npy>

Scores every labelled VTT cue longer than 1.5 s against the reference embedding and prints,
per speaker, the median, the 95th percentile and the maximum. Pick extract_by_voice.py's KEEP
threshold above the highest other-speaker maximum and below most of the target's scores.
"""
import collections, os, re, subprocess, sys
import numpy as np
from resemblyzer import VoiceEncoder

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import ffmpeg  # noqa: E402

audio, vtt, me, ref_path = sys.argv[1:5]
wav = np.frombuffer(subprocess.run([ffmpeg(), "-v", "error", "-i", audio, "-ac", "1", "-ar", "16000",
                                    "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32)


def secs(x):
    h, m, s = x.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


ref = np.load(ref_path)
enc = VoiceEncoder("cpu", verbose=False)
scores = collections.defaultdict(list)
for a, b, txt in re.findall(r"(\d\d:\d\d:\d\d\.\d+) --> (\d\d:\d\d:\d\d\.\d+)\n(.+?)(?:\n\n|\Z)", open(vtt).read(), re.S):
    a, b = secs(a), secs(b)
    if b - a < 1.5:
        continue
    who = txt.split(":")[0] if ":" in txt.split("\n")[0] else "?"
    scores[who].append(float(enc.embed_utterance(wav[int(a * 16000):int(b * 16000)]) @ ref))
for who, v in sorted(scores.items(), key=lambda kv: kv[0] != me):
    v = np.array(v)
    tag = "TARGET " if who == me else "other  "
    print("%s%-28s n=%3d  median %.3f  p95 %.3f  max %.3f" % (tag, who[:28], len(v), np.median(v),
                                                             np.percentile(v, 95), v.max()))
