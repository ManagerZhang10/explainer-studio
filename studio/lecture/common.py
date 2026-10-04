"""Shared config + DeepSeek client. Stdlib only (per AGENTS.md)."""
import json, os, ssl, time, urllib.request, urllib.error
from pathlib import Path
import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parents[2]))
from studio.common import config  # noqa: E402

def load_env():
    return config.secrets()


CFG = load_env()
_SSL = ssl.create_default_context(cafile=config.ca_file())


def deepseek(messages, max_tokens=16000, temperature=0.4, retries=4, timeout=1800):
    key = CFG["DEEPSEEK_API_KEY"]
    base = CFG["DEEPSEEK_BASE_URL"].rstrip("/")
    model = CFG["DEEPSEEK_V4_PRO_MODEL"]
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    payload = json.dumps(body).encode("utf-8")
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                f"{base}/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            )
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as resp:
                out = json.loads(resp.read().decode("utf-8"))
            content = out["choices"][0]["message"].get("content") or ""
            if content.strip():
                return content
            last = RuntimeError("empty content (max_tokens eaten by reasoning)")
        except Exception as e:  # noqa: BLE001
            last = e
        if attempt < retries - 1:
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"deepseek failed after {retries}: {last}")


def extract_json(text):
    """Pull the first top-level JSON object out of a model reply."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in reply")
    depth, in_str, esc = 0, False, False
    for i, ch in enumerate(text[start:], start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("unterminated JSON object")


def cn_len(text):
    return sum(1 for ch in text if "一" <= ch <= "鿿")
