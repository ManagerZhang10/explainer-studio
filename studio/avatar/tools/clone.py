#!/usr/bin/env python3
"""克隆声音：从 topic.json 的 camera.mic 截一段干净口播（voice.sample_start 起 voice.sample_len 秒）-> MiniMax voice-clone。
已有 work/voice/clone_result.json 就不重复花钱，除非加 --force。也可以在 topic.json 里用 voice.clone_result 指向别的专题已克隆好的结果。"""
import json, sys
from common import cfg, ff, mkdir, TOPIC, resolve
from studio.common import fal
c = cfg(); v = c['voice']; mkdir('work/voice')
dst = TOPIC / 'work/voice/clone_result.json'
if dst.exists() and '--force' not in sys.argv: sys.exit(f'已有 {dst}，加 --force 才重新克隆')
wav = TOPIC / 'work/voice/sample.wav'
ff('-ss', v.get('sample_start', 0), '-t', v.get('sample_len', 90), '-i', str(resolve(c['camera']['mic'])), '-ac', '1', '-ar', '44100', '-af', 'highpass=f=70,loudnorm=I=-18:TP=-2', str(wav))
url = fal.upload(wav); print('uploaded', flush=True)
r = fal.run('fal-ai/minimax/voice-clone', {'audio_url': url, 'noise_reduction': True, 'need_volume_normalization': True, 'model': 'speech-02-hd',
                                            'text': v.get('preview_text', '今天来拆一下这个模型，看看它到底改了哪几个零件。')})
json.dump(r, open(dst, 'w'), ensure_ascii=False, indent=1)
if r.get('audio'): fal.download(r['audio']['url'], TOPIC / 'work/voice/clone_preview.mp3')
print('voice_id', r.get('custom_voice_id'))
