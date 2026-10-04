"""参考视频库的目录约定。根目录 = 工作区下的 references/，布局：

references/
  creators/<作者>/<日期>_<标题>_<id>.mp4 + manifest.json   studio refs fetch 抓下来的博主视频
  saved/<YYYYMMDD 作者 标题>/                              手动收藏的单条（任何平台）
  jobs.tsv                                                 要分析哪些视频（studio refs jobs 生成）
  analysis/
    _asr/<slug>.{json,srt,txt}     转写（带时间戳）
    _shots/<slug>.tsv              硬切时间点
    _sheets/<slug>.jpg             全片缩略图拼版
    _metrics/metrics.json          语速、切镜频率等实测指标
    <分组>/<slug>.json             每条视频的拆解结果
    <作者>_作者风格报告.md          人写的总结
"""
import csv
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio.common import config  # noqa: E402

REF = (config.workspace() or Path.cwd()) / 'references'
CREATORS, SAVED, ANA = REF / 'creators', REF / 'saved', REF / 'analysis'
ASR, SHOTS, SHEETS, METRICS = ANA / '_asr', ANA / '_shots', ANA / '_sheets', ANA / '_metrics'
JOBS = REF / 'jobs.tsv'
COLS = ['slug', 'video', 'author', 'title', 'date', 'group', 'asr_sec']


def ff():
    return config.ffmpeg()


def duration(path):
    r = subprocess.run([ff(), '-hide_banner', '-i', str(path)], capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if 'Duration:' in line:
            h, m, s = line.split('Duration:')[1].split(',')[0].strip().split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
    return None


def read_jobs(path=None, only=None):
    """jobs.tsv：每行一条视频，列见 COLS；asr_sec 留空=整条转写，填数字=只转前 N 秒（长视频省钱）。"""
    rows = []
    for rec in csv.reader(open(path or JOBS, encoding='utf-8'), delimiter='\t'):
        if not rec or rec[0].startswith('#'):
            continue
        j = dict(zip(COLS, rec + [''] * (len(COLS) - len(rec))))
        if not only or j['slug'] in only:
            rows.append(j)
    return rows


def write_jobs(rows, path=None):
    p = Path(path or JOBS)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['# ' + '\t'.join(COLS)])
        for j in rows:
            w.writerow([str(j.get(c, '')) for c in COLS])
    return p
