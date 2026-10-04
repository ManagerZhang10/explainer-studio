#!/usr/bin/env python3
"""studio lecture <命令>：横屏讲义视频（讲义 -> 口播稿 -> 大字简图逐步动画 -> 成片）。
目录取 config.toml 的 [lecture]：course_docs（讲义 markdown）、course_slides（幻灯片）、project（出片项目）。"""
import os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
CMDS = {'draft': 'gen_script.py', 'render': 'build_video.py', 'audit': 'audit_pages.py', 'batch': 'run_batch.py', 'verify': 'verify_delivery.py'}
if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
    print(__doc__ + '\n  draft DAY            讲义 -> 口播稿（DeepSeek），写 work/scripts/dayNN.json\n  render DAY|--script JSON --project-dir DIR   出 HTML / 视频\n'
          '  audit DAY …          页面检查\n  batch …              批量出片\n  verify               成片解码与时长检查'); sys.exit(0 if len(sys.argv) < 2 else 2)
os.execv(sys.executable, [sys.executable, str(HERE / CMDS[sys.argv[1]]), *sys.argv[2:]])
