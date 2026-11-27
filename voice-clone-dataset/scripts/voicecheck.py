"""Score how much each 1.5 s window of each part sounds like the target speaker (resemblyzer speaker embeddings).

  uv run -q -p 3.11 --with resemblyzer --with 'setuptools<70' python voicecheck.py <parts-dir> [ref-dir]

Reference voice = the median embedding of all parts (most of them are the target speaker by construction).
Prints per-part min window similarity; low minimum = someone else, music, or noise in that part.
"""
import glob, json, os, sys
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

parts = sorted(glob.glob(os.path.join(sys.argv[1], "*.wav")))
ref_dir = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
enc = VoiceEncoder("cpu", verbose=False)
emb = {}
for p in parts:
    w = preprocess_wav(p)
    _, partial, _ = enc.embed_utterance(w, return_partials=True, rate=1.3)
    emb[p] = partial
refs = sorted(glob.glob(os.path.join(ref_dir, "*.wav")))
ref = np.median(np.vstack([emb[p].mean(0) if p in emb else enc.embed_utterance(preprocess_wav(p)) for p in refs]), 0)
ref /= np.linalg.norm(ref)
out = {}
for p in parts:
    s = emb[p] @ ref
    out[os.path.basename(p)] = dict(mean=round(float(s.mean()), 3), min=round(float(s.min()), 3),
                                    low_windows=[int(i) for i in np.where(s < 0.6)[0]])
    print("%s  mean %.3f  min %.3f  low %d/%d" % (os.path.basename(p), s.mean(), s.min(), (s < 0.6).sum(), len(s)))
np.save(os.path.join(sys.argv[1], "..", "ref_embedding.npy"), ref)
json.dump(out, open(os.path.join(sys.argv[1], "..", "voicecheck.json"), "w"), indent=1)
