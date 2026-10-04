#!/usr/bin/env python3
"""按配音时间轴生成背景音乐（ElevenLabs Music v2.5，经 fal）-> work/bgm/bgm.mp3。
分段：开场（第一句）轻起 -> 讲解段稳定律动、给人声留空间 -> 最后一句收尾。风格取 topic.json 的 bgm.style（bright / dark）。
注意：composition_plan 不能和 force_instrumental 一起用，靠 negative_styles 去人声。
不用 AI 配乐时（config 的 providers.music = "none"，或 topic.json 写了 bgm.file）：用自己的曲子，按片长循环截好；都没有就不配乐。"""
import json, subprocess, sys
from common import cfg, mkdir, TOPIC, FF, resolve
from studio.common import config
c = cfg(); mkdir('work/bgm')
own = c.get('bgm', {}).get('file')
if own or config.provider('music') == 'none':
    if not own:
        sys.exit('providers.music = none：在 topic.json 的 bgm.file 写一首自己的曲子（免版税），或者不配乐直接 build')
    tl = json.load(open(TOPIC / 'work/timeline.json'))
    end = tl['duration'] + c.get('tail', 1.6) + 1.5
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-stream_loop', '-1', '-i', str(resolve(own)), '-t', f'{end:.2f}',
                    '-af', f'afade=t=out:st={end - 2.5:.2f}:d=2.5', '-ar', '48000', '-ac', '2', '-b:a', '192k', str(TOPIC / 'work/bgm/bgm.mp3')], check=True)
    sys.exit(print('saved work/bgm/bgm.mp3（自备曲子）'))
from studio.common import fal
tl = json.load(open(TOPIC / 'work/timeline.json'))
lines = tl['lines']
STYLES = {
  'bright': {'base': ['bright future garage', 'lo-fi house', 'warm electric piano', 'clean shuffled drums', 'optimistic tech', 'instrumental'],
             'intro': 'Soft airy intro: filtered warm keys and light ticking percussion, curious and building.',
             'groove': 'Light bouncy groove around 116 BPM, warm keys, soft bass, clean drums, lots of space for a voiceover, steady energy, subtle variation every 16 bars.',
             'outro': 'Gentle lift, final chord hit and a soft tail ending.'},
  'dark': {'base': ['dark minimal electronic', '808 sub bass', 'crisp hi-hats', 'tech', 'cinematic', 'instrumental'],
           'intro': 'Tense minimal intro: filtered pulsing sub synth, ticking hi-hats, rising suspense.',
           'groove': 'Steady minimal tech groove around 118 BPM, clean punchy drums, sparse synth motif, lots of space for a voiceover.',
           'outro': 'Short lift then a final hit and a clean tail ending.'},
}
style = sys.argv[1] if len(sys.argv) > 1 else c.get('bgm', {}).get('style', 'bright')
s = STYLES[style]
a = lines[0]['end'] + 0.2; b = lines[-1]['start'] - 0.3; end = tl['duration'] + c.get('tail', 1.6) + 1.5
ms = lambda x, y: int(round((y - x) * 1000))
# 单段上限 120 秒：讲解段按不超过 60 秒切开，后半段稍微丰满一点，避免两分钟一成不变
import math
n = max(1, math.ceil((b - a) / 60)); seg = (b - a) / n
VAR = ['', ' Slightly fuller arrangement, add a soft counter-melody.', ' Brief breakdown feel, then back to the groove.', ' Fullest section, same tempo.']
chunks = [{'text': '[Intro]', 'duration_ms': ms(0, a), 'positive_styles': s['base'] + [s['intro']]}]
for k in range(n):
    chunks.append({'text': f'[Groove {k + 1}]', 'duration_ms': ms(a + k * seg, a + (k + 1) * seg), 'positive_styles': s['base'] + [s['groove'] + VAR[k % len(VAR)]]})
chunks.append({'text': '[Outro]', 'duration_ms': ms(b, end), 'positive_styles': s['base'] + [s['outro']]})
for ch in chunks: ch['negative_styles'] = ['vocals', 'singing', 'lyrics', 'choir', 'spoken word']
payload = {'composition_plan': {'chunks': chunks}, 'output_format': 'mp3_48000_192', 'seed': 7}
r = fal.run('elevenlabs/music/v2.5', payload, log=lambda m: print(m, flush=True))
json.dump({'payload': payload, 'result': r}, open(TOPIC / 'work/bgm/bgm.json', 'w'), ensure_ascii=False, indent=1)
url = (r.get('audio') or {}).get('url') or r.get('audio_file', {}).get('url')
fal.download(url, TOPIC / 'work/bgm/bgm.mp3'); print('saved work/bgm/bgm.mp3', style)
