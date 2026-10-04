"""Chapter doc + designed slides -> spoken-word scene script (JSON).

Factual source of truth = the chapter markdown. Slide text only supplies wording
and diagram element ids; narration must not invent facts that are absent from
the chapter doc.
"""
import json
import sys
from pathlib import Path

import extract_slides as E
from common import config, deepseek, extract_json, cn_len

DOCS = config.path("lecture", "course_docs")
OUT = config.path("lecture", "project") / "work" / "scripts"
OUT.mkdir(parents=True, exist_ok=True)

SYSTEM = """你是短视频口播稿作者，服务对象是初学者，不能假设已经理解 LLM 内部结构。
你要把一份 VLM 讲义的一个切片，改写成一条 2~3 分钟竖屏/横屏都能看的科普视频的口播稿。

硬规则：
1. 事实只能来自给你的讲义正文。讲义里没有的数字、模型名、结论，一律不许自己补。不确定就改写成讲义里已有的、更保守的说法。
2. 全篇口播总长 580~720 个中文字符。英文单词、数字、符号不计入这个数；最终时长以实际配音测量为准，不靠字数验收。
3. 口语化。一句话一个意思。不要用 Markdown、不要用 LaTeX、不要写公式符号（shape 写成「N 乘 d」这种口播形式，矩阵写成「矩阵」）。
4. 遇到英文术语，第一次出现时用「中文说法（English Term）」这种口播形式，例如「视觉令牌（visual token）」。后面再出现就用中文简写。
5. 每段口播对应屏幕上的一页 slide。你要决定：这一支视频只讲哪几页（slides 里给了序号和内容），跳过的页就不出现。
6. 每页口播 40~110 个中文字符，2~4 句，按句号/问号断句。
7. 开头 hook 25~45 字，必须在 3 秒内让人想知道「后面是什么」，可以用反常识、痛点、身份或一个具体的数字对比。不要说「大家好」「今天我们来聊聊」。
8. 结尾 outro 25~45 字，把这一支视频讲的那一件事钉死，并说明「下一支讲什么」。不要说「点赞关注」。
9. 不要在口播里念 slide 上已经大字写出来的标题。你在解释它，不是在复述它。
10. reveal 字段：这一页该按什么顺序把图里的元素讲出来。只能从该页提供的 svg_ids 里选，按讲解顺序排。可以不选全，但顺序必须符合口播叙述顺序。
11. 每一章只选一个核心问题，其他内容只用于解释这个问题。不要为了覆盖全章塞入互不相关的知识点。
12. 每场景给 visual 字段生成大字简图。title不超过18个汉字，subtitle解释图的目的，nodes包含2到5个节点，每个节点有label(不超过9字)、detail(不超过18字)、color(gray/blue/purple/orange/green)。links是[起点索引,终点索引,短标签]数组，仅表示真实的数据流或因果关系，并列比较不画箭头。example给具体例子，note给适用条件或结论。首次出现的术语先用生活例子解释。不要把教学实验数字泛化成通用定律。

只输出 JSON，不要任何解释文字。格式：
{"title":"这一支视频的标题，14 字以内",
 "hook":"开场口播",
 "scenes":[{"slide":3,"narration":"...","reveal":["p12-img","p12-flat"],"visual":{"title":"图片先切成小块","subtitle":"每块变成一个向量，再交给后续网络","nodes":[{"label":"图片","detail":"一张猫的照片","color":"gray"},{"label":"小块","detail":"按固定网格切分","color":"blue"},{"label":"向量","detail":"保留每块的位置","color":"purple"}],"links":[[0,1,"切分"],[1,2,"投影"]],"example":"格子里可能只有半只猫，不等于一个物体。","note":"这是固定网格切块的教学示意。"}}],
 "outro":"结尾口播"}
slide 用你在 slides 列表里看到的序号。"""


def build_prompt(day, slides):
    doc = (DOCS / f"day{day:02d}.md").read_text(encoding="utf-8")
    thumb = E.part_for(day).parent.parent / "media"
    lines = []
    for i, s in enumerate(slides, 1):
        lines.append(f"--- slide {i} ---")
        lines.append(f"类型: {'章节过渡页' if s['is_divider'] else '内容页'}")
        if s["h1"]:
            lines.append(f"大标题: {s['h1']}")
        if s["word"]:
            lines.append(f"大字: {s['word']}")
        if s["dq"]:
            lines.append(f"设问: {s['dq']}")
        if s["sub"]:
            lines.append(f"副标题: {s['sub']}")
        if s["gloss"]:
            lines.append(f"术语解释: {s['gloss'][:200]}")
        if s["svg_ids"]:
            lines.append(f"图中可逐个点亮的元素 id: {s['svg_ids']}")
    user = (
        f"# 讲义正文（day{day:02d}，这是事实来源）\n\n{doc}\n\n"
        f"# 这一章的页面（slides）\n\n" + "\n".join(lines) +
        "\n\n现在写这一支视频的口播稿 JSON。"
    )
    return user, doc


def gen(day, attempts=3):
    _, slides = E.extract(day)
    user, _ = build_prompt(day, slides)
    last_err = None
    for att in range(1, attempts + 1):
        raw = deepseek(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            temperature=0.35,
        )
        try:
            data = extract_json(raw)
            total = cn_len(data["hook"]) + cn_len(data["outro"]) + sum(
                cn_len(s["narration"]) for s in data["scenes"]
            )
            valid = {i for i in range(1, len(slides) + 1)}
            picked = [s["slide"] for s in data["scenes"]]
            assert 3 <= len(picked) <= len(slides), f"scene count {len(picked)}"
            assert all(p in valid for p in picked), f"bad slide index {picked}"
            assert len(set(picked)) == len(picked), "duplicate slide index"
            data["_total_cn"] = total
            data["_day"] = day
            data["_attempts"] = att
            ok_range = 580 <= total <= 720
            if not ok_range:
                last_err = f"total_cn={total} out of range"
                user += f"\n\n（上一次总字数是 {total} 个汉字，偏{'长' if total > 720 else '短'}，请整体{'压缩' if total > 720 else '扩写'}到 650 字左右。）"
                continue
            for s in data["scenes"]:
                idx = s["slide"] - 1
                s["_reveal"] = [i for i in (s.get("reveal") or []) if i in slides[idx]["svg_ids"]]
            return data, last_err
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            user += f"\n\n（上次输出不合法：{last_err}。请只输出合法 JSON。）"
    raise RuntimeError(f"day{day:02d}: script generation failed after {attempts}: {last_err}")


if __name__ == "__main__":
    day = int(sys.argv[1])
    data, _ = gen(day)
    p = OUT / f"day{day:02d}.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(p), "total_cn": data["_total_cn"],
                      "scenes": len(data["scenes"]), "attempts": data["_attempts"]}, ensure_ascii=False))
