#!/usr/bin/env python3
"""把成片压小、切两半，交给视觉模型连看带听，回一份 JSON 质检意见：studio avatar qc out/x.mp4 r1。
模型按 config 的 providers.vision：gemini（默认）或 bailian（千问全模态）。压成 270×480，部分中转服务拒收 1.5MB 以上的请求体。"""
import json, subprocess, sys, os
from common import FF, PIPE, TOPIC
from studio.common import vision
os.chdir(TOPIC)
src, tag = sys.argv[1], sys.argv[2]
dur = float(subprocess.run([FF, '-i', src], capture_output=True, text=True).stderr.split('Duration: ')[1].split(',')[0].split(':')[2]) + 60
PROMPT = open(PIPE / 'tools/qc_prompt.txt').read()
res = []
os.makedirs('work/qc', exist_ok=True)
for k, (a, b) in enumerate([(0, dur / 2 + 1), (dur / 2 - 1, dur)]):
    clip = f'work/qc/{tag}_part{k}.mp4'
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(a), '-to', str(b), '-i', src, '-vf', 'scale=270:480,fps=15',
                    '-c:v', 'libx264', '-crf', '34', '-preset', 'fast', '-c:a', 'aac', '-b:a', '40k', '-ac', '1', clip], check=True)
    try:
        res.append(vision.ask_json(PROMPT + f'\n（这是全片第 {k + 1}/2 段，从原片第 {a:.0f} 秒开始。）', video=clip, listen=True))
    except Exception as e:  # noqa: BLE001
        res.append({'error': f'{type(e).__name__}: {str(e)[:600]}'})
json.dump(res, open(f'work/qc/{tag}_qc.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
