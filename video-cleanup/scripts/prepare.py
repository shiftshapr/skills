"""Prepare a folder of raw clips for cutting, in one command.

  uv run -q --with mlx-whisper --with numpy python prepare.py <clips-folder> [work-dir]

For every video in the folder (default work dir: <folder>/cuts/work) it writes:
  <src>.wav           16 kHz mono audio
  <src>_w.json        word-timestamp transcript (clean; used for captions)
  <src>_chunks.json   phrase-by-phrase transcript split at pauses, with a disfluency
                      prompt - this is what exposes retakes, fillers and false starts
  inventory.txt       length, size, codec, HDR flag, and the phrase list per clip
Existing outputs are reused unless --force.
"""
import json, os, re, subprocess, sys
import numpy as np
import mlx_whisper

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = "mlx-community/whisper-large-v3-turbo"
VIDEO = (".mov", ".mp4", ".m4v")


def load_glossary(skill):
    """glossary.json (your own, git-ignored) or the shipped glossary.example.json."""
    for name in ("glossary.json", "glossary.example.json"):
        path = os.path.join(skill, name)
        if os.path.exists(path):
            return json.load(open(path))
    return {}


def ffmpeg():
    return subprocess.run([os.path.join(SKILL, "scripts", "setup.sh")], capture_output=True,
                          text=True, check=True).stdout.strip().splitlines()[-1]


def probe(ff, path):
    err = subprocess.run([ff, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    secs = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3]) if dur else 0
    v = re.search(r"Video: (\w+).*?(\d{3,5})x(\d{3,5})", err)
    rot = re.search(r"rotation of (-?[\d.]+)", err)
    w, h = (int(v[2]), int(v[3])) if v else (0, 0)
    if rot and abs(float(rot[1])) == 90:
        w, h = h, w
    return dict(seconds=round(secs, 2), codec=v[1] if v else "?", size="%dx%d" % (w, h),
                hdr="arib-std-b67" in err or "smpte2084" in err)


def chunks(ff, wav, audio, prompt):
    err = subprocess.run([ff, "-hide_banner", "-i", wav, "-af", "silencedetect=noise=-38dB:d=0.2",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    ss = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    se = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    dur = len(audio) / 16000
    out, t = [], 0.0
    for a, b in zip(ss, se + [dur] * (len(ss) - len(se))):
        if a - t > 0.12:
            out.append((t, a))
        t = b
    if dur - t > 0.12:
        out.append((t, dur))
    res = []
    for a, b in out:
        seg = audio[int(max(0, a - 0.08) * 16000):int(min(dur, b + 0.08) * 16000)]
        r = mlx_whisper.transcribe(seg, path_or_hf_repo=MODEL, language="en",
                                   condition_on_previous_text=False,
                                   initial_prompt="Um, uh, I- I'm, like, the the, so so. " + prompt)
        res.append(dict(start=round(a, 3), end=round(b, 3), text=r["text"].strip()))
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    folder = os.path.abspath(args[0])
    work = os.path.abspath(args[1]) if len(args) > 1 else os.path.join(folder, "cuts", "work")
    os.makedirs(work, exist_ok=True)
    ff = ffmpeg()
    prompt = load_glossary(SKILL).get("prompt", "")
    inv = []
    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(VIDEO):
            continue
        src, path = os.path.splitext(name)[0], os.path.join(folder, name)
        info = probe(ff, path)
        wav = os.path.join(work, src + ".wav")
        if force or not os.path.exists(wav):
            subprocess.run([ff, "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
        raw = subprocess.run([ff, "-v", "error", "-i", wav, "-f", "f32le", "-"], capture_output=True).stdout
        audio = np.frombuffer(raw, np.float32)
        wj = os.path.join(work, src + "_w.json")
        if force or not os.path.exists(wj):
            # one file at a time, no conditioning: batching or conditioning leaks text between
            # clips and produces "Thank you" loops
            r = mlx_whisper.transcribe(audio, path_or_hf_repo=MODEL, language="en", word_timestamps=True,
                                       condition_on_previous_text=False)
            json.dump(r, open(wj, "w"), default=float)
        cj = os.path.join(work, src + "_chunks.json")
        if force or not os.path.exists(cj):
            json.dump(chunks(ff, wav, audio, prompt), open(cj, "w"), indent=1)
        ch = json.load(open(cj))
        inv.append("== %s  %.1fs  %s %s%s  %.0f MB" % (name, info["seconds"], info["size"], info["codec"],
                   "  HDR" if info["hdr"] else "", os.path.getsize(path) / 1e6))
        inv += ["  %7.2f-%7.2f  %s" % (c["start"], c["end"], c["text"]) for c in ch]
        print(inv[-len(ch) - 1], flush=True)
    open(os.path.join(work, "inventory.txt"), "w").write("\n".join(inv) + "\n")
    print("\n".join(inv))
    print("\nwork dir:", work)


if __name__ == "__main__":
    main()
