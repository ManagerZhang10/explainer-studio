#!/usr/bin/env python3
"""HeyGen v3 precision 对口型（经 fal）：driver.mp4 + voice.mp3 -> work/lipsync/lipsync.mp4。约 0.1 美元/秒，2 分钟片要十几分钟。"""
import json, sys
from common import TOPIC
from studio.common import fal
video = sys.argv[1] if len(sys.argv) > 1 else TOPIC / 'work/lipsync/driver.mp4'
audio = sys.argv[2] if len(sys.argv) > 2 else TOPIC / 'work/tts/voice.mp3'
out = sys.argv[3] if len(sys.argv) > 3 else TOPIC / 'work/lipsync/lipsync.mp4'
vu = fal.upload(video); au = fal.upload(audio); print('uploaded', flush=True)
payload = {'video_url': vu, 'audio_url': au, 'enable_dynamic_duration': True, 'enable_caption': False, 'enable_speech_enhancement': False, 'disable_music_track': False}
r = fal.run('fal-ai/heygen/v3/lipsync/precision', payload, poll=10, log=lambda m: print(m, flush=True))
json.dump({'payload': payload, 'result': r}, open(str(out) + '.json', 'w'), ensure_ascii=False, indent=1)
fal.download(r['video']['url'], out); print('saved', out, flush=True)
