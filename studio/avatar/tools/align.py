#!/usr/bin/env python3
"""把稿子逐字对齐到配音：whisper 逐词时间 + difflib 字符匹配，输出 timeline.json。"""
import json, re, difflib
from common import TOPIC
import os; os.chdir(TOPIC)

d = json.load(open('script/script.json'))
w = json.load(open('work/tts/voice_words.json'))
dur = json.load(open('work/tts/tts_result.json'))['result']['duration_ms'] / 1000

def norm(c):
    c = c.lower()
    return c if re.match(r'[0-9a-z一-鿿]', c) else ''

# whisper 字符流（每个词的时长均分给它的字符）；丢掉最后一段 end 之后的幻觉
hyp, htime = [], []
last_end = 0
for seg in w['segments']:
    if seg['start'] >= dur - 0.4:
        continue
    for wd in seg.get('words', []):
        cs = [norm(c) for c in wd['word']]
        cs = [c for c in cs if c]
        if not cs or wd['start'] < last_end - 0.5:
            continue
        span = max(wd['end'] - wd['start'], 0.02)
        for i, c in enumerate(cs):
            hyp.append(c)
            htime.append((wd['start'] + span * i / len(cs), wd['start'] + span * (i + 1) / len(cs)))
        last_end = wd['end']

# 稿子字符流（say 文本）
ref, owner = [], []
for li, l in enumerate(d['lines']):
    for ci, c in enumerate(l['say']):
        n = norm(c)
        if n:
            ref.append(n); owner.append((li, ci))

sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
t = [None] * len(ref)
for a, b, n in sm.get_matching_blocks():
    for k in range(n):
        t[a + k] = htime[b + k]
# 没匹配上的字按前后已知时间线性插值
known = [i for i, x in enumerate(t) if x]
for i in range(len(t)):
    if t[i] is None:
        p = max([k for k in known if k < i], default=None)
        q = min([k for k in known if k > i], default=None)
        if p is None: t[i] = (t[q][0] - 0.1, t[q][0])
        elif q is None: t[i] = (t[p][1], t[p][1] + 0.1)
        else:
            f = (i - p) / (q - p); s = t[p][1] + (t[q][0] - t[p][1]) * f
            t[i] = (s, s + 0.05)

lines = []
for li, l in enumerate(d['lines']):
    idx = [i for i, o in enumerate(owner) if o[0] == li]
    chars = [{"c": l['say'][owner[i][1]], "s": round(t[i][0], 3), "e": round(t[i][1], 3)} for i in idx]
    lines.append({"id": l['id'], "show": l['show'], "say": l['say'],
                  "start": chars[0]['s'], "end": chars[-1]['e'], "chars": chars})
matched = sum(n for _, _, n in sm.get_matching_blocks())
out = {"duration": dur, "fps": 30, "frames": int(round(dur * 30)) + 45, "match_ratio": round(matched / len(ref), 3), "lines": lines}
json.dump(out, open('work/timeline.json', 'w'), ensure_ascii=False, indent=1)
print('match', out['match_ratio'], 'duration', dur)
for l in lines: print(l['id'], f"{l['start']:6.2f}-{l['end']:6.2f}", l['show'][:24])
