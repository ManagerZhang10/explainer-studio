"""看图/看视频回 JSON：按 config 的 providers.vision 选 Gemini 或百炼千问。
listen=True 表示要连声音一起判断（质检要听 BGM 和人声）：Gemini 本身能听；百炼换全模态模型。"""
import base64, json, ssl, time, urllib.request
from pathlib import Path
from studio.common import config


def _gemini(text, images, video, tries=4, timeout=400):
    s = config.secrets()
    base = config.secret('GEMINI_BASE_URL').rstrip('/')
    model = s.get('GEMINI_MODEL', 'gemini-2.5-flash')
    parts = [{'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(Path(i).read_bytes()).decode()}} for i in images]
    if video:
        parts.append({'inline_data': {'mime_type': 'video/mp4', 'data': base64.b64encode(Path(video).read_bytes()).decode()}})
    parts.append({'text': text})
    body = json.dumps({'contents': [{'parts': parts}], 'generationConfig': {
        'temperature': 0.2, 'maxOutputTokens': 8192, 'responseMimeType': 'application/json'}}).encode()
    ctx = ssl.create_default_context(cafile=config.ca_file())
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(f'{base}/models/{model}:generateContent', data=body, headers={
                'Content-Type': 'application/json', 'x-goog-api-key': config.secret('GEMINI_API_KEY')})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                out = json.loads(r.read())
            return json.loads(out['candidates'][0]['content']['parts'][0].get('text', ''))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(10 * (a + 1))
    raise last


def ask_json(text, images=(), video=None, listen=False):
    if config.provider('vision') == 'bailian':
        from studio.common import bailian
        return bailian.ask_json(text, images, video, omni=listen)
    return _gemini(text, images, video)
