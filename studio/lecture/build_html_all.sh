#!/bin/zsh
export PATH="$HOME/.local/bin:$PATH"
set -u
cd "$(dirname "$0")"
for d in $(seq -w 1 14); do
  dd=${d#0}
  echo "=== day${d} $(date +%H:%M:%S) ==="
  /usr/local/bin/python3 build_video.py $dd --html 2>&1 | tail -2
done
echo "HTML_ALL_DONE $(date +%H:%M:%S)"
