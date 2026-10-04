#!/usr/bin/env python3
"""截口型驱动底片：camera.video 从 camera.start 起，长度 = 配音时长 + 0.3 秒，混入同段麦克风（HeyGen 要求有音轨、时长接近）。
挑段要求：人在正常说话、手不挡嘴、头肩完整。-> work/lipsync/driver.mp4"""
from common import cfg, ff, duration, mkdir, TOPIC, resolve
c = cfg()['camera']; mkdir('work/lipsync')
d = duration(TOPIC / 'work/tts/voice.mp3') + 0.3
s = c.get('start', 0)
ff('-ss', s, '-t', f'{d:.2f}', '-i', str(resolve(c['video'])), '-ss', s, '-t', f'{d:.2f}', '-i', str(resolve(c['mic'])), '-map', '0:v', '-map', '1:a',
   '-vf', c.get('grade', 'null'), '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-shortest',
   str(TOPIC / 'work/lipsync/driver.mp4'))
print(f'driver {d:.2f}s from {s}s -> work/lipsync/driver.mp4')
