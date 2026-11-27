#!/usr/bin/env python3
"""Cut talking-head phone clips into clean, captioned, post-ready vertical videos.

  python3 render_cuts.py - <edl.json> <work-dir> [--preview] [--phone] [name ...]

"-" uses the skill's own ffmpeg (scripts/setup.sh installs it). --preview renders 8 s to
check colour/captions; --phone also writes previews/<name>-preview.mp4 (720p, <30 MB)
for reviewing on a phone. Caption names are fixed from ../glossary.json (or glossary.example.json) + edl "fixes".

edl.json: {"src_dir": "...", "out_dir": "...", "fixes": {"Jon": "John"},
           "clips": {"1-name": {"src": "IMG_0001", "start": 0.4, "end": 72.2,
                                "drops": [[20.2, 24.7, "why it goes"], ...],
                                "holds": [[86.66, 87.48, "let it breathe"]]}}}
<words-json-dir>/<src>_w.json is mlx_whisper JSON output with word timestamps.

For each clip: drop the listed ranges, tighten pauses longer than PAUSE_MIN,
convert iPhone HDR (HLG) to SDR H.264 1080x1920, normalise loudness to -14 LUFS (two-pass, linear: no pumping)
and burn in captions built from Whisper word timings.
"""
import array
import json
import math
import os
import re
import subprocess
import sys

FPS = 30
PAUSE_MIN = 0.4   # pauses longer than this get tightened...
PAUSE_PAD = 0.15  # ...to this much on each side (0.3s gap between phrases)
SIL_DB = -38      # room tone on these clips sits at -48..-52 dB, speech at -25..-35
XFADE = 0.03      # audio crossfade at every join: no clicks, no dips, natural decay

CLIPS, FIXES, SRC, OUT = {}, {}, ".", "."

ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Avenir Next Heavy,116,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,7,2,2,60,60,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def silences(ff, path):
    err = subprocess.run([ff, "-hide_banner", "-i", path, "-vn", "-af",
                          "silencedetect=noise=%ddB:d=0.3" % SIL_DB, "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    s = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    e = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    return list(zip(s, e))


def snap(t):
    return round(t * FPS) / FPS


def keeps_for(clip, sil):
    cuts = list(clip["drops"])
    holds = clip.get("holds", [])  # source ranges kept as-is: a deliberate beat/breath
    for s, e in sil:
        if any(s < hb and e > ha for ha, hb in holds):
            continue
        if e - s >= PAUSE_MIN:
            cuts.append((s + PAUSE_PAD, e - PAUSE_PAD))
    cuts.sort()
    keeps, t = [], clip["start"]
    for s, e in cuts:
        if e <= t:
            continue
        if s >= clip["end"]:
            break
        if s > t:
            keeps.append((t, s))
        t = max(t, e)
    if t < clip["end"]:
        keeps.append((t, clip["end"]))
    keeps = [(snap(a), snap(b)) for a, b in keeps]
    return [(a, b) for a, b in keeps if b - a >= 0.2]


def mapper(keeps):
    offs, acc = [], 0.0
    for a, b in keeps:
        offs.append(acc)
        acc += b - a

    def m(t, end=False):
        for i, (a, b) in enumerate(keeps):
            if t < a:
                # in a removed gap: ends snap back to previous keep, starts forward
                return offs[i] if not (end and i) else offs[i]
            if t <= b:
                return offs[i] + (t - a)
        return acc
    return m, acc


def fix_word(word):
    """Glossary fix, case-insensitive, keeping trailing punctuation: 'Jon.' -> 'John.'"""
    core = word.rstrip(".,?!")
    rep = FIXES.get(core.lower())
    return rep + word[len(core):] if rep else word


def captions(words, clip, keeps):
    m, total = mapper(keeps)
    ws = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        if mid < clip["start"] - 0.5 or mid > clip["end"]:
            continue
        if any(a <= mid <= b and w["end"] <= b + 0.15 for a, b in clip["drops"]):
            continue
        txt = fix_word(w["word"].strip())
        for ft, fw in clip.get("word_fixes", []):  # [[source_time, "replacement"]]
            if abs(w["start"] - ft) < 0.06:
                txt = fw
        s, e = m(w["start"]), m(w["end"], True)
        ws.append([txt, s, max(e, s + 0.12)])
    for i in range(len(ws) - 1):  # comma left dangling by a cut, e.g. 'building, is going'
        if ws[i][0].endswith(",") and ws[i + 1][0] == "is":
            ws[i][0] = ws[i][0][:-1]
    for i, w in enumerate(ws):  # sentence case survives the cuts
        if i == 0 or ws[i - 1][0][-1] in ".?!":
            w[0] = w[0][:1].upper() + w[0][1:]
        elif ws[i - 1][0][-1] == "," and w[0] in ("And", "But", "So", "That", "To"):
            w[0] = w[0].lower()
    chunks, cur = [], []
    for w in ws:
        cur.append(w)
        text = " ".join(x[0] for x in cur)
        if w[0][-1] in ".?!," or len(cur) >= 3 or len(text) >= 16:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    ev = []
    for i, c in enumerate(chunks):
        s, e = c[0][1], c[-1][2]
        if i + 1 < len(chunks):
            nxt = chunks[i + 1][0][1]
            e = nxt if nxt - e < 0.8 else e + 0.3
        e = min(max(e, s + 0.25), total)
        ev.append((s, e, " ".join(x[0] for x in c)))
    return ev, total


def captions_cut(words, total, phrase_fixes):
    ws = [[fix_word(w["word"].strip()), w["start"], max(w["end"], w["start"] + 0.12)] for w in words
          if w["word"].strip()]
    norm = lambda t: t.lower().strip(".,?!")
    for old, new in phrase_fixes.items():  # {"gates and transistors": "gates in transistors"}
        o = old.split()
        for i in range(len(ws) - len(o) + 1):
            if [norm(x[0]) for x in ws[i:i + len(o)]] == [norm(x) for x in o]:
                tail = ws[i + len(o) - 1][0][len(ws[i + len(o) - 1][0].rstrip(".,?!")):]
                ws[i:i + len(o)] = [[new + tail, ws[i][1], ws[i + len(o) - 1][2]]]
                break
    for i, w in enumerate(ws):
        if i == 0 or ws[i - 1][0][-1] in ".?!":
            w[0] = w[0][:1].upper() + w[0][1:]
    chunks, cur = [], []
    for w in ws:
        cur.append(w)
        if w[0][-1] in ".?!," or len(cur) >= 3 or len(" ".join(x[0] for x in cur)) >= 16:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    ev = []
    for i, c in enumerate(chunks):
        cs, ce = c[0][1], c[-1][2]
        if i + 1 < len(chunks):
            nxt = chunks[i + 1][0][1]
            ce = nxt if nxt - ce < 0.8 else ce + 0.3
        ev.append((cs, min(max(ce, cs + 0.25), total), " ".join(x[0] for x in c)))
    return ev


def ts(t):
    cs = int(round(t * 100))
    return "%d:%02d:%02d.%02d" % (cs // 360000, cs // 6000 % 60, cs // 100 % 60, cs % 100)


class Envelope:
    """Source audio at 16 kHz for checking what sits either side of every cut."""

    def __init__(self, ff, path):
        raw = subprocess.run([ff, "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000",
                              "-f", "f32le", "-"], capture_output=True).stdout
        self.x = array.array("f")
        self.x.frombytes(raw[: len(raw) // 4 * 4])
        full = sorted(self.db(i * 0.02, i * 0.02 + 0.02) for i in range(int(len(self.x) / 320) - 1))
        hi = sorted(self.db(i * 0.02, i * 0.02 + 0.02, True) for i in range(int(len(self.x) / 320) - 1))
        self.floor, self.hifloor = full[len(full) // 10], hi[len(hi) // 10]

    def db(self, a, b, high=False):
        i, j = max(1, int(a * 16000)), min(len(self.x), int(b * 16000))
        if j <= i:
            return -120.0
        x = self.x
        if high:  # first difference ~ high-pass: sibilants and consonant onsets
            e = sum((x[k] - x[k - 1]) ** 2 for k in range(i, j)) / (j - i)
        else:
            e = sum(x[k] * x[k] for k in range(i, j)) / (j - i)
        return 10 * math.log10(e + 1e-12)

    def loud(self, t, w=0.006):
        return (self.db(t, t + w) > self.floor + 12) or (self.db(t, t + w, True) > self.hifloor + 22)

    def free_after(self, b, limit):
        """Seconds after b before the next sound starts (capped at limit)."""
        t = b
        while t < b + limit:
            if self.loud(t):
                return t - b
            t += 0.002
        return limit

    def report(self, keeps, xf):
        warn = []
        for i, (a, b) in enumerate(keeps):
            if i and self.db(a, a + 0.01) > self.floor + 12:
                warn.append("starts mid-sound at %.3f" % a)
            if i < len(keeps) - 1:
                if self.db(b - 0.012, b) > self.floor + 18:
                    warn.append("ends mid-word at %.3f (%.0f dB over room tone)" % (b, self.db(b - 0.012, b) - self.floor))
                gap = self.free_after(b + 0.012, xf[i])  # skip the word's own decay
                if gap < xf[i] - 0.012:
                    warn.append("next sound may start ~%.0f ms after cut at %.3f (inside the %.0f ms "
                                "fade) - listen; set edl xfade for %.2f if it leaks"
                                % ((gap + 0.012) * 1000, b, xf[i] * 1000, b))
        return warn


def main():
    global CLIPS, FIXES, SRC, OUT
    ff, edl_path, wdir = sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
    skill = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if ff == "-":
        ff = subprocess.run([os.path.join(skill, "scripts", "setup.sh")], capture_output=True,
                            text=True, check=True).stdout.strip().splitlines()[-1]
    edl = json.load(open(edl_path))
    SRC, OUT = edl["src_dir"], edl["out_dir"]
    gl = next((os.path.join(skill, n) for n in ("glossary.json", "glossary.example.json")
               if os.path.exists(os.path.join(skill, n))), None)
    FIXES = {k.lower(): v for k, v in (json.load(open(gl)).get("fix", {}) if gl else {}).items()}
    FIXES.update({k.lower().rstrip(".,?!"): v.rstrip(".,?!") for k, v in edl.get("fixes", {}).items()})
    CLIPS = {k: dict(v, drops=[tuple(d[:2]) for d in v.get("drops", [])],
                     holds=[tuple(h[:2]) for h in v.get("holds", [])]) for k, v in edl["clips"].items()}
    os.makedirs(OUT, exist_ok=True)
    rest = sys.argv[4:]
    preview = "--preview" in rest
    names = [a for a in rest if not a.startswith("--")] or list(CLIPS)
    os.chdir(OUT)
    for name in names:
        clip = CLIPS[name]
        src = os.path.join(SRC, clip["src"] + clip.get("ext", ".MOV"))
        keeps = keeps_for(clip, silences(ff, src))
        sel = "+".join("between(t,%.4f,%.4f)" % (a - 0.5 / FPS, b - 0.5 / FPS) for a, b in keeps)
        # Each segment runs XFADE past its cut and is crossfaded into the next, so room tone
        # never dips at a join and word endings decay instead of stopping dead. Total length
        # is unchanged, so audio stays in sync with the hard video cuts.
        n = len(keeps)
        env = Envelope(ff, src)
        # Crossfade per join. Default XFADE; edl "xfade": {"<keep end, source s>": seconds}
        # shortens it where the next (removed) word starts within 30 ms of the cut. A fade
        # that runs through a word's own decay sounds natural; ending it early sounds clipped.
        over = {round(float(k), 2): v for k, v in clip.get("xfade", {}).items()}
        xf = [over.get(round(b, 2), XFADE) for a, b in keeps]
        for w in env.report(keeps, xf):
            print("  CHECK %s: %s" % (name, w), flush=True)
        aparts = "".join(
            "[0:a]atrim=%.4f:%.4f,asetpts=PTS-STARTPTS%s[s%d];"
            % (a, b + (xf[i] if i < n - 1 else 0),
               ",afade=t=in:d=0.005" if i == 0 else (",afade=t=out:st=%.4f:d=0.01" % (b - a - 0.01) if i == n - 1 else ""),
               i) for i, (a, b) in enumerate(keeps))
        prev = "s0"
        for i in range(1, n):
            aparts += "[%s][s%d]acrossfade=d=%.4f:c1=tri:c2=tri[x%d];" % (prev, i, xf[i - 1], i)
            prev = "x%d" % i
        aconcat = "[%s]" % prev
        # Captions come from transcribing the finished cut itself, so they always match what
        # is heard (the raw transcript merges retakes and drifts around cuts).
        cut_wav = os.path.join(wdir, name + "_cut.wav")
        subprocess.run([ff, "-y", "-v", "error", "-i", src, "-filter_complex",
                        aparts + aconcat + "aresample=16000,aformat=channel_layouts=mono[o]",
                        "-map", "[o]", cut_wav], check=True)
        # no initial prompt here: a name prompt made Whisper rewrite words ('next week' ->
        # 'this week', an extra 'Now,'). Names are fixed afterwards from the glossary.
        subprocess.run(["uvx", "--from", "mlx-whisper", "mlx_whisper", cut_wav, "--model",
                        "mlx-community/whisper-large-v3-turbo", "--language", "en",
                        "--word-timestamps", "True", "--condition-on-previous-text", "False",
                        "--output-format", "json",
                        "--output-name", name + "_cut", "--output-dir", wdir, "--verbose", "False"],
                       check=True, capture_output=True)
        words = [w for sg in json.load(open(os.path.join(wdir, name + "_cut.json")))["segments"]
                 for w in sg.get("words", [])]
        total = sum(b - a for a, b in keeps)
        ev = captions_cut(words, total, clip.get("caption_fixes", {}))
        with open(name + ".ass", "w") as f:
            f.write(ASS_HEAD)
            for cs, ce, text in ev:
                f.write("Dialogue: 0,%s,%s,Cap,,0,0,0,,%s\n" % (ts(cs), ts(ce), text))
        with open(name + ".txt", "w") as f:
            f.write(" ".join(t for _, _, t in ev) + "\n")
        vf = ("[0:v]fps=%d,select='%s',setpts=N/%d/TB,"
              "zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=203,format=gbrpf32le,"
              "zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
              "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,ass=%s.ass[v];"
              "%s%sloudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"
              % (FPS, sel, FPS, name, aparts, aconcat))
        meas = subprocess.run([ff, "-hide_banner", "-i", src, "-filter_complex",
                               aparts + aconcat + "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                               "-f", "null", "-"], capture_output=True, text=True).stderr
        mj = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
        ln = ("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I=%s:measured_TP=%s:"
              "measured_LRA=%s:measured_thresh=%s:offset=%s" % (mj["input_i"], mj["input_tp"],
              mj["input_lra"], mj["input_thresh"], mj["target_offset"]))
        vf = vf.replace("loudnorm=I=-14:TP=-1.5:LRA=11,", ln + ",")
        out = name + ("-preview.mp4" if preview else ".mp4")
        cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-filter_complex", vf,
               "-map", "[v]", "-map", "[a]"] + (["-t", "8"] if preview else []) + [
               "-c:v", "libx264", "-crf", "21", "-maxrate", "10M", "-bufsize", "20M", "-preset", "medium", "-pix_fmt", "yuv420p",
               "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
               "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", out]
        print("%s: %d kept ranges, %.1fs (from %.1fs)" % (name, len(keeps), total, clip["end"]), flush=True)
        subprocess.run(cmd, check=True)
        print("  wrote", out, flush=True)
        if "--phone" in rest and not preview:
            os.makedirs("previews", exist_ok=True)
            subprocess.run([ff, "-y", "-v", "error", "-i", out, "-vf", "scale=720:1280", "-c:v", "libx264",
                            "-preset", "medium", "-b:v", "2200k", "-maxrate", "2500k", "-bufsize", "5000k",
                            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
                            os.path.join("previews", name + "-preview.mp4")], check=True)
            print("  wrote previews/%s-preview.mp4" % name, flush=True)


if __name__ == "__main__":
    main()
