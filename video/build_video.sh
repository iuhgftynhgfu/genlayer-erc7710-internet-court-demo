#!/usr/bin/env bash
# Build the <=45s vertical (9:16) demo video from the rendered slides.
# 7 slides x 5.5s = 38.5s + 0.5s fades. Requires: python3 + Pillow + cairosvg, ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
VENV="../.venv/bin/python"
if [ -x "$VENV" ]; then PY="$VENV"; else PY="python3"; fi
"$PY" build_video.py
# Each slide held 5.5s; concat demuxer, then fade in/out.
cat > frames/concat.txt <<'EOF'
file 's1.png'
duration 5.5
file 's2.png'
duration 5.5
file 's3.png'
duration 5.5
file 's4.png'
duration 5.5
file 's5.png'
duration 6.5
file 's6.png'
duration 5.5
file 's7.png'
duration 5.5
EOF
ffmpeg -y -v error -f concat -safe 0 -i frames/concat.txt -t 40 \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fade=t=in:st=0:d=0.5,fade=t=out:st=39.0:d=1.0,format=yuv420p" \
  -r 30 -c:v libx264 -pix_fmt yuv420p -movflags +faststart delegate-and-defend-demo.mp4
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 delegate-and-defend-demo.mp4
