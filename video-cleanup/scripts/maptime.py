#!/usr/bin/env python3
"""Turn timestamps from a rendered clip into source times and a ready-to-paste drop.

  python3 maptime.py <edl.json> <clip-name> <work-dir> 0:08-0:18 [0:25 ...]

A range (a-b) is what the creator wants removed: prints the words it covers, widens it to
whole sentences, and suggests a drop whose edges sit after the last kept word has
decayed and before the next kept word starts, on the 1/30 s frame grid.
A single time (0:25) prints the source time and the words around it - use it for
"X is clipped at 0:25" or "let it breathe at 0:52".
Times use the keep list of the current edl.json, i.e. the latest render/preview.
"""
import importlib.util
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("rc", os.path.join(HERE, "render_cuts.py"))
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)


def secs(s):
    p = s.split(":")
    return float(p[-1]) + (int(p[-2]) * 60 if len(p) > 1 else 0)


def main():
    edl_path, name, work = sys.argv[1], sys.argv[2], sys.argv[3]
    edl = json.load(open(edl_path))
    clip = edl["clips"][name]
    clip = dict(clip, drops=[tuple(d[:2]) for d in clip.get("drops", [])],
                holds=[tuple(h[:2]) for h in clip.get("holds", [])])
    src = os.path.join(edl["src_dir"], clip["src"] + clip.get("ext", ".MOV"))
    ff = os.path.join(os.path.dirname(HERE), "bin/node_modules/ffmpeg-static/ffmpeg")
    if not os.path.exists(ff):  # first run: install the skill's ffmpeg build
        ff = subprocess.run([os.path.join(HERE, "setup.sh")], capture_output=True, text=True,
                            check=True).stdout.strip().splitlines()[-1]
    keeps = rc.keeps_for(clip, rc.silences(ff, src))
    offs, acc = [], 0.0
    for a, b in keeps:
        offs.append(acc)
        acc += b - a

    def to_src(t):
        for (a, b), o in zip(keeps, offs):
            if o <= t <= o + (b - a):
                return a + (t - o)
        return keeps[-1][1]

    words = [w for s in json.load(open(os.path.join(work, clip["src"] + "_w.json")))["segments"]
             for w in s.get("words", [])]
    def dropped(w):  # same rule as the captions in render_cuts.py
        mid = (w["start"] + w["end"]) / 2
        if mid < clip["start"] - 0.5 or mid > clip["end"]:
            return True
        return any(a <= mid <= b and w["end"] <= b + 0.15 for a, b in clip["drops"])
    kept = [w for w in words if not dropped(w)]

    def show(ws):
        return " ".join(w["word"].strip() for w in ws)

    for arg in sys.argv[4:]:
        if "-" in arg:
            oa, ob = map(secs, arg.split("-"))
            sa, sb = to_src(oa), to_src(ob)
            inside = [i for i, w in enumerate(kept) if w["end"] > sa and w["start"] < sb]
            if not inside:
                print("%s: no words there" % arg)
                continue
            i, j = inside[0], inside[-1]
            while i > 0 and kept[i - 1]["word"].strip()[-1] not in ".?!":
                i -= 1
            while j < len(kept) - 1 and kept[j]["word"].strip()[-1] not in ".?!":
                j += 1
            widened = (i, j) != (inside[0], inside[-1])
            prev_end = kept[i - 1]["end"] if i else clip["start"]
            next_start = kept[j + 1]["start"] if j + 1 < len(kept) else clip["end"]
            # edge after the previous word's decay; end just before the next word
            da = math.ceil((max(prev_end + 0.06, kept[i]["start"] - 0.25)) * 30) / 30
            db = math.floor((next_start - 0.03) * 30) / 30
            print("%s  -> source %.2f-%.2f" % (arg, sa, sb))
            print("  covers:  %s" % show(kept[inside[0]:inside[-1] + 1]))
            if widened:
                print("  widened to whole sentence(s): %s" % show(kept[i:j + 1]))
            print("  before:  ...%s" % show(kept[max(0, i - 8):i]))
            print("  after:   %s..." % show(kept[j + 1:j + 9]))
            print('  drop:    [%.4f, %.4f, "creator: remove %s"]' % (da, db, arg))
            print("  check the edges with envelope.py (word endings, run-together words) before rendering")
        else:
            t = secs(arg)
            s = to_src(t)
            near = sorted(kept, key=lambda w: abs((w["start"] + w["end"]) / 2 - s))[:1]
            k = kept.index(near[0])
            print("%s  -> source %.3f  near: ...%s [%s] %s..." % (
                arg, s, show(kept[max(0, k - 5):k]), near[0]["word"].strip(), show(kept[k + 1:k + 6])))
            print("  word %.2f-%.2f; nearest keep edges: %s" % (
                near[0]["start"], near[0]["end"],
                ", ".join("%.3f" % e for a, b in keeps for e in (a, b) if abs(e - s) < 1.5)))


if __name__ == "__main__":
    main()
