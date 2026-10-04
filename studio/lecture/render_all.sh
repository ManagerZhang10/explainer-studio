#!/bin/zsh
export PATH="$HOME/.local/bin:$PATH"
set -u
cd "$(dirname "$0")"
W="$1"; shift
for d in "$@"; do
  echo "### W$W day$d start $(date +%H:%M:%S)" >> ../logs/render_$W.log
  /usr/local/bin/python3 build_video.py $d --scale 0.6667 >> ../logs/render_$W.log 2>&1 \
    && echo "### W$W day$d OK $(date +%H:%M:%S)" >> ../logs/render_$W.log \
    || echo "### W$W day$d FAIL $(date +%H:%M:%S)" >> ../logs/render_$W.log
done
echo "### W$W ALLDONE $(date +%H:%M:%S)" >> ../logs/render_$W.log
