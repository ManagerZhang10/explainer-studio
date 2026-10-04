#!/usr/bin/env python3
"""studio refs <命令>：参考视频库（抓博主视频 -> 转写 -> 切镜 -> 指标 -> Gemini 拆解 -> 汇总）。

  fetch URL… [--limit N]     抓抖音单条或博主最近 N 条到 references/creators/
  jobs [目录…]               扫 creators/ 和 saved/ 里的 mp4，补进 jobs.tsv（已有的行不动）
  run [slug…]                对 jobs.tsv 里的视频跑全套：asr shots metrics analyze（已有结果跳过）
  asr | shots | analyze [slug…]   只跑某一步
  merge                      用最新指标重算所有拆解文件
  report [分组…]             按分组打印节奏、语速、钩子、配乐等统计
  where                      打印参考视频库目录

分析结果在 references/analysis/<分组>/<slug>.json；分组 = jobs.tsv 的 group 列（默认取作者名）。"""
import re
import sys

from common import ANA, CREATORS, JOBS, REF, SAVED, read_jobs, write_jobs

cmd, args = (sys.argv[1] if len(sys.argv) > 1 else 'help'), sys.argv[2:]


def jobs_cmd(dirs):
    rows = read_jobs() if JOBS.exists() else []
    have = {r['video'] for r in rows}
    for d in [*map(__import__('pathlib').Path, dirs)] or [CREATORS, SAVED]:
        for v in sorted(d.rglob('*.mp4')):
            if str(v) in have:
                continue
            rel = v.relative_to(REF) if v.is_relative_to(REF) else v
            parts = rel.parts
            author = parts[1] if parts[0] == 'creators' else (parts[1].split(' ')[1] if parts[0] == 'saved' and ' ' in parts[1] else '')
            m = re.match(r'(\d{4}-\d{2}-\d{2})_(.*)_(\d+)$', v.stem)
            date, title, vid = (m.groups() if m else ('', v.parent.name if v.stem == 'source' else v.stem, ''))
            slug = re.sub(r'\W+', '_', f'{author}_{vid or date or v.stem}').strip('_')[:48]
            rows.append({'slug': slug, 'video': str(v), 'author': author, 'title': title, 'date': date, 'group': author or 'misc'})
            print('  +', slug, title[:30])
    print('jobs ->', write_jobs(rows), f'共 {len(rows)} 条')


if cmd == 'fetch':
    import fetch, asyncio, argparse  # noqa: E401
    ap = argparse.ArgumentParser(prog='studio refs fetch'); ap.add_argument('urls', nargs='+')
    ap.add_argument('--limit', type=int, default=10); ap.add_argument('--dry', action='store_true')
    a = ap.parse_args(args); asyncio.run(fetch.main(a.urls, a.limit, a.dry))
elif cmd == 'jobs':
    jobs_cmd(args)
elif cmd in ('run', 'asr', 'shots', 'analyze', 'metrics'):
    import pipeline as P
    js = read_jobs(only=set(args))
    steps = ['asr', 'shots', 'metrics', 'analyze'] if cmd == 'run' else [cmd]
    for step in steps:
        if step == 'metrics':
            print('metrics:', len(P.metrics(js)), '条'); continue
        M = P.metrics(js) if step == 'analyze' else {}
        for j in js:
            try:
                r = P.analyze(j, M.get(j['slug'])) if step == 'analyze' else getattr(P, step)(j)
            except Exception as e:  # noqa: BLE001
                r = f'失败 {type(e).__name__}: {str(e)[:160]}'
            print(f'{step:8} {j["slug"]:36} {r}', flush=True)
elif cmd == 'merge':
    import pipeline as P
    print('merged', P.merge())
elif cmd == 'report':
    import pipeline as P
    P.report(set(args))
elif cmd == 'where':
    print(REF, '\n', ANA, sep='')
else:
    print(__doc__)
