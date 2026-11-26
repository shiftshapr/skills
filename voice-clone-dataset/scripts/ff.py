"""Find an ffmpeg: $FFMPEG, then the video-cleanup skill's full build, then ffmpeg on PATH."""
import os, shutil

def ffmpeg():
    env = os.environ.get("FFMPEG")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    for skill in (os.path.join(here, "..", "..", "video-cleanup"),
                  os.path.expanduser("~/.claude/skills/video-cleanup")):
        ff = os.path.join(skill, "bin", "node_modules", "ffmpeg-static", "ffmpeg")
        if os.path.exists(ff):
            return ff
    ff = shutil.which("ffmpeg")
    if not ff:
        raise SystemExit("ffmpeg not found: install it, set FFMPEG, or run video-cleanup/scripts/setup.sh")
    return ff
