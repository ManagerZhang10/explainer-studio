"""本机配置：路径、密钥、个人素材都从这里读，代码里不写任何本机绝对路径。

配置文件默认在 ~/.config/explainer-studio/config.toml（可用环境变量 EXPLAINER_STUDIO_CONFIG 指到别处），
格式见仓库根目录的 config.example.toml。缺的项用下面 DEFAULTS 里的值。
"""
import os
import shutil
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(os.environ.get('EXPLAINER_STUDIO_CONFIG', '~/.config/explainer-studio/config.toml')).expanduser()
CACHE = Path(os.environ.get('EXPLAINER_STUDIO_CACHE', '~/.cache/explainer-studio')).expanduser()

DEFAULTS = {
    'paths': {'workspace': '~/explainer-studio-workspace'},
    'secrets': {'env_file': '~/.config/explainer-studio/.env'},
    'tools': {'ffmpeg': '', 'mlx_whisper': 'mlx_whisper'},
    # 各环节用哪家服务。fal/gemini/openai = 海外；bailian = 阿里云百炼（国内直连，一把 DASHSCOPE_API_KEY 全包）
    'providers': {'voice': 'fal', 'lipsync': 'fal', 'vision': 'gemini', 'asr': 'openai', 'music': 'fal',
                  'bailian_vision_model': 'qwen3-vl-plus', 'bailian_omni_model': 'qwen3.5-omni-plus',
                  'bailian_qwen_tts_model': 'qwen-audio-3.0-tts-plus', 'bailian_cosyvoice_model': 'cosyvoice-v3.5-plus'},
    'me': {},        # 本人素材：camera_video / camera_mic / camera_start / voice_clone_result / demo_image
}

_cfg = None


def load():
    global _cfg
    if _cfg is None:
        data = {}
        if CONFIG_PATH.exists():
            data = tomllib.loads(CONFIG_PATH.read_text())
        _cfg = {k: {**v, **data.get(k, {})} for k, v in DEFAULTS.items()}
        for k, v in data.items():
            _cfg.setdefault(k, v)
    return _cfg


def get(section, key, default=None):
    v = load().get(section, {}).get(key, default)
    return os.path.expanduser(v) if isinstance(v, str) and v.startswith('~') else v


def path(section, key, default=None):
    v = get(section, key, default)
    return Path(v).expanduser() if v else None


def workspace():
    return path('paths', 'workspace')


def ffmpeg():
    p = get('tools', 'ffmpeg') or shutil.which('ffmpeg')
    if not p:
        sys.exit('找不到 ffmpeg：装好后放进 PATH，或在 config.toml 的 [tools] ffmpeg 写绝对路径')
    return p


def secrets():
    """密钥：先读 config 指定的 env 文件，进程环境变量优先。值只在内存里用，不落盘、不打印。"""
    out = {}
    f = path('secrets', 'env_file')
    if f and f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                out[k.replace('export ', '').strip()] = v.strip().strip('"').strip("'")
    out.update({k: v for k, v in os.environ.items() if k.isupper()})
    return out


def secret(name, *aliases):
    """取密钥；aliases 是同一把钥匙的别名（例如百炼的 key 有人存成 QWEN_API_KEY）。"""
    s = secrets()
    for k in (name, *aliases):
        if s.get(k):
            return s[k]
    sys.exit(f'缺少密钥 {name}：写进 {get("secrets", "env_file")}（或设成环境变量）')


def provider(kind):
    """某个环节用哪家：voice / lipsync / vision / asr / music。"""
    return get('providers', kind)


def ca_file():
    """python.org 版 Python 不带根证书：优先 certifi，其次系统证书包。"""
    try:
        import certifi
        return certifi.where()
    except ImportError:
        for p in ('/etc/ssl/cert.pem', '/etc/ssl/certs/ca-certificates.crt'):
            if Path(p).exists():
                return p
    return None
