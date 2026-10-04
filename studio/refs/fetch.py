"""抖音视频抓取：无头 Chromium 打开页面，从页面自己请求的接口里拿视频地址和元数据，再带 Referer 下载。

  studio refs fetch https://www.douyin.com/video/<id> …           单条
  studio refs fetch https://www.douyin.com/user/<sec_uid> --limit 10   博主最近 N 条

存到 references/creators/<作者>/<日期>_<标题前60字>_<id>.mp4，并追加 manifest.json。
只用于个人学习拆解；尊重平台条款和作者版权，不要转载。"""
import argparse
import asyncio
import datetime as dt
import json
import re
import sys

from common import CREATORS

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
API = ('aweme/v1/web/aweme/detail', 'aweme/v1/web/aweme/post')


def _safe(s, n=60):
    return re.sub(r'[\\/:*?"<>|\n\r\t#@]+', ' ', s or '').strip()[:n].strip()


def _item(a):
    v = a.get('video') or {}
    urls = (v.get('play_addr') or {}).get('url_list') or []
    best = max(v.get('bit_rate') or [], key=lambda b: b.get('bit_rate', 0), default=None)
    if best:
        urls = ((best.get('play_addr') or {}).get('url_list') or []) + urls
    return {'aweme_id': a.get('aweme_id'), 'author': (a.get('author') or {}).get('nickname', 'unknown'),
            'date': dt.datetime.fromtimestamp(a.get('create_time', 0)).strftime('%Y-%m-%d'),
            'desc': a.get('desc', ''), 'duration_min': round((v.get('duration') or a.get('duration') or 0) / 60000, 1),
            'url': f"https://www.douyin.com/video/{a.get('aweme_id')}", 'play': urls}


async def collect(ctx, url, limit):
    page = await ctx.new_page(); found = {}

    async def on_resp(resp):
        if any(k in resp.url for k in API):
            try:
                d = await resp.json()
            except Exception:  # noqa: BLE001
                return
            for a in ([d['aweme_detail']] if d.get('aweme_detail') else d.get('aweme_list') or []):
                found.setdefault(a.get('aweme_id'), _item(a))
    page.on('response', on_resp)
    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
    is_user = '/user/' in url
    for _ in range(40):
        if (not is_user and found) or (is_user and len(found) >= limit):
            break
        if is_user:
            await page.mouse.wheel(0, 4000)
        await asyncio.sleep(1)
    await page.close()
    items = list(found.values())
    if not is_user:
        vid = re.search(r'/video/(\d+)', url)
        items = [i for i in items if not vid or i['aweme_id'] == vid.group(1)][:1]
    return sorted(items, key=lambda i: i['date'], reverse=True)[:limit]


async def main(urls, limit, dry):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        br = await pw.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled', '--no-sandbox'])
        ctx = await br.new_context(user_agent=UA, viewport={'width': 1440, 'height': 900}, locale='zh-CN')
        await ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        for url in urls:
            items = await collect(ctx, url, limit)
            print(f'{url}  ->  {len(items)} 条', flush=True)
            for it in items:
                d = CREATORS / _safe(it['author'], 40)
                f = d / f"{it['date']}_{_safe(it['desc'])}_{it['aweme_id']}.mp4"
                print(f"  {it['date']} {it['duration_min']}分钟 {it['desc'][:40]}", flush=True)
                if dry or f.exists():
                    continue
                for u in it.pop('play'):
                    r = await ctx.request.get(u, headers={'Referer': 'https://www.douyin.com/'}, timeout=300000)
                    if r.ok:
                        body = await r.body()
                        if len(body) > 200_000:
                            d.mkdir(parents=True, exist_ok=True); f.write_bytes(body); break
                else:
                    print('    下载失败', flush=True); continue
                mp = d / 'manifest.json'
                man = json.load(open(mp)) if mp.exists() else []
                man = [m for m in man if m.get('aweme_id') != it['aweme_id']] + [{**it, 'file': str(f)}]
                json.dump(man, open(mp, 'w'), ensure_ascii=False, indent=1)
                print(f'    -> {f}  {f.stat().st_size // 1024} KB', flush=True)
        await br.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('urls', nargs='+'); ap.add_argument('--limit', type=int, default=10)
    ap.add_argument('--dry', action='store_true', help='只列出，不下载')
    a = ap.parse_args()
    sys.exit(asyncio.run(main(a.urls, a.limit, a.dry)))
