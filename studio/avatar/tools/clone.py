#!/usr/bin/env python3
"""克隆声音：从 topic.json 的 camera.mic 截一段干净口播（voice.sample_start 起 voice.sample_len 秒）-> MiniMax 声音复刻。
走哪家看 config 的 providers.voice：fal（默认）或 bailian（百炼，9.9 元/次，要先在控制台开通 MiniMax speech-2.8-hd）。
两家的克隆结果不通用，分别存 work/voice/clone_result.json 和 clone_result_bailian.json。已有结果就不重复花钱，除非加 --force。"""
import json, sys, time, uuid
from common import cfg, ff, mkdir, TOPIC, resolve
from studio.common import config
c = cfg(); v = c['voice']; mkdir('work/voice')
prov = config.provider('voice')
dst = TOPIC / ('work/voice/clone_result_bailian.json' if prov == 'bailian' else 'work/voice/clone_result.json')
if dst.exists() and '--force' not in sys.argv: sys.exit(f'已有 {dst}，加 --force 才重新克隆')
wav = TOPIC / 'work/voice/sample.wav'
ff('-ss', v.get('sample_start', 0), '-t', v.get('sample_len', 90), '-i', str(resolve(c['camera']['mic'])), '-ac', '1', '-ar', '44100', '-af', 'highpass=f=70,loudnorm=I=-18:TP=-2', str(wav))
preview = v.get('preview_text', '今天来拆一下这个模型，看看它到底改了哪几个零件。')
if prov == 'bailian':
    from studio.common import bailian
    model = 'MiniMax/speech-2.8-hd'
    vid = f'studio{int(time.time())}{uuid.uuid4().hex[:6]}'  # 百炼要求：字母开头，只含字母数字 - _
    url = bailian.upload(wav, model); print('uploaded', flush=True)
    r = bailian.call('services/aigc/multimodal-generation/generation', {'model': model, 'input': {
        'action': 'voice_clone', 'voice_id': vid, 'audio_url': url, 'text': preview,
        'need_noise_reduction': True, 'need_volume_normalization': True, 'language_boost': 'Chinese'}}, oss=True)
    json.dump({'provider': 'bailian', 'model': model, 'custom_voice_id': vid, 'result': r}, open(dst, 'w'), ensure_ascii=False, indent=1)
    if (r.get('output') or {}).get('demo_audio'): bailian.download(r['output']['demo_audio'], TOPIC / 'work/voice/clone_preview.mp3')
    print('voice_id', vid)
else:
    from studio.common import fal
    url = fal.upload(wav); print('uploaded', flush=True)
    r = fal.run('fal-ai/minimax/voice-clone', {'audio_url': url, 'noise_reduction': True, 'need_volume_normalization': True, 'model': 'speech-02-hd', 'text': preview})
    json.dump(r, open(dst, 'w'), ensure_ascii=False, indent=1)
    if r.get('audio'): fal.download(r['audio']['url'], TOPIC / 'work/voice/clone_preview.mp3')
    print('voice_id', r.get('custom_voice_id'))
