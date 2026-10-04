#!/usr/bin/env python3
"""混音：配音（EQ+压缩）+ 背景音乐（有人声时自动压低）+ numpy 合成的音效（时间表来自页面的 CUES）-> work/render/{ver}_mix.m4a，响度 -14 LUFS。"""
import json, math, subprocess, sys
from pathlib import Path
import numpy as np

from common import TOPIC as ROOT, FF
SR = 48000


def decode(path, ch=1):
    raw = subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-i', str(path), '-ac', str(ch), '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).copy()
    return a.reshape(-1, ch) if ch > 1 else a


def onepole(x, fc):  # fc 可以是逐样本数组：做扫频
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s += a[i] * (x[i] - s); y[i] = s
    return y


def env(n, att, dec):
    t = np.arange(n) / SR
    return np.minimum(t / max(att, 1e-4), 1) * np.exp(-np.maximum(t - att, 0) / dec)


def sfx(kind, seed=0):
    r = np.random.default_rng(seed)
    if kind == 'tick':
        n = int(0.06 * SR); t = np.arange(n) / SR
        return (0.6 * np.sin(2 * np.pi * 2800 * t) + 0.4 * r.standard_normal(n)) * env(n, 0.001, 0.012)
    if kind == 'type':
        n = int(0.05 * SR); t = np.arange(n) / SR
        return (0.5 * np.sin(2 * np.pi * (1700 + 300 * r.random()) * t) + 0.5 * onepole(r.standard_normal(n), 5000)) * env(n, 0.0005, 0.010)
    if kind == 'pop':
        n = int(0.16 * SR); t = np.arange(n) / SR
        f = 950 * np.exp(-t * 18) + 280
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.05)
    if kind == 'swipe':
        n = int(0.32 * SR); t = np.arange(n) / SR
        x = r.standard_normal(n); x = x - onepole(x, np.linspace(1500, 5000, n))
        return onepole(x, 9000) * np.sin(np.pi * t / t[-1]) ** 2 * 0.9
    if kind == 'whoosh':
        n = int(0.55 * SR); t = np.arange(n) / SR
        fc = 300 + 3200 * np.sin(np.pi * t / t[-1]) ** 2
        return onepole(r.standard_normal(n), fc) * np.sin(np.pi * t / t[-1]) ** 1.5 * 1.6
    if kind == 'hit':
        n = int(0.9 * SR); t = np.arange(n) / SR
        f = 110 * np.exp(-t * 14) + 42
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.28)
        click = onepole(r.standard_normal(n), 6000) * env(n, 0.0005, 0.012)
        return 0.95 * body + 0.5 * click
    if kind == 'boom':
        n = int(1.8 * SR); t = np.arange(n) / SR
        f = 75 * np.exp(-t * 6) + 30
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 0.65)
        tail = onepole(r.standard_normal(n), 600) * env(n, 0.01, 0.5) * 0.9
        return body + tail + onepole(r.standard_normal(n), 7000) * env(n, 0.0005, 0.02) * 0.6
    if kind == 'glitch':
        n = int(0.14 * SR); x = np.zeros(n); i = 0
        while i < n:
            seg = int(r.integers(150, 900)); fq = r.choice([180, 440, 900, 1800, 3500])
            tt = np.arange(min(seg, n - i)) / SR
            x[i:i + seg] = np.sign(np.sin(2 * np.pi * fq * tt)) * r.uniform(0.2, 0.8); i += seg
        return np.round(x * 6) / 6 * env(n, 0.001, 0.08)
    if kind == 'riser':
        n = int(0.95 * SR); t = np.arange(n) / SR
        f = 200 * (10 ** (t / t[-1]))
        tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
        nz = onepole(r.standard_normal(n), 400 + 6000 * t / t[-1]) * 0.9
        return (tone + nz) * (t / t[-1]) ** 2
    if kind == 'sparkle':
        n = int(0.7 * SR); x = np.zeros(n)
        for k in range(7):
            st = int(r.uniform(0, 0.5) * SR); m = int(0.12 * SR); tt = np.arange(m) / SR
            x[st:st + m] += np.sin(2 * np.pi * r.uniform(3000, 6500) * tt) * env(m, 0.001, 0.04)[:len(x[st:st + m])] * 0.4
        return x
    raise ValueError(kind)


def main(ver):
    data = json.load(open(ROOT / 'work/data.json'))
    cues = json.load(open(ROOT / f'work/render/cues_{ver}.json'))
    N = int(data['nFrames'] / 30 * SR) + SR // 2
    vp = ROOT / 'work/tts/voice_eq.wav'
    if not vp.exists():
        subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(ROOT / 'work/tts/voice.mp3'), '-af',
                        'highpass=f=70,equalizer=f=180:t=q:w=1:g=2.5,equalizer=f=3200:t=q:w=1.2:g=1.5,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2',
                        '-ar', str(SR), str(vp)], check=True)
    voice = decode(vp); vo = np.zeros(N); vo[:min(N, len(voice))] = voice[:N]
    bgm = decode(ROOT / 'work/bgm/bgm.mp3', 2); bg = np.zeros((N, 2)); bg[:min(N, len(bgm))] = bgm[:N]
    # 配音包络 -> BGM 自动避让
    hop = SR // 100
    rms = np.array([math.sqrt(float(np.mean(vo[i:i + hop] ** 2))) for i in range(0, N, hop)])
    act = (rms > 0.02).astype(float)
    sm = np.zeros_like(act); s = 0
    for i, a in enumerate(act):
        s += (0.35 if a > s else 0.025) * (a - s); sm[i] = s
    duck = np.repeat(sm, hop)[:N]
    g_bg = 0.55 - 0.40 * duck          # 有人声时约 -16 dB，空档时约 -5 dB
    t = np.arange(N) / SR
    g_bg *= np.clip((data['nFrames'] / 30 - 0.2 - t) / 1.5, 0, 1)   # 片尾淡出
    mix_m = vo * 1.0
    fx = np.zeros(N)
    cache = {}
    for i, c in enumerate(cues):
        k = (c['type'], i % 3)
        if k not in cache: cache[k] = sfx(c['type'], seed=i % 3)
        x = cache[k]; st = int(c['t'] * SR)
        if st >= N: continue
        e = min(N, st + len(x)); fx[st:e] += x[:e - st] * 0.26 * c.get('gain', 1) * (0.7 if c['type'] in ('boom', 'hit') else 1)
    fx = fx - onepole(fx, 45.0)  # 切掉 45Hz 以下，手机外放不破音
    out = np.stack([mix_m + fx, mix_m + fx], 1) + bg * g_bg[:, None]
    out = out / max(1e-6, np.abs(out).max()) * 0.9
    tmp = ROOT / f'work/render/{ver}_mix_raw.wav'
    import wave
    with wave.open(str(tmp), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype('<i2').tobytes())
    dst = ROOT / f'work/render/{ver}_mix.m4a'
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(tmp), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k', str(dst)], check=True)
    tmp.unlink()
    print('mix', dst)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'main')
