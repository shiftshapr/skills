#!/bin/zsh
# One-time (idempotent) setup for the video-cleanup skill.
# Installs a full ffmpeg build (zscale for HDR->SDR, libass for captions) inside the skill
# folder so it survives scratchpad cleanups, and warms the Whisper model.
# Prints the ffmpeg path on the last line.
set -e
SKILL="${0:A:h:h}"
BIN="$SKILL/bin"
FF="$BIN/node_modules/ffmpeg-static/ffmpeg"
if [[ ! -x "$FF" ]]; then
  mkdir -p "$BIN"
  (cd "$BIN" && [[ -f package.json ]] || npm init -y >/dev/null 2>&1)
  npm i --prefix "$BIN" ffmpeg-static >/dev/null 2>&1
fi
for f in zscale ass tonemap loudnorm; do
  "$FF" -hide_banner -filters 2>/dev/null | grep -q " $f " || { echo "ffmpeg at $FF lacks $f" >&2; exit 1; }
done
command -v uv >/dev/null || { echo "uv is missing (needed for mlx-whisper)" >&2; exit 1; }
command -v ffprobe >/dev/null || echo "note: Homebrew ffprobe not found; prepare.py falls back to ffmpeg" >&2
echo "$FF"
