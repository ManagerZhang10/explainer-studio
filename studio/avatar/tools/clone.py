#!/usr/bin/env python3
"""克隆声音：从 topic.json 的 camera.mic 截一段干净口播（voice.sample_start 起）-> 在 providers.voice 选的那家建一个复刻音色。
  fal / bailian：MiniMax，截 voice.sample_len 秒（默认 90）；fal 约 1.5 美元，百炼 9.9 元（要先在控制台开通 speech-2.8-hd）
  qwen / cosyvoice：阿里自家复刻，免费，样本 10–20 秒最好，超过 20 秒只取前 20 秒
各家的克隆结果不通用，分别存 work/voice/clone_result[_<家>].json。已有结果就不重复克隆，除非加 --force。"""
import json, sys, time, uuid
from common import cfg, ff, mkdir, TOPIC, resolve, clone_slot, bailian_tts_model
from studio.common import config
c = cfg(); v = c['voice']; mkdir('work/voice')
prov = config.provider('voice')
dst = TOPIC / clone_slot(prov)[1]
if dst.exists() and '--force' not in sys.argv: sys.exit(f'已有 {dst}，加 --force 才重新克隆')
seconds = v.get('sample_len', 90) if prov in ('fal', 'bailian') else min(20, v.get('sample_len', 20))
wav = TOPIC / 'work/voice/sample.wav'
ff('-ss', v.get('sample_start', 0), '-t', seconds, '-i', str(resolve(c['camera']['mic'])), '-ac', '1', '-ar', '44100', '-af', 'highpass=f=70,loudnorm=I=-18:TP=-2', str(wav))
preview = v.get('preview_text', '今天来拆一下这个模型，看看它到底改了哪几个零件。')
if prov == 'fal':
    from studio.common import fal
    url = fal.upload(wav); print('uploaded', flush=True)
    r = fal.run('fal-ai/minimax/voice-clone', {'audio_url': url, 'noise_reduction': True, 'need_volume_normalization': True, 'model': 'speech-02-hd', 'text': preview})
    json.dump(r, open(dst, 'w'), ensure_ascii=False, indent=1)
    if r.get('audio'): fal.download(r['audio']['url'], TOPIC / 'work/voice/clone_preview.mp3')
    print('voice_id', r.get('custom_voice_id'))
elif prov == 'bailian':
    from studio.common import bailian
    model = 'MiniMax/speech-2.8-hd'
    vid = f'studio{int(time.time())}{uuid.uuid4().hex[:6]}'  # 百炼要求：字母开头，只含字母数字 - _
    url = bailian.upload(wav, model); print('uploaded', flush=True)
    r = bailian.call('services/aigc/multimodal-generation/generation', {'model': model, 'input': {
        'action': 'voice_clone', 'voice_id': vid, 'audio_url': url, 'text': preview,
        'need_noise_reduction': True, 'need_volume_normalization': True, 'language_boost': 'Chinese'}}, oss=True)
    json.dump({'provider': prov, 'model': model, 'custom_voice_id': vid, 'result': r}, open(dst, 'w'), ensure_ascii=False, indent=1)
    if (r.get('output') or {}).get('demo_audio'): bailian.download(r['output']['demo_audio'], TOPIC / 'work/voice/clone_preview.mp3')
    print('voice_id', vid)
else:  # qwen / cosyvoice：百炼 voice-enrollment，免费
    from studio.common import bailian
    model = bailian_tts_model(prov)
    url = bailian.upload(wav, 'voice-enrollment'); print('uploaded', flush=True)
    r = bailian.call('services/audio/tts/customization', {'model': 'voice-enrollment', 'input': {
        'action': 'create_voice', 'target_model': model, 'prefix': 'studio', 'url': url,
        'language_hints': ['zh'], 'max_prompt_audio_length': float(seconds)}}, oss=True)
    vid = r['output']['voice_id']
    json.dump({'provider': prov, 'model': model, 'custom_voice_id': vid, 'result': r}, open(dst, 'w'), ensure_ascii=False, indent=1)
    print('voice_id', vid)
