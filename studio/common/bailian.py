"""阿里云百炼（DashScope，北京地域）调用：临时空间上传、异步任务提交与轮询、千问视觉/全模态问答。只用标准库。
密钥取 DASHSCOPE_API_KEY（别名 QWEN_API_KEY）。所需模型要先在百炼控制台开通。"""
import base64, json, ssl, time, urllib.error, urllib.request, uuid
from pathlib import Path
from studio.common import config

HOST = 'https://dashscope.aliyuncs.com'
CTX = ssl.create_default_context(cafile=config.ca_file())


def _key():
    return config.secret('DASHSCOPE_API_KEY', 'QWEN_API_KEY')


def _req(url, body=None, headers=None, timeout=600, raw=False):
    h = {'Authorization': f'Bearer {_key()}', **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode(); h['Content-Type'] = 'application/json'
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=timeout, context=CTX)
        if raw:  # 流式：交给调用方逐行读
            return r
        with r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors='replace')[:1000]
        if 'not activated' in msg:
            msg += '\n——这个模型还没在百炼控制台开通：https://bailian.console.aliyun.com/ → 模型广场搜模型名 → 开通'
        raise RuntimeError(f'百炼 HTTP {e.code} {url}: {msg}') from None


def upload(path, model):
    """传到百炼临时空间（48 小时有效），返回 oss:// 地址；提交任务时要带 oss=True。"""
    p = Path(path)
    pol = _req(f'{HOST}/api/v1/uploads?action=getPolicy&model={model}')['data']
    key = f"{pol['upload_dir']}/{uuid.uuid4().hex[:8]}_{p.name}"
    fields = {'OSSAccessKeyId': pol['oss_access_key_id'], 'Signature': pol['signature'], 'policy': pol['policy'],
              'x-oss-object-acl': pol['x_oss_object_acl'], 'x-oss-forbid-overwrite': pol['x_oss_forbid_overwrite'],
              'key': key, 'success_action_status': '200'}
    b = uuid.uuid4().hex
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
    parts += [f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{p.name}"\r\n'
              f'Content-Type: application/octet-stream\r\n\r\n'.encode(), p.read_bytes(), f'\r\n--{b}--\r\n'.encode()]
    req = urllib.request.Request(pol['upload_host'], data=b''.join(parts), headers={'Content-Type': f'multipart/form-data; boundary={b}'})
    urllib.request.urlopen(req, timeout=1800, context=CTX).read()
    return f'oss://{key}'


def call(path, body, oss=False, async_=False):
    h = {}
    if oss:
        h['X-DashScope-OssResourceResolve'] = 'enable'
    if async_:
        h['X-DashScope-Async'] = 'enable'
    return _req(f'{HOST}/api/v1/{path}', body, h)


def wait(task_id, poll=10, log=print):
    t0 = time.time()
    while True:
        o = _req(f'{HOST}/api/v1/tasks/{task_id}')
        st = o['output']['task_status']
        if st == 'SUCCEEDED':
            log(f'done {task_id} in {time.time() - t0:.0f}s')
            return o
        if st in ('FAILED', 'UNKNOWN', 'CANCELED'):
            raise RuntimeError(f'百炼任务失败 {task_id}: {json.dumps(o["output"], ensure_ascii=False)[:600]}')
        time.sleep(poll)


def download(url, out):
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=1800, context=CTX) as r:
        out.write_bytes(r.read())
    return out


def ask_json(text, images=(), video=None, omni=False):
    """千问看图/看视频，回 JSON。omni=True 用全模态模型（能听声音），否则用视觉模型。"""
    content = [{'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + base64.b64encode(Path(i).read_bytes()).decode()}}
               for i in images]
    if video:
        content.append({'type': 'video_url', 'video_url': {'url': 'data:video/mp4;base64,' + base64.b64encode(Path(video).read_bytes()).decode()}})
    content.append({'type': 'text', 'text': text})
    model = config.get('providers', 'bailian_omni_model' if omni else 'bailian_vision_model')
    body = {'model': model, 'messages': [{'role': 'user', 'content': content}]}
    if omni:  # 全模态模型只支持流式
        body.update({'stream': True, 'modalities': ['text']})
    else:
        body['response_format'] = {'type': 'json_object'}
    url = f'{HOST}/compatible-mode/v1/chat/completions'
    if not omni:
        out = _req(url, body)['choices'][0]['message']['content']
    else:
        out = ''
        for line in _req(url, body, raw=True):
            line = line.decode().strip()
            if line.startswith('data:') and line != 'data: [DONE]':
                for c in json.loads(line[5:]).get('choices', []):
                    out += (c.get('delta') or {}).get('content') or ''
    out = out.strip()
    if not out.startswith(('{', '[')):  # 模型偶尔包一层 ```json 或前后加话：取第一个 { 到最后一个 }
        a, b = out.find('{'), out.rfind('}')
        out = out[a:b + 1] if a >= 0 < b else out
    return json.loads(out)
