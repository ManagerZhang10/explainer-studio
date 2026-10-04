#!/usr/bin/env python3
"""studio setup：下载渲染用的开源字体（fontsource，OFL 许可）到缓存目录，并检查依赖是否齐全。"""
import importlib.util, io, shutil, ssl, sys, tarfile, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.common import config  # noqa: E402

FONTS = {  # 目录名: (npm 包, 版本)
    'noto-sans-sc': ('@fontsource-variable/noto-sans-sc', '5.3.0'),
    'noto-serif-sc': ('@fontsource-variable/noto-serif-sc', '5.3.0'),
    'archivo-black': ('@fontsource/archivo-black', '5.3.0'),
    'jetbrains-mono': ('@fontsource-variable/jetbrains-mono', '5.3.0'),
}


def fetch_fonts():
    dst = config.CACHE / 'fonts'
    ctx = ssl.create_default_context(cafile=config.ca_file())
    for short, (pkg, ver) in FONTS.items():
        out = dst / short
        if (out / 'index.css').exists():
            print(f'  字体 {short} 已有'); continue
        url = f'https://registry.npmjs.org/{pkg}/-/{pkg.split("/")[1]}-{ver}.tgz'
        data = urllib.request.urlopen(url, context=ctx, timeout=300).read()
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            for m in tf.getmembers():
                rel = m.name.split('/', 1)[1] if '/' in m.name else ''
                if m.isfile() and (rel in ('index.css', 'LICENSE') or (rel.startswith('files/') and rel.endswith('.woff2'))):
                    p = out / rel; p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(tf.extractfile(m).read())
        print(f'  字体 {short} {ver} -> {out}')


def check():
    ok = True
    def row(name, good, hint=''):
        nonlocal ok
        ok &= good
        print(f'  {"✓" if good else "✗"} {name}' + ('' if good else f'  —— {hint}'))
    print('配置文件:', config.CONFIG_PATH, '' if config.CONFIG_PATH.exists() else '（还没有，照 config.example.toml 建一份）')
    row('ffmpeg', bool(config.get('tools', 'ffmpeg') or shutil.which('ffmpeg')), '装 ffmpeg 或在 config.toml 写路径')
    for mod, hint in [('playwright', 'pip install playwright && playwright install chromium'), ('numpy', 'pip install numpy'),
                      ('cv2', 'pip install "opencv-python-headless<5"'), ('PIL', 'pip install pillow')]:
        row(f'python: {mod}', importlib.util.find_spec(mod) is not None, hint)
    row('mlx_whisper（口播对齐用，Apple 芯片）', bool(shutil.which(config.get('tools', 'mlx_whisper', 'mlx_whisper'))), 'pip install mlx-whisper；非 Mac 可换别的 whisper，输出同格式 JSON')
    s = config.secrets()
    for k, why in [('FAL_KEY', '配音、对口型、配乐'), ('GEMINI_API_KEY', '看片质检'), ('GEMINI_BASE_URL', '看片质检')]:
        row(f'密钥 {k}（{why}）', bool(s.get(k)), f'写进 {config.get("secrets", "env_file")}')
    ws = config.workspace()
    row(f'工作区 {ws}', bool(ws and ws.exists()), '在 config.toml 的 [paths] workspace 指一个目录')
    return ok


if __name__ == '__main__':
    print('下载字体 ->', config.CACHE / 'fonts'); fetch_fonts()
    print('检查依赖'); sys.exit(0 if check() else 1)
