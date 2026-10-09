#!/usr/bin/env python3
"""文字动效短视频：先出关键帧总览 + 浏览器预览，确认后再逐帧渲染 + 混音。

动画是一个单文件 HTML，约定（模板见 studio/motion/template/index.html）：
  - 所有画面状态是 render(t) 的纯函数，页面暴露 window.__seek(t)；
  - URL 不带 #seek 时自动循环播放（= 预览），带 #seek 时只响应 __seek（= 渲染）。

配置文件 motion.json 和 HTML 放在一起（默认找 <名字>.motion.json，其次同目录 motion.json）：
  {"duration": 20, "fps": 30, "width": 1080, "height": 1920, "selector": "#stage",   # width/height = 舞台 CSS 尺寸
   "output_size": "720x1280",                       # 可选：输出分辨率（同比例缩放，默认 = 舞台尺寸）
   "preview": [0.5, 3, 7.2],                       # 可选：preview 默认截这些秒
   "bgm":  {"file": "bgm-tech.mp3", "volume": 0.45, "fade_in": 0.2, "fade_out": 1.8},
   "cues": [{"t": 1.35, "file": "keyboard/type-fast.mp3", "volume": 0.55}, …]}
素材路径：绝对路径 > 相对 motion.json 所在目录 > 相对 --sfx-dir / --bgm-dir（默认 config.toml 的 [motion] sfx_dir / bgm_dir）。

  studio motion init <目录>                         复制模板（index.html + motion.json）起步
  studio motion preview <html> [--times 1,3.5,7 | --n 12] [--cols 6] [-o 总览.png] [--open]
  studio motion render  <html> [-o out.mp4] [--duration 2] [--fps 30] [--size 720x1280] [--workers 4]
"""
import argparse, asyncio, json, shutil, subprocess, sys, tempfile, time, webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio.common import config  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULTS = {'duration': 10.0, 'fps': 30, 'width': 1080, 'height': 1920, 'selector': '#stage'}


# ---------- 配置 ----------

def find_spec(html, given=None):
    if given:
        return Path(given).expanduser().resolve()
    for p in (html.with_suffix('.motion.json'), html.parent / 'motion.json'):
        if p.exists():
            return p
    return None


def load_spec(a):
    html = Path(a.html).expanduser().resolve()
    if not html.exists():
        sys.exit(f'找不到动画 HTML：{html}')
    sp = find_spec(html, a.config)
    spec = dict(DEFAULTS)
    if sp:
        spec.update(json.loads(sp.read_text()))
    if getattr(a, 'duration', None): spec['duration'] = a.duration
    if getattr(a, 'fps', None): spec['fps'] = a.fps
    if getattr(a, 'size', None):
        spec['output_size'] = a.size
    ow, oh = (int(x) for x in str(spec.get('output_size') or f"{spec['width']}x{spec['height']}").lower().split('x'))
    if abs(ow / oh - spec['width'] / spec['height']) > 0.01 or ow % 2 or oh % 2:
        sys.exit(f"输出分辨率 {ow}x{oh} 要和舞台 {spec['width']}x{spec['height']} 同比例、且宽高都是偶数")
    spec['out_w'], spec['out_h'], spec['scale'] = ow, oh, ow / spec['width']
    if getattr(a, 'selector', None): spec['selector'] = a.selector
    return html, sp, spec


def resolve_asset(name, spec_path, base_dir, kind):
    p = Path(name).expanduser()
    cands = [p] if p.is_absolute() else ([spec_path.parent / p] if spec_path else []) + ([base_dir / p] if base_dir else [])
    for c in cands:
        if c.exists():
            return c
    sys.exit(f'找不到{kind}素材 {name}：试过 {[str(c) for c in cands] or "（没配 " + kind + " 目录）"}。'
             f'用 --{"bgm" if kind == "配乐" else "sfx"}-dir 指定，或写进 config.toml 的 [motion]')


# ---------- 浏览器 ----------

async def open_page(br, html, spec, errors):
    page = await br.new_page(viewport={'width': spec['width'], 'height': spec['height']}, device_scale_factor=spec['scale'])
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: errors.append(str(e)))
    await page.goto(html.as_uri() + '#seek')
    await page.evaluate('document.fonts.ready.then(() => 0)')
    if not await page.evaluate('typeof window.__seek === "function"'):
        sys.exit('页面没有暴露 window.__seek(t)：照 studio/motion/template/index.html 的约定写')
    el = await page.query_selector(spec['selector'])
    return page, el


async def shot(page, el, spec, t, fmt='jpeg'):
    await page.evaluate('t => window.__seek(t)', t)
    kw = {'type': fmt, **({'quality': 95} if fmt == 'jpeg' else {})}
    if el:
        return await el.screenshot(**kw)
    return await page.screenshot(clip={'x': 0, 'y': 0, 'width': spec['width'], 'height': spec['height']}, **kw)


async def launch(pw, channel):
    return await pw.chromium.launch(**({'channel': channel} if channel else {}))


# ---------- preview ----------

async def _preview(html, spec, times, out, cols, thumb, channel):
    import io
    from PIL import Image, ImageDraw, ImageFont
    from playwright.async_api import async_playwright
    errors, ims = [], []
    async with async_playwright() as pw:
        br = await launch(pw, channel)
        page, el = await open_page(br, html, spec, errors)
        for t in times:
            ims.append(Image.open(io.BytesIO(await shot(page, el, spec, t, 'png'))).convert('RGB'))
        await br.close()
    w = thumb; h = round(w * spec['height'] / spec['width']); gap = 8
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * w + (cols + 1) * gap, rows * h + (rows + 1) * gap), (40, 40, 40))
    try:
        font = ImageFont.truetype('DejaVuSans-Bold.ttf', max(16, w // 10))
    except OSError:
        font = ImageFont.load_default(size=max(16, w // 10))
    for i, (t, im) in enumerate(zip(times, ims)):
        im = im.resize((w, h), Image.LANCZOS); d = ImageDraw.Draw(im)
        label = f'{t:.2f}s'; bb = d.textbbox((0, 0), label, font=font); pad = 6
        d.rectangle([0, 0, bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad + 4], fill=(0, 0, 0))
        d.text((pad - bb[0], pad - bb[1] + 2), label, fill=(255, 214, 0), font=font)
        sheet.paste(im, (gap + (i % cols) * (w + gap), gap + (i // cols) * (h + gap)))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return errors


def cmd_preview(a):
    html, sp, spec = load_spec(a)
    if a.times:
        times = [float(x) for x in a.times.split(',') if x.strip()]
    elif a.n:
        d = spec['duration']; times = [round(d * (i + 0.5) / a.n, 2) for i in range(a.n)]
    elif spec.get('preview'):
        times = [float(x) for x in spec['preview']]
    else:
        d = spec['duration']; times = [round(d * (i + 0.5) / 12, 2) for i in range(12)]
    out = Path(a.output).expanduser().resolve() if a.output else html.with_name(html.stem + '_keyframes.png')
    errors = asyncio.run(_preview(html, spec, times, out, a.cols or min(len(times), 6), a.thumb, a.channel))
    print(f'{len(times)} 帧总览 -> {out}')
    print('配置：', sp or '（没找到 motion.json，用默认值）', f"{spec['width']}x{spec['height']} {spec['duration']}s")
    if errors:
        print('页面报错：', errors[:5])
    if a.open:
        webbrowser.open(html.as_uri())   # 不带 #seek = 自动循环播放
        print('已在浏览器打开预览（自动循环）：', html.as_uri())
    if errors:
        sys.exit(1)


# ---------- render ----------

async def _frames(html, spec, silent, workers, channel, ff):
    from playwright.async_api import async_playwright
    fps, n = spec['fps'], int(round(spec['duration'] * spec['fps']))
    errors, t0 = [], time.time()
    step = (n + workers - 1) // workers
    async with async_playwright() as pw:
        br = await launch(pw, channel)
        pages = [await open_page(br, html, spec, errors) for _ in range(workers)]

        async def run(k, page, el):
            a, b = k * step, min(n, (k + 1) * step)
            seg = silent.with_name(f'seg{k}.mp4')
            if a >= b:
                return None
            p = subprocess.Popen([ff, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', str(fps),
                                  '-c:v', 'mjpeg', '-i', '-', '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
                                  '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-colorspace', 'bt709',
                                  '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', str(seg)], stdin=subprocess.PIPE)
            for f in range(a, b):
                p.stdin.write(await shot(page, el, spec, f / fps))
                if k == 0 and (f - a) % (fps * 5) == 0:
                    print(f'  worker0 {f - a}/{b - a}  {time.time() - t0:.0f}s', flush=True)
            p.stdin.close(); p.wait()
            return seg

        segs = [s for s in await asyncio.gather(*[run(k, pg, el) for k, (pg, el) in enumerate(pages)]) if s]
        await br.close()
    lst = silent.with_name('list.txt')
    lst.write_text(''.join(f"file '{s}'\n" for s in segs))
    subprocess.run([ff, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(silent)], check=True)
    print(f'{n} 帧 / {workers} 路 用时 {time.time() - t0:.0f}s')
    return errors


def mix(silent, out, spec, sp, sfx_dir, bgm_dir, ff):
    D = spec['duration']
    args = [ff, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(silent)]
    fl, labels, k = [], [], 1
    bgm = spec.get('bgm')
    if bgm and bgm.get('file'):
        args += ['-i', str(resolve_asset(bgm['file'], sp, bgm_dir, '配乐'))]
        fi, fo = bgm.get('fade_in', 0.2), bgm.get('fade_out', 1.8)
        chain = f'[{k}:a]atrim=0:{D},asetpts=PTS-STARTPTS'
        if fi: chain += f',afade=t=in:d={fi}'
        if fo: chain += f',afade=t=out:st={max(0, D - fo)}:d={fo}'
        fl.append(chain + f",volume={bgm.get('volume', 0.45)}[bgm]"); labels.append('[bgm]'); k += 1
    for i, c in enumerate(c for c in spec.get('cues', []) if c['t'] < D):
        args += ['-i', str(resolve_asset(c['file'], sp, sfx_dir, '音效'))]
        ms = int(round(c['t'] * 1000))
        fl.append(f"[{k}:a]volume={c.get('volume', 0.6)},adelay={ms}|{ms}[s{i}]"); labels.append(f'[s{i}]'); k += 1
    if not labels:
        print('motion.json 里没有 bgm 也没有 cues：出无声视频')
        shutil.copy(silent, out); return
    fl.append(''.join(labels) + f'amix=inputs={len(labels)}:duration=longest:normalize=0,apad,atrim=0:{D}[a]')
    args += ['-filter_complex', ';'.join(fl), '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
             '-t', str(D), '-movflags', '+faststart', str(out)]
    subprocess.run(args, check=True)


def cmd_render(a):
    html, sp, spec = load_spec(a)
    ff = config.ffmpeg()
    out = Path(a.output).expanduser().resolve() if a.output else html.with_suffix('.mp4')
    out.parent.mkdir(parents=True, exist_ok=True)
    sfx_dir = Path(a.sfx_dir).expanduser() if a.sfx_dir else config.path('motion', 'sfx_dir')
    bgm_dir = Path(a.bgm_dir).expanduser() if a.bgm_dir else (config.path('motion', 'bgm_dir') or sfx_dir)
    tmp = Path(tempfile.mkdtemp(prefix='.motion_', dir=out.parent))   # 临时片段，结束即删
    try:
        silent = tmp / 'silent.mp4'
        errors = asyncio.run(_frames(html, spec, silent, max(1, a.workers), a.channel, ff))
        mix(silent, out, spec, sp, sfx_dir, bgm_dir, ff)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"成片 -> {out}  ({spec['out_w']}x{spec['out_h']} {spec['fps']}fps {spec['duration']}s)")
    if errors:
        print('页面报错：', errors[:5]); sys.exit(1)


def cmd_init(a):
    d = Path(a.dir).expanduser().resolve(); d.mkdir(parents=True, exist_ok=True)
    for name in ('index.html', 'motion.json'):
        if (d / name).exists():
            sys.exit(f'{d / name} 已存在，不覆盖')
    for name in ('index.html', 'motion.json'):
        shutil.copy(HERE / 'template' / name, d / name)
    print(f'已复制模板到 {d}：先改 index.html 的 render(t)，再 studio motion preview {d / "index.html"} --open')


def main():
    ap = argparse.ArgumentParser(prog='studio motion', description='文字动效短视频：HTML 动画 -> 关键帧总览 / 浏览器预览 -> 逐帧渲染 + 混音')
    sub = ap.add_subparsers(dest='cmd', required=True)

    def common(p):
        p.add_argument('html', help='动画 HTML（render(t) + window.__seek）')
        p.add_argument('--config', help='motion.json 路径（默认 <名字>.motion.json 或同目录 motion.json）')
        p.add_argument('--duration', '--dur', type=float, help='时长（秒），覆盖 motion.json')
        p.add_argument('--size', help='输出分辨率，如 720x1280（和舞台同比例；默认 = 舞台尺寸）')
        p.add_argument('--selector', help='截取的舞台元素，默认 #stage')
        p.add_argument('--channel', help='用系统浏览器，如 chrome（默认 Playwright 自带 Chromium）')
        p.add_argument('-o', '--output')

    p = sub.add_parser('init', help='复制动画模板起步'); p.add_argument('dir'); p.set_defaults(fn=cmd_init)
    p = sub.add_parser('preview', help='关键帧总览图（每格标秒数），可选直接打开浏览器预览'); common(p)
    p.add_argument('--times', help='逗号分隔的秒数，如 0.5,3,7.2')
    p.add_argument('--n', type=int, help='均匀取 N 帧')
    p.add_argument('--cols', type=int)
    p.add_argument('--thumb', type=int, default=270, help='每格宽度（像素）')
    p.add_argument('--open', action='store_true', help='同时在浏览器打开 HTML 自动循环预览')
    p.set_defaults(fn=cmd_preview)
    p = sub.add_parser('render', help='逐帧渲染 + 配乐 + 音效 -> mp4'); common(p)
    p.add_argument('--fps', type=int)
    p.add_argument('--workers', type=int, default=4, help='并行页面数')
    p.add_argument('--sfx-dir', help='音效素材目录（默认 config [motion] sfx_dir）')
    p.add_argument('--bgm-dir', help='配乐素材目录（默认 config [motion] bgm_dir，没配则同 sfx_dir）')
    p.set_defaults(fn=cmd_render)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
