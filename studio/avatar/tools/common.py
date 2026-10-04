#!/usr/bin/env python3
"""口播视频各工具的公共部分。所有工具都在「专题目录」里运行（cwd = 专题根，里面有 topic.json）。"""
import json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))   # 仓库根，供 `from studio.common import …`
from studio.common import config  # noqa: E402

PIPE = Path(__file__).resolve().parent.parent      # studio/avatar
FONTS = config.CACHE / 'fonts'                      # `studio setup` 下载到这里
TOPIC = Path.cwd()
FF = config.ffmpeg()
FPS = 30


def cfg():
    p = TOPIC / 'topic.json'
    if not p.exists():
        sys.exit(f'{TOPIC} 里没有 topic.json：先 cd 到专题目录，或用 studio avatar init <目录> 新建')
    return json.load(open(p))


def script():
    return json.load(open(TOPIC / 'script/script.json'))


def env():
    return config.secrets()


def sh(*a, **kw):
    return subprocess.run([str(x) for x in a], check=True, **kw)


def ff(*a):
    sh(FF, '-hide_banner', '-loglevel', 'error', '-y', *a)


def duration(path):
    err = subprocess.run([FF, '-hide_banner', '-i', str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r'Duration: (\d+):(\d+):([\d.]+)', err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def mkdir(*ps):
    for p in ps:
        (TOPIC / p).mkdir(parents=True, exist_ok=True)


def resolve(p):
    """topic.json 里的路径：相对路径按专题目录解析，~ 展开。"""
    p = Path(str(p)).expanduser()
    return p if p.is_absolute() else TOPIC / p


# 配音服务：fal / bailian 都是 MiniMax speech-2.8-hd；qwen = 千问 Qwen-Audio-3.0-TTS；cosyvoice = CosyVoice v3.5（后三个都走百炼）
VOICES = {'fal': 'MiniMax（fal）', 'bailian': 'MiniMax（百炼）', 'qwen': '千问 Qwen-Audio-3.0-TTS（百炼）', 'cosyvoice': 'CosyVoice v3.5（百炼）'}


def clone_slot(prov):
    """各家的克隆声音互不通用，分开存：topic.json 里的键名和默认文件。fal 沿用老名字。"""
    if prov == 'fal':
        return 'clone_result', 'work/voice/clone_result.json'
    return f'clone_result_{prov}', f'work/voice/clone_result_{prov}.json'


def bailian_tts_model(prov):
    return config.get('providers', {'qwen': 'bailian_qwen_tts_model', 'cosyvoice': 'bailian_cosyvoice_model'}[prov])
