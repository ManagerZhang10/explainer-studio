"""Gemini 看图答 JSON（标准库 urllib）。密钥与地址取 GEMINI_API_KEY / GEMINI_BASE_URL / GEMINI_MODEL。"""
import base64
import json
import ssl
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio.common import config  # noqa: E402

SSL = ssl.create_default_context(cafile=config.ca_file())


def call(parts, tries=4, timeout=300, max_tokens=4096):
    s = config.secrets()
    base = config.secret('GEMINI_BASE_URL').rstrip('/')
    model = s.get('GEMINI_MODEL', 'gemini-2.5-flash')
    body = json.dumps({'contents': [{'parts': parts}], 'generationConfig': {
        'temperature': 0.2, 'maxOutputTokens': max_tokens, 'responseMimeType': 'application/json'}}).encode()
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(f'{base}/models/{model}:generateContent', data=body, headers={
                'Content-Type': 'application/json', 'x-goog-api-key': config.secret('GEMINI_API_KEY')})
            with urllib.request.urlopen(req, timeout=timeout, context=SSL) as r:
                out = json.loads(r.read())
            return json.loads(out['candidates'][0]['content']['parts'][0].get('text', ''))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(10 * (a + 1))
    raise last


def img(path):
    return {'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(Path(path).read_bytes()).decode()}}
