"""Join the parts that pass the voice check into one ElevenLabs upload.

  python3 finalize.py <out-name> <set-dir> [<set-dir> ...]

Each set dir has parts/*.wav, segments.json and voicecheck.json (from voicecheck.py).
A part is kept when every 1.5 s window scores >= 0.6 against the speaker's reference voice.
"""
import json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import ffmpeg  # noqa: E402
FF = ffmpeg()
name, sets = sys.argv[1], sys.argv[2:]
lst, kept, dropped, script = name + "_list.txt", 0, [], []
with open(lst, "w") as f:
    for d in sets:
        vc = json.load(open(os.path.join(d, "voicecheck.json")))
        seg = {x["n"]: x for x in json.load(open(os.path.join(d, "segments.json")))}
        for part, r in sorted(vc.items()):
            n = int(part.split(".")[0])
            if r["low_windows"] or r["mean"] < 0.7:
                dropped.append("%s/%s (mean %.2f): %s" % (d, part, r["mean"], seg[n]["text"][:90]))
                continue
            f.write("file '%s'\n" % os.path.abspath(os.path.join(d, "parts", part)))
            script.append(seg[n]["text"])
            kept += 1
raw = name + "_raw.wav"
subprocess.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:a", "pcm_s24le", raw], check=True)
m = subprocess.run([FF, "-hide_banner", "-i", raw, "-af", "loudnorm=I=-20:TP=-3:LRA=11:print_format=json",
                    "-f", "null", "-"], capture_output=True, text=True).stderr
j = json.loads(m[m.rindex("{"):])
ln = ("loudnorm=I=-20:TP=-3:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:"
      "offset=%s:linear=true" % (j["input_i"], j["input_tp"], j["input_lra"], j["input_thresh"], j["target_offset"]))
subprocess.run([FF, "-v", "error", "-y", "-i", raw, "-af", ln, "-ar", "48000", "-c:a", "pcm_s24le", name + ".wav"], check=True)
subprocess.run([FF, "-v", "error", "-y", "-i", name + ".wav", "-c:a", "libmp3lame", "-b:a", "192k", name + ".mp3"], check=True)
os.remove(raw)
open(name + "_dropped.txt", "w").write("\n".join(dropped) + "\n")
dur = subprocess.run([FF, "-hide_banner", "-i", name + ".wav"], capture_output=True, text=True).stderr
print("kept %d parts, dropped %d" % (kept, len(dropped)), [l.strip() for l in dur.splitlines() if "Duration" in l])
print("\n".join(dropped))
