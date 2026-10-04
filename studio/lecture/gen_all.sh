#!/bin/zsh
set -u
cd "$(dirname "$0")"
run() {
  for d in $@; do
    [[ -f ../work/scripts/day${d}.json ]] && { echo "skip day${d}"; continue; }
    echo "=== gen day${d} start $(date +%H:%M:%S) ==="
    python3 gen_script.py ${d#0} 2>&1 | tail -3
  done
}
run 01 02 03 04 &
run 05 06 07 &
run 08 09 10 &
run 11 12 13 14 &
wait
echo "ALL_DONE $(date +%H:%M:%S)"
