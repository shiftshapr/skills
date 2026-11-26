"""Build a voice-cloning set of one speaker talking alone, from a Zoom recording + its speaker-labelled VTT.

  python3 build_set.py <audio> <vtt> "<speaker name as in the VTT>" <out-dir> [target-minutes]

Keeps only the speaker's turns that are at least MIN_TURN s long and have no other speaker within
GUARD s, shortens long pauses, joins them with short gaps, and levels to ElevenLabs' range.
"""
import json, os, re, subprocess, sys

ME = None  # set from the command line
MIN_TURN, GUARD, JOIN_GAP, PAD = 5.0, 0.6, 1.2, 0.15
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import ffmpeg  # noqa: E402
FF = ffmpeg()


def secs(x):
    h, m, s = x.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def turns(vtt):
    blocks = re.findall(r"(\d\d:\d\d:\d\d\.\d+) --> (\d\d:\d\d:\d\d\.\d+)\n(.+?)(?:\n\n|\Z)", open(vtt).read(), re.S)
    cues = []
    for a, b, txt in blocks:
        m = re.match(r"([^:\n]{2,40}):\s*(.*)", txt, re.S)
        cues.append((secs(a), secs(b), m[1] if m else "?", (m[2] if m else txt).replace("\n", " ")))
    mine, others = [], [(a, b) for a, b, who, _ in cues if who != ME]
    for a, b, who, t in cues:
        if who != ME:
            continue
        if mine and a - mine[-1][1] < JOIN_GAP and not any(oa < a and ob > mine[-1][1] for oa, ob in others):
            mine[-1] = (mine[-1][0], b, mine[-1][2] + " " + t)
        else:
            mine.append((a, b, t))
    # cut each turn around anyone else's speech (plus a guard) and keep the clean pieces
    ok = []
    for a, b, t in mine:
        pieces = [(a, b)]
        for oa, ob in others:
            nxt = []
            for pa, pb in pieces:
                if oa - GUARD < pb and ob + GUARD > pa:
                    nxt += [x for x in ((pa, oa - GUARD), (ob + GUARD, pb)) if x[1] > x[0]]
                else:
                    nxt.append((pa, pb))
            pieces = nxt
        whole = len(pieces) == 1 and pieces[0] == (a, b)
        ok += [(pa, pb, t if whole else "(part) " + t) for pa, pb in pieces if pb - pa >= MIN_TURN]
    return ok


def main():
    global ME
    audio, vtt, ME, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    target = float(sys.argv[5]) * 60 if len(sys.argv) > 5 else 1e9
    os.makedirs(os.path.join(out, "parts"), exist_ok=True)
    ts = sorted(turns(vtt), key=lambda x: x[1] - x[0], reverse=True)  # longest, most fluent turns first
    chosen, total = [], 0.0
    for t in ts:
        if total >= target:
            break
        chosen.append(t)
        total += t[1] - t[0]
    chosen.sort()
    lst = open(os.path.join(out, "parts", "list.txt"), "w")
    log = []
    for i, (a, b, text) in enumerate(chosen):
        p = os.path.join(out, "parts", "%03d.wav" % i)
        subprocess.run([FF, "-v", "error", "-y", "-ss", "%.3f" % max(0, a - PAD), "-to", "%.3f" % (b + PAD),
                        "-i", audio, "-ac", "1", "-ar", "48000", "-af",
                        "highpass=f=70,"
                        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.1,"
                        "silenceremove=stop_periods=-1:stop_duration=0.7:stop_threshold=-45dB:stop_silence=0.45,"
                        "apad=pad_dur=0.45", "-c:a", "pcm_s24le", p], check=True)
        lst.write("file '%s'\n" % os.path.abspath(p))
        log.append(dict(n=i, src_start=round(a, 2), src_end=round(b, 2), text=text))
    lst.close()
    raw = os.path.join(out, "raw.wav")
    subprocess.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst.name, "-c", "copy", raw], check=True)
    # ElevenLabs asks for roughly -23 to -18 dB RMS with peaks under -3 dB
    m = subprocess.run([FF, "-hide_banner", "-i", raw, "-af", "loudnorm=I=-20:TP=-3:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):])
    ln = ("loudnorm=I=-20:TP=-3:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:"
          "offset=%s:linear=true" % (j["input_i"], j["input_tp"], j["input_lra"], j["input_thresh"], j["target_offset"]))
    name = os.path.join(out, "voice-set")
    subprocess.run([FF, "-v", "error", "-y", "-i", raw, "-af", ln, "-ar", "48000", "-c:a", "pcm_s24le", name + ".wav"], check=True)
    subprocess.run([FF, "-v", "error", "-y", "-i", name + ".wav", "-c:a", "libmp3lame", "-b:a", "192k", name + ".mp3"], check=True)
    json.dump(log, open(os.path.join(out, "segments.json"), "w"), indent=1)
    print("turns kept %d of %d qualifying; source speech %.1f min -> %s" % (len(chosen), len(ts), total / 60, name + ".wav"))


if __name__ == "__main__":
    main()
