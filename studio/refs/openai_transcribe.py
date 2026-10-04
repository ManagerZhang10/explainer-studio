"""OpenAI 语音转写（标准库 multipart，verbose_json 带分句时间戳）。单文件上限 25MB，超了先抽音轨。"""
import json
import os
import ssl
import sys
import time
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from studio.common import config  # noqa: E402

SSL = ssl.create_default_context(cafile=config.ca_file())


def _multipart(fields, files):
    b = '----studio' + uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out += [f'--{b}\r\n'.encode(), f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode(), str(v).encode(), b'\r\n']
    for k, (fn, data, ct) in files.items():
        out += [f'--{b}\r\n'.encode(), f'Content-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'.encode(),
                f'Content-Type: {ct}\r\n\r\n'.encode(), data, b'\r\n']
    out.append(f'--{b}--\r\n'.encode())
    return b''.join(out), f'multipart/form-data; boundary={b}'


def transcribe(path, model='whisper-1', tries=3, language='zh'):
    s = config.secrets()
    base = s.get('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    key = config.secret('OPENAI_API_KEY')
    data = open(path, 'rb').read()
    if len(data) > 24 * 1024 * 1024:
        raise ValueError(f'{path} 超过 25MB，先抽成低码率单声道音轨')
    ct0 = 'audio/mpeg' if str(path).endswith('.mp3') else 'audio/mp4'
    body, ct = _multipart({'model': model, 'language': language, 'response_format': 'verbose_json'},
                          {'file': (os.path.basename(path), data, ct0)})
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(f'{base}/audio/transcriptions', data=body,
                                         headers={'Authorization': f'Bearer {key}', 'Content-Type': ct})
            with urllib.request.urlopen(req, timeout=600, context=SSL) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (a + 1))
    raise last


if __name__ == '__main__':
    r = transcribe(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'whisper-1')
    print(json.dumps({'n_segments': len(r.get('segments', [])), 'duration': r.get('duration'), 'text': r.get('text', '')[:120]},
                     ensure_ascii=False, indent=1))
