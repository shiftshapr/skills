"""Fit a music track to a short video so its biggest moment lands on a chosen frame.

  python3 music_fit.py chart  <track> [<track> ...]      loudness every 4 s + biggest jumps
  python3 music_fit.py zoom   <track> <from> <to>        loudness every 0.25 s in a range
  python3 music_fit.py onset  <track> <around-seconds>   where the hit really starts (50 ms steps)
  python3 music_fit.py mix    <video> <track> <track-hit> <video-hit> <out.mp4> [options]
  python3 music_fit.py levels <video> <t1:t2> [<t1:t2> ...]   measured loudness of the result

mix options:
  --lead 0.42        gain before the build (quiet pulses make the hit bigger)
  --build 3.4:5.0    ramp from --lead to full gain over this span of the video (seconds)
  --fade-in 0.4 --fade-out 1.7
  --bass             add a sub drop on the hit: a 95->36 Hz sweep plus a short 55 Hz thump
  --peak -1          peak level in dBFS before the limiter

The track is placed so <track-hit> (seconds in the track) plays at <video-hit> (seconds in
the video); the video stream is copied, never re-encoded.
"""
import json, math, os, re, shutil, struct, subprocess, sys


def ffmpeg():
    if os.environ.get("FFMPEG"):
        return os.environ["FFMPEG"]
    here = os.path.dirname(os.path.abspath(__file__))
    for skill in (os.path.join(here, "..", "..", "video-cleanup"), os.path.expanduser("~/.claude/skills/video-cleanup")):
        ff = os.path.join(skill, "bin", "node_modules", "ffmpeg-static", "ffmpeg")
        if os.path.exists(ff):
            return ff
    ff = shutil.which("ffmpeg")
    if not ff:
        raise SystemExit("ffmpeg not found: install it or set FFMPEG")
    return ff


FF = ffmpeg()
RATE = 8000


def pcm(path, start=None, dur=None):
    cmd = [FF, "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(start)]
    if dur is not None:
        cmd += ["-t", str(dur)]
    raw = subprocess.run(cmd + ["-i", path, "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return struct.unpack("<%dh" % (len(raw) // 2), raw)


def db(x):
    if not x:
        return -90.0
    r = math.sqrt(sum(v * v for v in x) / len(x)) / 32768
    return 20 * math.log10(r + 1e-6)


def bar(d, floor=-50):
    return "#" * max(0, int(d - floor))


def duration(path):
    err = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def chart(paths):
    for p in paths:
        x = pcm(p)
        sec = [db(x[i * RATE:(i + 1) * RATE]) for i in range(len(x) // RATE)]
        q = sorted(sec)[len(sec) // 10] if sec else -90
        print("\n%s  %.1f s  loudest %.1f dB  quietest 10%% %.1f dB  range %.1f dB"
              % (p, len(x) / RATE, max(sec), q, max(sec) - q))
        jumps = sorted(((sec[i + 2] - sec[i], i + 1) for i in range(len(sec) - 2)), reverse=True)[:5]
        print("  biggest 2 s jumps (dB, at s):", [(round(a, 1), b) for a, b in jumps])
        for i in range(0, len(sec), 4):
            d = sum(sec[i:i + 4]) / len(sec[i:i + 4])
            print("  %4d-%4ds %s %.0f" % (i, i + 4, bar(d), d))


def zoom(path, a, b, step=0.25):
    x = pcm(path, a, b - a)
    n = int(step * RATE)
    for i in range(0, len(x) - n + 1, n):
        d = db(x[i:i + n])
        print("%8.2f %s %.0f" % (a + i / RATE, bar(d), d))


def onset(path, around):
    a = max(0.0, around - 1.5)
    x = pcm(path, a, 3.0)
    n = int(0.05 * RATE)
    levels = [(a + i / RATE, db(x[i:i + n])) for i in range(0, len(x) - n + 1, n)]
    base = sorted(d for _, d in levels[:20])[10]
    for t, d in levels:
        if d > base + 6:
            print("onset about %.2f s (%.0f dB over a %.0f dB bed)" % (t, d - base, base))
            break
    for t, d in levels:
        print("%7.2f %s %.0f" % (t, bar(d), d))


def mix(args):
    video, track, track_hit, video_hit, out = args[:5]
    opt = {"--lead": "0.42", "--build": None, "--fade-in": "0.4", "--fade-out": "1.7", "--peak": "-1"}
    bass = "--bass" in args
    rest = [a for a in args[5:] if a != "--bass"]
    for k, v in zip(rest[::2], rest[1::2]):
        opt[k] = v
    vdur = duration(video)
    start = float(track_hit) - float(video_hit)
    if start < 0:
        raise SystemExit("the track hit comes too early for that video time")
    lead = float(opt["--lead"])
    if opt["--build"]:
        b0, b1 = (float(v) for v in opt["--build"].split(":"))
    else:
        b0, b1 = max(0.0, float(video_hit) - 1.6), float(video_hit)
    gain = "if(lt(t,%g),%g,if(lt(t,%g),%g+%g*(t-%g)/%g,1))" % (b0, lead, b1, lead, 1 - lead, b0, b1 - b0)
    fo = float(opt["--fade-out"])
    af = ("atrim=start=%.3f:duration=%.3f,asetpts=PTS-STARTPTS,volume='%s':eval=frame,"
          "afade=t=in:d=%s,afade=t=out:st=%.3f:d=%.3f" % (start, vdur, gain, opt["--fade-in"], vdur - fo, fo))
    err = subprocess.run([FF, "-hide_banner", "-i", track, "-af", af + ",volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    peak = float(re.search(r"max_volume: (-?[\d.]+) dB", err).group(1))
    g = float(opt["--peak"]) - peak
    graph = "[1:a]%s,volume=%.2fdB[m]" % (af, g)
    if bass:
        ms = int(float(video_hit) * 1000)
        graph += (";aevalsrc='0.75*exp(-0.9*t)*sin(2*PI*(36*t+(59/2.5)*(1-exp(-2.5*t))))"
                  "+0.5*exp(-9*t)*sin(2*PI*55*t)':s=48000:d=5,afade=t=out:st=3.5:d=1.5,"
                  "pan=stereo|c0=c0|c1=c0,adelay=%d:all=1[s];[m][s]amix=inputs=2:normalize=0:duration=first[mm]" % ms)
        last = "[mm]"
    else:
        last = "[m]"
    graph += ";%salimiter=limit=0.89:attack=2:release=60[a]" % last
    subprocess.run([FF, "-v", "error", "-y", "-i", video, "-i", track, "-filter_complex", graph,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                    "-t", "%.3f" % vdur, out], check=True)
    print("wrote %s: track %.2f s plays at video %.2f s; music gain %+.1f dB%s"
          % (out, float(track_hit), float(video_hit), g, ", bass drop on the hit" if bass else ""))


def levels(video, spans):
    x = pcm(video)
    for s in spans:
        a, b = (float(v) for v in s.split(":"))
        print("%6.2f-%6.2f s  %.1f dB" % (a, b, db(x[int(a * RATE):int(b * RATE)])))


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "chart":
        chart(args)
    elif cmd == "zoom":
        zoom(args[0], float(args[1]), float(args[2]))
    elif cmd == "onset":
        onset(args[0], float(args[1]))
    elif cmd == "mix":
        mix(args)
    elif cmd == "levels":
        levels(args[0], args[1:])
    else:
        raise SystemExit(__doc__)
