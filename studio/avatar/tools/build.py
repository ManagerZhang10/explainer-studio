#!/usr/bin/env python3
"""出成片：渲染画面 -> 混音 -> 合成 -> out/<out_name>.mp4。build.py [--ver main] [--theme dark]"""
import subprocess, sys, time
from common import cfg, TOPIC, FF, PIPE
c = cfg()
ver = sys.argv[sys.argv.index('--ver') + 1] if '--ver' in sys.argv else 'main'
theme = ['--theme', sys.argv[sys.argv.index('--theme') + 1]] if '--theme' in sys.argv else []
t0 = time.time()
subprocess.run([sys.executable, str(PIPE / 'tools/render.py'), 'video', '--ver', ver, '--workers', '4', *theme], check=True)
subprocess.run([sys.executable, str(PIPE / 'tools/mix.py'), ver], check=True)
name = c.get('out_name', TOPIC.name) + ('' if ver == 'main' else f'_{ver}')
out = TOPIC / 'out' / f'{name}.mp4'; out.parent.mkdir(exist_ok=True)
subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(TOPIC / f'work/render/{ver}_silent.mp4'), '-i', str(TOPIC / f'work/render/{ver}_mix.m4a'),
                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart', str(out)], check=True)
print(f'DONE -> {out}  ({time.time() - t0:.0f}s)', flush=True)
