#!/usr/bin/env python3
"""fal.ai 调用：上传本地文件、走队列跑模型、下载结果。只用标准库。"""
import json, mimetypes, os, ssl, sys, time, urllib.request, urllib.error
from pathlib import Path
from studio.common import config

KEY = config.secret('FAL_KEY')
# python.org 版 Python 不带根证书，用 certifi 或系统证书包
CTX = ssl.create_default_context(cafile=config.ca_file())
urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=CTX)))
H = {'Authorization': f'Key {KEY}', 'Content-Type': 'application/json'}

def _req(url, data=None, method=None, headers=None, timeout=600):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or H)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code} {url}: {e.read().decode(errors="replace")[:2000]}') from None
    return json.loads(body) if body else {}

def upload(path):
    p = Path(path)
    ct = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
    init = _req('https://rest.alpha.fal.ai/storage/upload/initiate?storage_type=fal-cdn-v3',
                json.dumps({'content_type': ct, 'file_name': p.name}).encode())
    urllib.request.urlopen(urllib.request.Request(init['upload_url'], data=p.read_bytes(), method='PUT',
                           headers={'Content-Type': ct}), timeout=1800).read()
    return init['file_url']

def run(endpoint, payload, poll=5, log=print):
    sub = _req(f'https://queue.fal.run/{endpoint}', json.dumps(payload).encode())
    status_url, resp_url = sub['status_url'], sub['response_url']
    log(f'submitted {endpoint} request_id={sub.get("request_id")}')
    t0 = time.time()
    while True:
        st = _req(status_url + '?logs=0', headers=H)
        s = st.get('status')
        if s == 'COMPLETED':
            break
        if s not in ('IN_QUEUE', 'IN_PROGRESS'):
            raise RuntimeError(f'{endpoint} status {st}')
        time.sleep(poll)
    log(f'done {endpoint} in {time.time()-t0:.0f}s')
    return _req(resp_url, headers=H)

def download(url, out):
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=1800) as r:
        out.write_bytes(r.read())
    return out

if __name__ == '__main__':
    # python3 fal.py upload <file>
    if sys.argv[1] == 'upload':
        print(upload(sys.argv[2]))
