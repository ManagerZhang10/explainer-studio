"""Track A chapter titles — the index the end card points at."""

TITLES = {
    1: "懂 LLM 的人该补哪五层",
    2: "图片怎么变成视觉 token",
    3: "CLIP / SigLIP 到底学到了什么",
    4: "视觉特征怎么接进 LLM：三类接口",
    5: "视觉 token 进了 LLM 之后",
    6: "VLM 到底吃什么数据",
    7: "一张图走完 VLM：端到端 shape trace",
    8: "训练为什么分阶段",
    9: "高分辨率与动态分辨率",
    10: "为什么会识图却不会定位",
    11: "幻觉与语言捷径怎么测",
    12: "视频多出来的那一维",
    13: "为什么又慢又贵",
    14: "VLM 六问阅读卡",
}


def next_card(day):
    """(title, hint) for the end card. Day 14 wraps back to the start."""
    nxt = day + 1
    if nxt > 14:
        return "VLM 基本功 · 全部 14 章", "从 Day 01 重新过一遍，或者挑一章直接看"
    return f"Day {nxt:02d} · {TITLES[nxt]}", TITLES[nxt]
