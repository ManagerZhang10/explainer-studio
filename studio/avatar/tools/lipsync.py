#!/usr/bin/env python3
"""对口型：driver.mp4 + voice.mp3 -> work/lipsync/lipsync.mp4。走哪家看 config 的 providers.lipsync：
  fal（默认）= HeyGen v3 precision，约 0.1 美元/秒，画质最好，2 分钟片要十几分钟；
  bailian     = 百炼 VideoRetalk，0.08 元/秒，国内直连；单段最长 120 秒、同时只跑一个任务，长片自动切段再拼，嘴型比 HeyGen 夸张一些。"""
import json, math, os, subprocess, sys
from common import TOPIC, FF, duration, mkdir
from studio.common import config
video = sys.argv[1] if len(sys.argv) > 1 else TOPIC / 'work/lipsync/driver.mp4'
audio = sys.argv[2] if len(sys.argv) > 2 else TOPIC / 'work/tts/voice.mp3'
out = sys.argv[3] if len(sys.argv) > 3 else TOPIC / 'work/lipsync/lipsync.mp4'
log = lambda m: print(m, flush=True)  # noqa: E731

if config.provider('lipsync') == 'bailian':
    from studio.common import bailian
    mkdir('work/lipsync/retalk'); tmp = TOPIC / 'work/lipsync/retalk'
    D = duration(audio); n = max(1, math.ceil(D / float(os.environ.get('STUDIO_RETALK_CHUNK', 110)))); seg = D / n
    # VideoRetalk 要求边长 640–2048、H.264：统一缩到长边 ≤1920
    vf = "scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(iw,ih),-2,min(1920,ih))'"
    parts, meta = [], []
    for k in range(n):
        a, b = k * seg, (k + 1) * seg
        v, w, o = tmp / f'v{k}.mp4', tmp / f'a{k}.wav', tmp / f'out{k}.mp4'
        if not o.exists():
            subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{a:.3f}', '-t', f'{b - a + (0.3 if k == n - 1 else 0):.3f}',
                            '-i', str(video), '-an', '-vf', vf, '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', str(v)], check=True)
            subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{a:.3f}', '-t', f'{b - a:.3f}', '-i', str(audio),
                            '-ac', '1', '-ar', '44100', str(w)], check=True)
            vu, au = bailian.upload(v, 'videoretalk'), bailian.upload(w, 'videoretalk')
            t = bailian.call('services/aigc/image2video/video-synthesis/', {'model': 'videoretalk', 'input': {'video_url': vu, 'audio_url': au}},
                             oss=True, async_=True)
            log(f'段 {k + 1}/{n}（{a:.1f}–{b:.1f}s）已提交 {t["output"]["task_id"]}')
            r = bailian.wait(t['output']['task_id'], poll=10, log=log)
            bailian.download(r['output']['video_url'], o); meta.append(r)
        parts.append(o)
    # 拼段并换上整段配音
    lst = tmp / 'concat.txt'; lst.write_text(''.join(f"file '{p}'\n" for p in parts))
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-i', str(audio),
                    '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(out)], check=True)
    json.dump({'provider': 'bailian', 'segments': n, 'tasks': meta}, open(str(out) + '.json', 'w'), ensure_ascii=False, indent=1)
    log(f'saved {out}')
else:
    from studio.common import fal
    vu = fal.upload(video); au = fal.upload(audio); log('uploaded')
    payload = {'video_url': vu, 'audio_url': au, 'enable_dynamic_duration': True, 'enable_caption': False, 'enable_speech_enhancement': False, 'disable_music_track': False}
    r = fal.run('fal-ai/heygen/v3/lipsync/precision', payload, poll=10, log=log)
    json.dump({'provider': 'fal', 'payload': payload, 'result': r}, open(str(out) + '.json', 'w'), ensure_ascii=False, indent=1)
    fal.download(r['video']['url'], out); log(f'saved {out}')
