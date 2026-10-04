"""edge-tts per scene -> mp3 + word boundaries. Also builds the caption track."""
import asyncio
import json
import re
from pathlib import Path

import edge_tts

VOICE = "zh-CN-YunxiNeural"   # 男声，技术讲解，语速稳
RATE = "+10%"
PITCH = "+0Hz"
from common import config
OUT = config.path("lecture", "project") / "work" / "audio"


async def _one(text, mp3_path, rate):
    comm = edge_tts.Communicate(text, VOICE, rate=rate, pitch=PITCH)
    marks = []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                marks.append({
                    "offset": chunk["offset"] / 1e7,      # 100ns ticks -> seconds
                    "duration": chunk["duration"] / 1e7,
                    "text": chunk["text"],
                })
    return marks


def synth(key, text, rate=RATE):
    OUT.mkdir(parents=True, exist_ok=True)
    mp3 = OUT / f"{key}.mp3"
    marks = asyncio.run(_one(text, mp3, rate))
    return mp3, marks


def split_captions(text, max_chars=16):
    """Sentence -> caption chunks that fit one line.

    Never breaks inside a latin token (visualtoken) or a （）pair, and never
    leaves an orphan closing bracket at the start of a chunk.
    """
    normalized = re.sub(r"\s+", " ", text).strip()
    terms = ("视觉令牌", "语言模型", "神经网络", "自注意力", "连接器", "高分辨率",
             "固定长度", "视觉特征", "输入序列", "预填充", "多模态", "向量",
             "位置", "特征", "解码", "训练", "评测", "数据", "图像", "图片", "切块", "计算")
    technical_words = "|".join(re.escape(term) for term in sorted(terms, key=len, reverse=True))
    tokens = re.findall(r"（[^）]*）|\([^)]*\)|[A-Za-z0-9]+(?:[ ._-][A-Za-z0-9]+)*|" + technical_words + r"|.", normalized)
    chunks, current = [], ""
    for token in tokens:
        if current and len(current) + len(token) > max_chars and token not in "，。！？；：、,.!?;:":
            chunks.append(current.strip())
            current = ""
        current += token
        if token in "，。！？；,.!?;" and current.strip():
            chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks or [normalized]


def duration_of(mp3_path):
    import subprocess
    r = subprocess.run(["ffmpeg", "-i", str(mp3_path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    if not m:
        raise RuntimeError(f"no duration for {mp3_path}")
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s


if __name__ == "__main__":
    import sys
    mp3, marks = synth("probe", "图片是怎么变成视觉 token 的？三步：切块、展平、投影。")
    print(mp3, duration_of(mp3), "marks:", len(marks))
    print(split_captions("视觉 token 不对应物体，因为格子是固定大小的，小物体只占一格。"))
