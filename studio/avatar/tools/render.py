#!/usr/bin/env python3
"""用无头 Chrome 逐帧跑 engine/core.js + 专题的 scenes.js，JPEG 直接管道给 ffmpeg。
  render.py stills 3.0 9.5 ...          出静帧到 work/stills/（检查用）
  render.py video [--workers 4]         出整条无声视频 work/render/main_silent.mp4 + 音效时间表
  可加 --ver NAME（多版本时区分文件名）、--theme dark
"""
import asyncio, base64, functools, http.server, json, sys, threading, time, urllib.parse
from pathlib import Path
from common import PIPE, TOPIC, FF, FONTS
import subprocess

PORT = 8766


def serve():
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
        def translate_path(self, path):  # /engine、/fonts 指向流水线，其余指向专题目录
            p = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
            if p.startswith('/engine/'): return str(PIPE / 'engine' / p[8:])
            if p.startswith('/fonts/'): return str(FONTS / p[7:])
            return str(TOPIC / p.lstrip('/'))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def qs(ver, theme):
    return f'v={ver}' + (f'&theme={theme}' if theme else '')


async def open_page(br, ver, theme, errors):
    page = await br.new_page(viewport={'width': 1080, 'height': 1920})
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.on('pageerror', lambda e: errors.append(str(e)))
    await page.goto(f'http://127.0.0.1:{PORT}/engine/index.html?{qs(ver, theme)}')
    await page.evaluate('window.ready')
    return page


async def grab(page, f):
    b64 = await page.evaluate("async f => { await renderFrame(f); return document.getElementById('c').toDataURL('image/jpeg', 0.93).slice(23); }", f)
    return base64.b64decode(b64)


async def stills(ver, theme, times):
    from playwright.async_api import async_playwright
    errors = []; out = TOPIC / 'work/stills'; out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        br = await pw.chromium.launch()
        page = await open_page(br, ver, theme, errors)
        for t in times:
            (out / f'{ver}_{float(t):06.2f}.jpg').write_bytes(await grab(page, int(round(float(t) * 30))))
        await br.close()
    print('errors:', errors[:5]) if errors else print('ok', len(times), 'stills ->', out)


async def video(ver, theme, workers):
    from playwright.async_api import async_playwright
    errors = []; out = TOPIC / 'work/render'; out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        br = await pw.chromium.launch()
        p0 = await open_page(br, ver, theme, errors)
        meta = await p0.evaluate('window.META'); cues = await p0.evaluate('window.CUES')
        json.dump(cues, open(out / f'cues_{ver}.json', 'w'))
        n = meta['nFrames']; step = (n + workers - 1) // workers; t0 = time.time()

        async def run(k, page):
            a, b = k * step, min(n, (k + 1) * step)
            seg = out / f'{ver}_seg{k}.mp4'
            ff = subprocess.Popen([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-',
                                   '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
                                   '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', str(seg)], stdin=subprocess.PIPE)
            for f in range(a, b):
                ff.stdin.write(await grab(page, f))
                if k == 0 and (f - a) % 300 == 0: print(f'  worker0 {f - a}/{b - a}  {time.time() - t0:.0f}s', flush=True)
            ff.stdin.close(); ff.wait()
            return seg

        pages = [p0] + [await open_page(br, ver, theme, errors) for _ in range(workers - 1)]
        segs = await asyncio.gather(*[run(k, pg) for k, pg in enumerate(pages)])
        await br.close()
    lst = out / f'{ver}_list.txt'
    lst.write_text(''.join(f"file '{s.resolve()}'\n" for s in segs))
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-c', 'copy', str(out / f'{ver}_silent.mp4')], check=True)
    for s in segs: s.unlink()
    lst.unlink()
    print(f'{ver}: {n} frames in {time.time() - t0:.0f}s', 'errors:', errors[:5])
    if errors: sys.exit(1)


def opt(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name); v = sys.argv[i + 1]; del sys.argv[i:i + 2]; return v
    return default


if __name__ == '__main__':
    ver, theme, workers = opt('--ver', 'main'), opt('--theme'), int(opt('--workers', '4'))
    if not (FONTS / 'noto-sans-sc/index.css').exists(): sys.exit(f'字体还没装：先跑 studio setup（下载到 {FONTS}）')
    serve()
    if sys.argv[1] == 'stills': asyncio.run(stills(ver, theme, sys.argv[2:]))
    else: asyncio.run(video(ver, theme, workers))
