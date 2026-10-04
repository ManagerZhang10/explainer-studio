#!/usr/bin/env python3
"""本机 mlx_whisper 给配音出逐词时间 -> work/tts/voice_words.json（对齐用；听错的字不要紧，align 按字符对齐稿子）。"""
import subprocess, json
from common import TOPIC, config
subprocess.run([config.get('tools', 'mlx_whisper', 'mlx_whisper'), 'voice.mp3', '--model', 'mlx-community/whisper-large-v3-turbo', '--language', 'zh', '--word-timestamps', 'True',
                '--output-format', 'json', '--output-name', 'voice_words', '--output-dir', '.', '--initial-prompt', '以下是普通话的句子，使用简体中文。'],
               cwd=TOPIC / 'work/tts', check=True, capture_output=True)
r = json.load(open(TOPIC / 'work/tts/voice_words.json'))
for s in r['segments']: print(f"{s['start']:7.2f} {s['text']}")
