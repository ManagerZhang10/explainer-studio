#!/usr/bin/env python3
"""把成片压小、切两半，交给 Gemini 看画面听声音，回一份 JSON 质检意见。qc.py out/x.mp4 r1；Gemini 走 .env 里的 GEMINI_BASE_URL，单次请求体 >~1.5MB 会被中转拒绝，所以压成 270×480"""
import base64, json, subprocess, sys, os
from common import FF, PIPE, TOPIC, env
os.chdir(TOPIC)
src, tag = sys.argv[1], sys.argv[2]
cfg = env()
dur = float(subprocess.run([FF, '-i', src], capture_output=True, text=True).stderr.split('Duration: ')[1].split(',')[0].split(':')[2]) + 60
PROMPT = open(PIPE / 'tools/qc_prompt.txt').read()
res = []
os.makedirs('work/qc', exist_ok=True)
for k, (a, b) in enumerate([(0, dur / 2 + 1), (dur / 2 - 1, dur)]):
    clip = f'work/qc/{tag}_part{k}.mp4'
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(a), '-to', str(b), '-i', src, '-vf', 'scale=270:480,fps=15',
                    '-c:v', 'libx264', '-crf', '34', '-preset', 'fast', '-c:a', 'aac', '-b:a', '40k', '-ac', '1', clip], check=True)
    body = {'contents': [{'parts': [{'text': PROMPT + f'\n（这是全片第 {k + 1}/2 段，从原片第 {a:.0f} 秒开始。）'},
                                    {'inline_data': {'mime_type': 'video/mp4', 'data': base64.b64encode(open(clip, 'rb').read()).decode()}}]}],
            'generationConfig': {'temperature': 0.3, 'responseMimeType': 'application/json'}}
    bf = f'work/qc/{tag}_body{k}.json'; json.dump(body, open(bf, 'w'))
    out = subprocess.run(['curl', '-sS', f"{cfg['GEMINI_BASE_URL'].rstrip('/')}/models/{cfg.get('GEMINI_MODEL', 'gemini-3.8-flash')}:generateContent", '-H', 'Content-Type: application/json',
                          '-H', f"x-goog-api-key: {cfg['GEMINI_API_KEY']}", '--data', '@' + bf, '--max-time', '400'], capture_output=True, text=True).stdout
    os.remove(bf)
    try: res.append(json.loads(json.loads(out)['candidates'][0]['content']['parts'][0]['text']))
    except Exception: res.append({'raw': out[:800]})
json.dump(res, open(f'work/qc/{tag}_gemini.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
