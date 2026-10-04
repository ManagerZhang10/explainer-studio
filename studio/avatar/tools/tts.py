#!/usr/bin/env python3
"""用克隆声音把 script.json 的 say 念成一整段配音 -> work/tts/voice.mp3。走哪家看 config 的 providers.voice，克隆结果要是同一家的。
  fal / bailian（MiniMax）：整稿一次合成，语速取 topic.json 的 voice.speed（默认 1.12）
  qwen / cosyvoice：逐句合成再拼，语速取 voice.rate（默认 1.0，和 MiniMax 1.12 的快慢差不多）
句间停顿取每句的 pause_after（默认 0.35 秒）。"""
import json, subprocess, sys
from common import cfg, script, mkdir, TOPIC, FF, resolve, clone_slot, bailian_tts_model, VOICES
from studio.common import config
c = cfg(); d = script(); mkdir('work/tts')
prov = config.provider('voice')
key, default = clone_slot(prov)
cr = resolve(c['voice'].get(key) or default)
if not cr.exists():
    sys.exit(f'没有找到克隆结果 {cr}：先跑 studio avatar clone（providers.voice = {prov}），或在 topic.json 的 voice.{key} 指向已克隆好的结果')
clone = json.load(open(cr))
if clone.get('provider', 'fal') != prov:
    sys.exit(f'{cr} 是在 {VOICES.get(clone.get("provider", "fal"))} 上克隆的，现在 providers.voice = {prov}；各家的声音不通用，要重新 clone')
voice = clone['custom_voice_id']
out = TOPIC / 'work/tts/voice.mp3'
vs = {'voice_id': voice, 'speed': float(sys.argv[1]) if len(sys.argv) > 1 else c['voice'].get('speed', 1.12), 'vol': 1, 'pitch': 0}
au = {'format': 'mp3', 'sample_rate': 44100, 'bitrate': 256000, 'channel': 1}
text = ''.join([l['say'] + (f"<#{l.get('pause_after', 0.35):.2f}#>" if i < len(d['lines']) - 1 else '') for i, l in enumerate(d['lines'])])
if prov == 'fal':
    from studio.common import fal
    payload = {'prompt': text, 'output_format': 'url', 'language_boost': 'Chinese', 'voice_setting': vs, 'audio_setting': au}
    r = fal.run('fal-ai/minimax/speech-2.8-hd', payload)
    fal.download(r['audio']['url'], out)
elif prov == 'bailian':
    from studio.common import bailian
    payload = {'model': 'MiniMax/speech-2.8-hd', 'input': {'text': text, 'voice_setting': vs, 'audio_setting': au, 'language_boost': 'Chinese', 'output_format': 'url'}}
    r = bailian.call('services/aigc/multimodal-generation/generation', payload)
    o = r.get('output') or {}
    audio = (o.get('data') or {}).get('audio') or o.get('audio') or ''
    bailian.download(audio, out) if audio.startswith('http') else out.write_bytes(bytes.fromhex(audio))
else:  # qwen / cosyvoice：没有停顿标记，逐句合成后按 pause_after 补静音再拼
    from studio.common import bailian
    model = bailian_tts_model(prov); rate = float(sys.argv[1]) if len(sys.argv) > 1 else c['voice'].get('rate', 1.0)
    payload = {'model': model, 'voice': voice, 'rate': rate}; r = []; ins, fc = [], []
    for i, l in enumerate(d['lines']):
        res = bailian.call('services/audio/tts/SpeechSynthesizer', {'model': model, 'input': {
            'text': l['say'], 'voice': voice, 'format': 'mp3', 'sample_rate': 44100, 'rate': rate}})
        f = TOPIC / f'work/tts/line_{i:02d}.mp3'; bailian.download(res['output']['audio']['url'], f); r.append(res.get('usage'))
        pad = f",apad=pad_dur={l.get('pause_after', 0.35)}" if i < len(d['lines']) - 1 else ''
        ins += ['-i', str(f)]; fc.append(f'[{i}:a]aresample=44100,aformat=channel_layouts=mono{pad}[a{i}]')
    n = len(d['lines'])
    fc.append(''.join(f'[a{i}]' for i in range(n)) + f'concat=n={n}:v=0:a=1[o]')
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', *ins, '-filter_complex', ';'.join(fc), '-map', '[o]', '-b:a', '256k', str(out)], check=True)
json.dump({'provider': prov, 'payload': payload, 'result': r}, open(TOPIC / 'work/tts/tts_result.json', 'w'), ensure_ascii=False, indent=1)
(TOPIC / 'work/tts/voice_eq.wav').unlink(missing_ok=True)
e = subprocess.run([FF, '-hide_banner', '-i', str(out)], capture_output=True, text=True).stderr
print(VOICES[prov], 'duration', e.split('Duration: ')[1].split(',')[0])
