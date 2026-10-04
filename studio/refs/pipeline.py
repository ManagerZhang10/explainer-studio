"""参考视频拆解流水线：转写 -> 切镜 -> 指标 -> 视觉模型拆解 -> 汇总。
每一步按 slug 落盘，已有结果直接跳过，可随时中断重跑。"""
import json
import re
import statistics as st
import subprocess
import time
import urllib.request

from common import ASR, ANA, METRICS, SHEETS, SHOTS, duration, ff
from studio.common import vision
from openai_transcribe import transcribe

CJK = re.compile(r'[一-鿿]')


def cjk(s):
    return len(CJK.findall(s))


def _ts(sec):
    ms = int(round(sec * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def segments(slug):
    p = ASR / f'{slug}.json'
    if not p.exists():
        return []
    return [(float(s['start']), float(s['end']), s.get('text', '').strip())
            for s in json.load(open(p)).get('segments', []) if s.get('text', '').strip()]


# ---------- 1. 转写：providers.asr = openai（whisper API）| bailian（Fun-ASR）| local（本机 mlx-whisper，免费） ----------
def _asr_openai(audio, model):
    r = transcribe(str(audio), model)
    return r.get('segments', []), r.get('language'), r.get('duration')


def _asr_bailian(audio):
    from studio.common import bailian
    url = bailian.upload(audio, 'fun-asr')
    t = bailian.call('services/audio/asr/transcription', {'model': 'fun-asr', 'input': {'file_urls': [url]},
                     'parameters': {'language_hints': ['zh', 'en']}}, oss=True, async_=True)
    try:
        o = bailian.wait(t['output']['task_id'], poll=5, log=lambda m: None)
    except RuntimeError as e:
        if 'ASR_RESPONSE_HAVE_NO_WORDS' in str(e):  # 整段没人声（纯音乐）：如实记 0 句，别像 whisper 那样编字
            return [], 'zh', None
        raise
    res = json.loads(urllib.request.urlopen(o['output']['results'][0]['transcription_url'], context=bailian.CTX, timeout=300).read())
    tr = res['transcripts'][0]
    segs = [{'start': x['begin_time'] / 1000, 'end': x['end_time'] / 1000, 'text': x['text']} for x in tr.get('sentences', [])]
    return segs, 'zh', (res.get('properties') or {}).get('original_duration_in_milliseconds', 0) / 1000 or None


def _asr_local(audio):
    from studio.common import config
    subprocess.run([config.get('tools', 'mlx_whisper', 'mlx_whisper'), str(audio), '--model', 'mlx-community/whisper-large-v3-turbo',
                    '--language', 'zh', '--output-format', 'json', '--output-name', audio.stem, '--output-dir', str(audio.parent),
                    '--initial-prompt', '以下是普通话的句子，使用简体中文。'], check=True, capture_output=True)
    r = json.load(open(audio.with_suffix('.json')))
    audio.with_suffix('.json').unlink()
    return [{'start': x['start'], 'end': x['end'], 'text': x['text']} for x in r['segments']], 'zh', None


def asr(j, model='whisper-1'):
    from studio.common import config
    slug = j['slug']; out = ASR / f'{slug}.json'
    if out.exists():
        return 'skip'
    ASR.mkdir(parents=True, exist_ok=True)
    prov = config.provider('asr')
    # 统一抽成 16k 单声道：OpenAI 用 m4a（压到 25MB 内），Fun-ASR 认 mp3 不认这种 m4a，本机 whisper 用 wav
    ext, codec = {'bailian': ('mp3', ['-c:a', 'libmp3lame', '-b:a', '48k']), 'local': ('wav', [])}.get(prov, ('m4a', ['-c:a', 'aac', '-b:a', '32k']))
    audio = ASR / f'{slug}.{ext}'
    cmd = [ff(), '-hide_banner', '-loglevel', 'error', '-y', '-threads', '2', '-i', j['video']]
    if j.get('asr_sec'):
        cmd += ['-t', str(j['asr_sec'])]
    subprocess.run(cmd + ['-vn', '-ac', '1', '-ar', '16000', *codec, str(audio)], check=True)
    try:
        segs, lang, dur = (_asr_bailian(audio) if prov == 'bailian' else _asr_local(audio) if prov == 'local'
                           else _asr_openai(audio, model))
    finally:
        audio.unlink(missing_ok=True)
    json.dump({'model': model if prov == 'openai' else prov, 'language': lang, 'duration': dur,
               'clip_sec': j.get('asr_sec') or None, 'n_segments': len(segs), 'segments': segs},
              open(out, 'w'), ensure_ascii=False)
    (ASR / f'{slug}.srt').write_text('\n\n'.join(f"{i + 1}\n{_ts(s['start'])} --> {_ts(s['end'])}\n{s['text'].strip()}"
                                                 for i, s in enumerate(segs)))
    (ASR / f'{slug}.txt').write_text('\n'.join(s['text'].strip() for s in segs))
    time.sleep(2 if prov == 'openai' else 0)
    return f'{len(segs)} 句'


# ---------- 2. 切镜：硬切（换镜头）和软切（版面变化）两档阈值 ----------
def _scene_times(video, th):
    r = subprocess.run([ff(), '-hide_banner', '-loglevel', 'error', '-threads', '2', '-i', video, '-an', '-filter:v',
                        f"select='gt(scene,{th})',metadata=print:file=-", '-f', 'null', '-'], capture_output=True, text=True)
    return [float(x) for x in re.findall(r'pts_time:([0-9.]+)', r.stdout)]


def shots(j, hard=0.25, soft=0.10):
    slug = j['slug']; SHOTS.mkdir(parents=True, exist_ok=True)
    done = []
    for th, name in ((hard, f'{slug}.tsv'), (soft, f'{slug}.soft.tsv')):
        p = SHOTS / name
        if not p.exists():
            p.write_text('\n'.join(f'{t:.3f}' for t in _scene_times(j['video'], th)))
        done.append(len([x for x in p.read_text().split() if x]))
    return f'硬切 {done[0]} / 版面变化 {done[1]}'


def sheet(j, cols=5, rows=3, scale=300):
    out = SHEETS / f"{j['slug']}.jpg"
    if not out.exists():
        SHEETS.mkdir(parents=True, exist_ok=True)
        step = max(2, round((duration(j['video']) or 60) / (cols * rows)))
        subprocess.run([ff(), '-hide_banner', '-loglevel', 'error', '-y', '-i', j['video'], '-vf',
                        f'fps=1/{step},scale={scale}:-1,tile={cols}x{rows}', '-frames:v', '1', str(out)], check=True)
    return out


# ---------- 3. 指标（全部可复现，不靠模型） ----------
def _read_times(p):
    return [float(x) for x in p.read_text().split() if x.strip()] if p.exists() else []


def metrics_one(j):
    slug = j['slug']; segs = segments(slug)
    if not segs:
        return None
    dur = duration(j['video']) or segs[-1][1]
    s0, s1 = segs[0][0], segs[-1][1]
    chars = sum(cjk(s[2]) for s in segs); span = s1 - s0
    lens = sorted(cjk(s[2]) for s in segs if cjk(s[2]))
    cuts = [c for c in _read_times(SHOTS / f'{slug}.tsv') if c <= s1 + 2]
    b = [0.0] + cuts + [s1]
    sh = [round(b[i + 1] - b[i], 3) for i in range(len(b) - 1) if b[i + 1] - b[i] > 0.15]
    soft = _read_times(SHOTS / f'{slug}.soft.tsv')
    return {'duration_ms': int(dur * 1000), 'speech_span_s': round(span, 2), 'narration_chars': chars,
            'speech_rate_cps': round(chars / span, 2) if span > 0 else 0, 'seg_count': len(segs),
            'seg_cjk_len_median': lens[len(lens) // 2] if lens else 0,
            'seg_cjk_len_p90': lens[int(len(lens) * 0.9)] if lens else 0,
            'seg_sec_median': round(sorted(s[1] - s[0] for s in segs)[len(segs) // 2], 2),
            'shot_count': len(sh), 'cuts_per_min': round(len(sh) / (dur / 60), 2) if dur else 0,
            'shot_ms_avg': int(sum(sh) / len(sh) * 1000) if sh else 0,
            'shot_ms_fastest': int(min(sh) * 1000) if sh else 0, 'shot_ms_slowest': int(max(sh) * 1000) if sh else 0,
            'layout_change_count': len(soft) or None, 'first_narration_s': round(s0, 2), 'cut_times_head': cuts[:14]}


def metrics(jobs):
    METRICS.mkdir(parents=True, exist_ok=True)
    p = METRICS / 'metrics.json'
    rows = json.load(open(p)) if p.exists() else {}
    for j in jobs:
        m = metrics_one(j)
        if m:
            rows[j['slug']] = m
    json.dump(rows, open(p, 'w'), ensure_ascii=False, indent=1)
    return rows


# ---------- 4. 视觉模型拆解（Gemini 或千问，见 providers.vision） ----------
def _mean_db(video, t0, d):
    r = subprocess.run([ff(), '-hide_banner', '-nostats', '-ss', str(t0), '-t', str(d), '-i', video, '-vn',
                        '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True)
    m = re.search(r'mean_volume:\s*(-?[\d.]+) dB', r.stderr)
    return float(m.group(1)) if m else None


def audio_probe(video, segs):
    """说话段 vs 句间停顿的平均音量：停顿里还有声音 = 有配乐或音效垫底。"""
    speech = [(a, b - a) for a, b, _ in segs if b - a > 0.8][:12]
    gaps = [(segs[i][1], segs[i + 1][0] - segs[i][1]) for i in range(len(segs) - 1) if segs[i + 1][0] - segs[i][1] > 0.7][:12]
    avg = lambda L: round(sum(L) / len(L), 1) if L else None  # noqa: E731
    sm = [v for v in (_mean_db(video, a, d) for a, d in speech) if v is not None]
    gm = [v for v in (_mean_db(video, a, d) for a, d in gaps) if v is not None]
    return {'speech_mean_db': avg(sm), 'gap_mean_db': avg(gm), 'speech_n': len(sm), 'gap_n': len(gm)}


SCHEMA = """只回答 JSON，字段严格如下（不要多余解释）：
{
 "visual_layers":["从这些里选可辨识的层：真人口播/屏幕录制/自绘动效/图表/代码/论文截图/B-roll/实拍书页/UI界面录屏/字幕条"],
 "on_screen_text":{"density":"high|med|low","style":"字幕的具体视觉形态","position":"位置","font_estimate":"字号与视觉重量估计","examples":["3-6条画面上真实出现的文字（照抄）"]},
 "animation":{"has_motion_graphics":true,"types":["逐字/逐条弹出","进度条生长","数字滚动","卡片滑入","高亮扫过","连线绘制","镜头推拉","遮罩转场"],"easing":"缓动风格描述"},
 "audio_note":"从画面判断的口播/字幕音/是否有配乐的感觉（不确定就说看不出）",
 "hook":{"hook_type":"悬念/痛点/反常识/身份背书/数字冲击/问题直给","first_3s_desc":"开头3秒画面在干什么","on_screen_headline":"第一屏的大标题（照抄）"},
 "retention_devices":["3-5条具体到动作的留人手段"],
 "structure":[{"t_start":0.0,"t_end":3.2,"beat":"钩子/立论/证据/转折/小结/收尾","desc":"这一段在干什么（20字内）"}],
 "reusable":["4-6条『做技术科普短视频时可直接照抄的动作』，每条必须具体到可执行，如『底部居中白字黑底圆角胶囊字幕，每屏≤14字』"]}"""


def analyze(j, m=None):
    out = ANA / (j.get('group') or 'misc') / f"{j['slug']}.json"
    if out.exists():
        return 'skip'
    segs = segments(j['slug'])
    if not segs:
        return '缺转写，先跑 asr'
    dur = duration(j['video']) or segs[-1][1]
    aud = audio_probe(j['video'], segs)
    tl = '\n'.join(f'[{a:6.1f}-{b:6.1f}] {t}' for a, b, t in segs[:260])
    if len(segs) > 260:
        tl += f'\n...(共{len(segs)}句，已截断)'
    ctx = f"""这是一支中文技术科普短视频的制作拆解素材。
作者：{j['author']}｜标题：{j['title']}｜日期：{j['date']}｜时长：{round(dur, 1)}秒
图片是一张按时间顺序排列的缩略图拼版（每 {max(2, round(dur / 15))} 秒一帧，从左上角开始按行从左到右）。
音频实测：说话段平均音量 {aud['speech_mean_db']} dB，句间停顿平均音量 {aud['gap_mean_db']} dB（停顿里有音量=有配乐或音效垫底）。

逐句转写（带时间戳）：
{tl}

{'硬指标：' + json.dumps(m, ensure_ascii=False) if m else ''}

{SCHEMA}"""
    raw = vision.ask_json(ctx, images=[sheet(j)])
    raw.update({'slug': j['slug'], 'author': j['author'], 'title': j['title'], 'date': j['date'],
                'duration_ms': int(dur * 1000), 'audio_measured': aud})
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(normalize(raw, m or {}, {'source_video': j['video']}), open(out, 'w'), ensure_ascii=False, indent=1)
    return str(out)


def normalize(raw, m, keep):
    """视觉模型给的语义字段 + 实测指标 -> 统一结构。原始输出存在 _raw，可随时用新指标重算（studio refs merge）。"""
    hook, ost, am = raw.get('hook') or {}, raw.get('on_screen_text') or {}, raw.get('audio_measured') or {}
    bgm = None
    if am.get('gap_mean_db') is not None and am.get('speech_mean_db') is not None:
        delta = am['gap_mean_db'] - am['speech_mean_db']
        bgm = True if delta >= -12 else (False if delta <= -30 else None)
    dur = (raw.get('duration_ms') or m.get('duration_ms') or 0) / 1000
    soft = m.get('layout_change_count')
    seg, cpm, cps = m.get('seg_sec_median'), m.get('cuts_per_min'), m.get('speech_rate_cps')
    pp = None
    if seg:
        bits = [f'字幕平均每 {seg}s 一句（约 {round(60 / seg, 1)} 句/分钟）']
        if cpm:
            bits.append(f'硬切 {cpm} 次/分钟')
        if cps:
            bits.append(f'语速 {cps} 字/秒')
        if raw.get('structure'):
            bits.append(f"叙事按 {len(raw['structure'])} 个段落推进：{'→'.join(b.get('beat', '') for b in raw['structure'][:6])}")
        pp = '；'.join(bits)
    return {**keep,
            'slug': raw.get('slug'), 'author': raw.get('author'), 'title': raw.get('title'), 'date': raw.get('date'),
            'duration_ms': raw.get('duration_ms') or m.get('duration_ms'),
            'shot_count': m.get('shot_count'), 'cuts_per_min': cpm, 'layout_change_count': soft,
            'layout_changes_per_min': round(soft / (dur / 60), 2) if soft and dur else None,
            'pacing': {'avg_shot_ms': m.get('shot_ms_avg'), 'fastest_ms': m.get('shot_ms_fastest'),
                       'slowest_ms': m.get('shot_ms_slowest'), 'subtitle_seg_median_s': seg},
            'narration': {'speech_rate_cps': cps, 'subtitle_chars_median_per_line': m.get('seg_cjk_len_median'),
                          'subtitle_chars_p90_per_line': m.get('seg_cjk_len_p90')},
            'on_screen_text': {k: ost.get(k) for k in ('density', 'style', 'position', 'font_estimate')} | {'examples': ost.get('examples', [])},
            'visual_layers': raw.get('visual_layers', []), 'animation': raw.get('animation', {}),
            'audio': {'bgm': bgm, 'bgm_style': raw.get('audio_note'), 'speech_mean_db': am.get('speech_mean_db'),
                      'silence_gap_mean_db': am.get('gap_mean_db')},
            'structure': raw.get('structure', []), 'hook_type': hook.get('hook_type'),
            'hook_first3s': hook.get('first_3s_desc'), 'hook_on_screen_headline': hook.get('on_screen_headline'),
            'retention_devices': raw.get('retention_devices', []), 'pacing_pattern': pp,
            '可复用做法': raw.get('reusable', []), '_raw': raw}


def merge():
    """用最新 metrics.json 重算所有拆解文件的指标字段；不认识的字段（人工补的核验记录等）原样保留。"""
    M = json.load(open(METRICS / 'metrics.json')) if (METRICS / 'metrics.json').exists() else {}
    n = 0
    for p in ANA.glob('*/*.json'):
        if p.parent.name.startswith('_'):
            continue
        d = json.load(open(p))
        raw = d.get('_raw')
        if not isinstance(raw, dict):
            continue
        new = normalize(raw, M.get(p.stem, {}), {})
        json.dump({**d, **{k: v for k, v in new.items() if v not in (None, [], {})}}, open(p, 'w'), ensure_ascii=False, indent=1)
        n += 1
    return n


# ---------- 5. 汇总 ----------
def report(groups=None):
    dirs = sorted(d for d in ANA.iterdir() if d.is_dir() and not d.name.startswith('_') and (not groups or d.name in groups))
    for d in dirs:
        rows = [json.load(open(p)) for p in d.glob('*.json')]
        if not rows:
            continue
        print('=' * 64); print(d.name, 'n =', len(rows), '｜作者：', '、'.join(sorted({str(r.get('author')) for r in rows})))

        def line(name, vals):
            v = [x for x in vals if isinstance(x, (int, float))]
            if v:
                print(f'  {name:28} 中位 {st.median(v):8.2f}   最小 {min(v):8.2f}   最大 {max(v):8.2f}')
        line('时长 秒', [(r.get('duration_ms') or 0) / 1000 for r in rows])
        line('硬切 次/分钟', [r.get('cuts_per_min') for r in rows])
        line('版面变化 次/分钟', [r.get('layout_changes_per_min') for r in rows])
        line('平均镜头 毫秒', [(r.get('pacing') or {}).get('avg_shot_ms') for r in rows])
        line('语速 字/秒', [(r.get('narration') or {}).get('speech_rate_cps') for r in rows])
        line('字幕每句中位 字', [(r.get('narration') or {}).get('subtitle_chars_median_per_line') for r in rows])
        line('字幕每句中位 秒', [(r.get('pacing') or {}).get('subtitle_seg_median_s') for r in rows])
        cnt = lambda key: {k: sum(1 for r in rows if str(key(r)) == k) for k in sorted({str(key(r)) for r in rows})}  # noqa: E731
        print('  开头钩子类型:', cnt(lambda r: r.get('hook_type')))
        print('  配乐垫底:', cnt(lambda r: (r.get('audio') or {}).get('bgm')))
        print('  画面层:', sorted({x for r in rows for x in (r.get('visual_layers') or [])}))
        print('  动画类型:', sorted({x for r in rows for x in ((r.get('animation') or {}).get('types') or [])}))

