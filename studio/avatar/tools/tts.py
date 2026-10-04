#!/usr/bin/env python3
"""用克隆声音把 script.json 的 say 念成一整段配音（MiniMax speech-2.8-hd）-> work/tts/voice.mp3。
走哪家看 config 的 providers.voice（fal 或 bailian），克隆结果要和它同一家。
语速取 topic.json 的 voice.speed（默认 1.12）；句间停顿取每句的 pause_after（默认 0.35 秒）。"""
import json, sys
from common import cfg, script, mkdir, TOPIC, resolve
from studio.common import config
c = cfg(); d = script(); mkdir('work/tts')
prov = config.provider('voice')
key, default = ('clone_result_bailian', 'work/voice/clone_result_bailian.json') if prov == 'bailian' else ('clone_result', 'work/voice/clone_result.json')
cr = resolve(c['voice'].get(key) or default)
if not cr.exists():
    sys.exit(f'没有找到克隆结果 {cr}：先跑 studio avatar clone（providers.voice = {prov}），或在 topic.json 的 voice.{key} 指向已克隆好的结果')
clone = json.load(open(cr))
if clone.get('provider', 'fal') != prov:
    sys.exit(f'{cr} 是在 {clone.get("provider", "fal")} 上克隆的，现在 providers.voice = {prov}；两家的声音不通用，要在 {prov} 上重新 clone')
voice = clone['custom_voice_id']
speed = float(sys.argv[1]) if len(sys.argv) > 1 else c['voice'].get('speed', 1.12)
parts = []
for l in d['lines']:
    parts += [l['say'], f"<#{l.get('pause_after', 0.35):.2f}#>"]
text = ''.join(parts[:-1])
vs = {'voice_id': voice, 'speed': speed, 'vol': 1, 'pitch': 0}
au = {'format': 'mp3', 'sample_rate': 44100, 'bitrate': 256000, 'channel': 1}
out = TOPIC / 'work/tts/voice.mp3'
if prov == 'bailian':
    from studio.common import bailian
    payload = {'model': 'MiniMax/speech-2.8-hd', 'input': {'text': text, 'voice_setting': vs, 'audio_setting': au,
                                                           'language_boost': 'Chinese', 'output_format': 'url'}}
    r = bailian.call('services/aigc/multimodal-generation/generation', payload)
    o = r.get('output') or {}
    audio = (o.get('data') or {}).get('audio') or o.get('audio') or ''
    if audio.startswith('http'):
        bailian.download(audio, out)
    else:
        out.write_bytes(bytes.fromhex(audio))
    dur = (o.get('extra_info') or {}).get('audio_length', 0) / 1000
else:
    from studio.common import fal
    payload = {'prompt': text, 'output_format': 'url', 'language_boost': 'Chinese', 'voice_setting': vs, 'audio_setting': au}
    r = fal.run('fal-ai/minimax/speech-2.8-hd', payload)
    fal.download(r['audio']['url'], out)
    dur = r.get('duration_ms', 0) / 1000
json.dump({'provider': prov, 'payload': payload, 'result': r}, open(TOPIC / 'work/tts/tts_result.json', 'w'), ensure_ascii=False, indent=1)
(TOPIC / 'work/tts/voice_eq.wav').unlink(missing_ok=True)
print('duration_s', dur)
