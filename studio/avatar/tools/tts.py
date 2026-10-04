#!/usr/bin/env python3
"""用克隆声音把 script.json 的 say 念成一整段配音（MiniMax speech-2.8-hd，经 fal）-> work/tts/voice.mp3。
语速取 topic.json 的 voice.speed（默认 1.12）；句间停顿取每句的 pause_after（默认 0.35 秒）。"""
import json, sys
from common import cfg, script, mkdir, TOPIC, resolve
from studio.common import fal
c = cfg(); d = script(); mkdir('work/tts')
cr = resolve(c['voice'].get('clone_result', 'work/voice/clone_result.json'))
voice = json.load(open(cr))['custom_voice_id']
speed = float(sys.argv[1]) if len(sys.argv) > 1 else c['voice'].get('speed', 1.12)
parts = []
for l in d['lines']:
    parts += [l['say'], f"<#{l.get('pause_after', 0.35):.2f}#>"]
payload = {'prompt': ''.join(parts[:-1]), 'output_format': 'url', 'language_boost': 'Chinese',
           'voice_setting': {'voice_id': voice, 'speed': speed, 'vol': 1, 'pitch': 0},
           'audio_setting': {'format': 'mp3', 'sample_rate': 44100, 'bitrate': 256000, 'channel': 1}}
r = fal.run('fal-ai/minimax/speech-2.8-hd', payload)
json.dump({'payload': payload, 'result': r}, open(TOPIC / 'work/tts/tts_result.json', 'w'), ensure_ascii=False, indent=1)
fal.download(r['audio']['url'], TOPIC / 'work/tts/voice.mp3')
(TOPIC / 'work/tts/voice_eq.wav').unlink(missing_ok=True)
print('duration_s', r.get('duration_ms', 0) / 1000)
