#!/usr/bin/env python3
"""渲染前的数据准备：口型视频抽帧、人脸左右跟踪、配音包络、字幕分块 -> work/data.json。"""
import json, math, re, difflib, sys
from pathlib import Path
import numpy as np
import cv2
from common import cfg, ff, FPS, TOPIC
import subprocess
from common import FF


def frames(src):
    out = TOPIC / 'work/frames/person'; out.mkdir(parents=True, exist_ok=True)
    stamp = out / '.src'
    if not any(out.glob('*.jpg')) or (stamp.exists() and stamp.read_text() != str(Path(src).stat().st_mtime)):
        for p in out.glob('*.jpg'): p.unlink()
        ff('-i', src, '-vf', 'fps=30,scale=1920:1080:flags=lanczos', '-q:v', '3', str(out / '%05d.jpg'))
        stamp.write_text(str(Path(src).stat().st_mtime))
    return sorted(out.glob('*.jpg'))


def face_track(files):
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    n = len(files); raw = [None] * n
    for i in range(0, n, 3):
        im = cv2.imread(str(files[i]), cv2.IMREAD_GRAYSCALE)
        fs = casc.detectMultiScale(cv2.resize(im, (640, 360)), 1.1, 5, minSize=(50, 50))
        if len(fs):
            x, y, w, h = max(fs, key=lambda r: r[2] * r[3]); k = 1920 / 640
            raw[i] = [(x + w / 2) * k, (y + h / 2) * k, w * k, h * k]
    idx = [i for i, r in enumerate(raw) if r]
    if not idx: return [[960, 540, 400, 400]] * n
    arr = np.array([raw[i] for i in idx], dtype=float)
    full = np.stack([np.interp(np.arange(n), idx, arr[:, j]) for j in range(4)], axis=1)
    def smooth(v, w):  # 左右跟踪平滑 2 秒，镜头不跟着抖
        k = np.ones(w) / w; p = np.pad(v, (w // 2, w - 1 - w // 2), mode='edge'); return np.convolve(p, k, mode='valid')
    for j in range(4): full[:, j] = smooth(full[:, j], 61)
    print('face detected on', len(idx), 'of', (n + 2) // 3, 'sampled frames; median', np.median(full, axis=0).round())
    return full.round(1).tolist()


def envelope(n):
    raw = subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-i', str(TOPIC / 'work/tts/voice.mp3'), '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32); hop = 48000 // FPS
    e = np.array([math.sqrt(float(np.mean(a[i * hop:(i + 1) * hop] ** 2))) if i * hop < len(a) else 0 for i in range(n)])
    return np.clip(e / (np.percentile(e, 95) + 1e-9), 0, 1).round(3).tolist()


def captions(tl):
    caps = []
    norm = lambda c: c.lower() if re.match(r'[0-9a-zA-Z一-鿿]', c) else ''
    for li, l in enumerate(tl['lines']):
        say = [c for c in l['chars']]  # 只含有效字符
        show = l['show']
        a = [norm(c) for c in show]
        b = [c['c'].lower() for c in say]
        idx_a = [i for i, c in enumerate(a) if c]
        sm = difflib.SequenceMatcher(a=[a[i] for i in idx_a], b=b, autojunk=False)
        tmap = {}
        for x, y, n in sm.get_matching_blocks():
            for k in range(n): tmap[idx_a[x + k]] = (say[y + k]['s'], say[y + k]['e'])
        times = []
        last = (l['start'], l['start'] + 0.05)
        known = sorted(tmap)
        for i in range(len(show)):
            if i in tmap: last = tmap[i]
            elif a[i]:  # 稿子和配音写法不同（如 Qwen3-VL / 千问三VL）：在前后已知时间之间插值
                p = max([k for k in known if k < i], default=None); q = min([k for k in known if k > i], default=None)
                if p is not None and q is not None:
                    fr = (i - p) / (q - p); s = tmap[p][1] + (tmap[q][0] - tmap[p][1]) * fr; last = (s, s + 0.05)
            times.append(last)
        # 按中文标点切块，每块最多 16 字
        chunks, cur = [], []
        wid = lambda idx: sum(1.0 if '\u4e00' <= show[k] <= '\u9fff' else 0.56 for k in idx)
        depth = 0
        for i, ch in enumerate(show):
            if ch == '(': depth += 1
            if ch == ')': depth -= 1
            if ch in '，。：；？！、' and depth == 0:
                if cur: chunks.append(cur); cur = []
                continue
            cur.append(i)
            nxt = show[i + 1] if i + 1 < len(show) else ''
            safe = depth == 0 and not (re.match(r'[0-9A-Za-z.\-]', ch) and re.match(r'[0-9A-Za-z.\-]', nxt))
            latin_next = bool(re.match(r'[A-Za-z]', nxt)) and '\u4e00' <= ch <= '\u9fff'
            if (wid(cur) >= 15 and safe) or (latin_next and wid(cur) >= 13 and depth == 0): chunks.append(cur); cur = []
        if cur: chunks.append(cur)
        # 很短的块（如「一句话」「第一」）和下一块合并显示，中间空一格，免得一闪而过
        merged = []
        for ch in chunks:
            if merged and (wid(merged[-1]) <= 4.2 or wid(ch) <= 2.2) and wid(merged[-1]) + wid(ch) <= 13:
                merged[-1] = merged[-1] + [-1] + ch
            else:
                merged.append(ch)
        # 句末剩下很短一截（如单独一个「token」）并回上一块，不空格，免得单独闪一下
        if len(merged) > 1 and wid(merged[-1]) <= 3.5 and wid(merged[-2]) + wid(merged[-1]) <= 17 and merged[-1][0] == merged[-2][-1] + 1:
            last = merged.pop(); merged[-1] = merged[-1] + last
        chunks = merged
        nxt = tl['lines'][li + 1]['start'] if li + 1 < len(tl['lines']) else tl['duration'] + 0.6
        for ci, ch in enumerate(chunks):
            idx = [i if i >= 0 else None for i in ch]
            txt = ''.join(show[i] if i is not None else ' ' for i in idx)
            st = times[ch[0]][0]
            en = times[chunks[ci + 1][0]][0] if ci + 1 < len(chunks) else min(l['end'] + 0.4, nxt - 0.05)
            cs, prev = [], times[ch[0]]
            for i in idx:
                if i is not None: prev = times[i]
                cs.append({'s': round(prev[0], 3), 'e': round(prev[1], 3)})
            caps.append({'text': txt, 'start': round(st, 3), 'end': round(en, 3), 'chars': cs})
    return caps


def main():
    c = cfg()
    src = sys.argv[1] if len(sys.argv) > 1 else str(TOPIC / 'work/lipsync/lipsync.mp4')
    if not Path(src).exists(): sys.exit(f'找不到口型视频 {src}：先跑 avatar-video lipsync；想先看版式可用 avatar-video prep work/lipsync/driver.mp4')
    files = frames(src)
    tl = json.load(open(TOPIC / 'work/timeline.json'))
    n_frames = int(math.ceil((tl['duration'] + c.get('tail', 1.6)) * FPS))
    data = {'fps': FPS, 'voiceEnd': tl['duration'], 'nFrames': n_frames, 'nPerson': len(files), 'src': {'w': 1920, 'h': 1080},
            'face': face_track(files), 'env': envelope(n_frames), 'lines': tl['lines'], 'caps': captions(tl),
            'cfg': {k: c[k] for k in ('theme', 'camera_open', 'camera_open_until') if k in c}}
    json.dump(data, open(TOPIC / 'work/data.json', 'w'), ensure_ascii=False)
    print('person frames', len(files), 'render frames', n_frames, 'caps', len(data['caps']))


if __name__ == '__main__':
    main()
