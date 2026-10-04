from html import escape
import re
import base64
import mimetypes
from pathlib import Path


COLORS = {
    "gray": "#ECEEF1", "blue": "#DCEBFC", "purple": "#EADFF8",
    "orange": "#FCE8D5", "green": "#DEF1E4",
}


def render_visual(visual, scene_id, series="知识点讲解"):
    nodes = visual["nodes"]
    if not 2 <= len(nodes) <= 5:
        raise ValueError("visual requires 2-5 nodes")
    markup = []
    positions = []
    width = (1640 - (len(nodes) - 1) * 48) / len(nodes)
    for index, node in enumerate(nodes):
        left = 10 + index * (width + 48)
        positions.append((left, left + width, left + width / 2))
        font = min(44, (width - 30) / max(1, len(node["label"])))
        detail = node.get("detail", "")
        lines, current = [], ""
        for token in re.findall(r"[A-Za-z0-9]+(?:[ _./+-][A-Za-z0-9]+)*|.", detail):
            if current and len(current) + len(token) > 10:
                lines.append(current)
                current = ""
            current += token
        if current:
            lines.append(current)
        text = "".join(f'<text x="{left + width / 2}" y="{285 + line_index * 38}" text-anchor="middle" font-size="29" fill="#48515d">{escape(line)}</text>'
                       for line_index, line in enumerate(lines))
        markup.append(f'<g id="{scene_id}-node{index}"><rect x="{left}" y="155" width="{width}" height="210" rx="26" fill="{COLORS.get(node.get("color"), COLORS["blue"])}"/>'
                      f'<text x="{left + width / 2}" y="225" text-anchor="middle" font-size="{font}" font-weight="600" fill="#1D1D1F">{escape(node["label"])}</text>{text}</g>')
    for source, target, *label in visual.get("links", []):
        if source == target or not 0 <= source < len(nodes) or not 0 <= target < len(nodes):
            raise ValueError("invalid diagram link")
        start = positions[source][1 if target > source else 0] + (8 if target > source else -8)
        end = positions[target][0 if target > source else 1] + (-10 if target > source else 10)
        if abs(source - target) == 1:
            path = f'M{start},260 H{end}'
            label_y = 242
        else:
            path = f'M{start},175 V110 H{end} V175'
            label_y = 98
        markup.append(f'<path d="{path}" fill="none" stroke="#64748b" stroke-width="4" marker-end="url(#ar)"/>')
        if label:
            markup.append(f'<text x="{(start + end)/2}" y="{label_y}" text-anchor="middle" font-size="22" fill="#64748b">{escape(label[0])}</text>')
    if visual.get("kind") == "patches":
        grid = int(visual.get("grid", 4))
        if not 2 <= grid <= 8:
            raise ValueError("patch grid must be 2-8")
        asset = visual.get("asset")
        image = ""
        if asset:
            path = Path(asset)
            content = base64.b64encode(path.read_bytes()).decode("ascii")
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            image = f'<image href="data:{mime};base64,{content}" x="70" y="65" width="360" height="360" preserveAspectRatio="xMidYMid slice"/>'
        else:
            for row in range(8):
                for column in range(8):
                    fill = "#A7D8EE" if row < 4 else "#A8CBA0"
                    if row in (3, 4, 5) and column in (3, 4):
                        fill = "#EFBE85"
                    image += f'<rect x="{70 + column*45}" y="{65 + row*45}" width="45" height="45" fill="{fill}"/>'
        cuts = "".join(f'<path d="M{70 + index*360/grid},65 V425 M70,{65 + index*360/grid} H430" stroke="white" stroke-width="4"/>' for index in range(1, grid))
        cells = "".join(f'<rect x="{650 + (index % 8)*48}" y="{180 + (index // 8)*60}" width="34" height="42" rx="5" fill="{COLORS["purple"]}"/>' for index in range(grid*grid))
        vector = "".join(f'<rect x="{1260 + column*36}" y="{145 + row*64}" width="24" height="{24 + (column+row)%3*12}" rx="4" fill="{COLORS["green"]}"/>' for row in range(3) for column in range(6))
        markup = [f'<g id="{scene_id}-node0">{image}{cuts}<text x="250" y="40" text-anchor="middle" font-size="34">图片按网格切块</text></g>',
                  f'<g id="{scene_id}-node1">{cells}<text x="835" y="110" text-anchor="middle" font-size="34">{grid} × {grid} = {grid*grid} 个位置</text><text x="835" y="410" text-anchor="middle" font-size="28" fill="#64748b">每个块保留自己的位置</text></g>',
                  f'<g id="{scene_id}-node2">{vector}<text x="1370" y="90" text-anchor="middle" font-size="34">每块变成一个向量</text><text x="1370" y="400" text-anchor="middle" font-size="28" fill="#64748b">这里只画三个向量示例</text><text x="1370" y="440" text-anchor="middle" font-size="24" fill="#64748b">实际每个块都对应一个向量</text></g>',
                  '<path d="M460,250 H595" stroke="#64748b" stroke-width="4" fill="none" marker-end="url(#ar)"/><path d="M1080,250 H1200" stroke="#64748b" stroke-width="4" fill="none" marker-end="url(#ar)"/>']
        reveal = [f"{scene_id}-node{index}" for index in range(3)]
    elif visual.get("kind") == "timeline":
        selected = set(visual.get("selected_frames", [0, 3, 5]))
        count = int(visual.get("frame_count", 6))
        event_frame = visual.get("event_frame")
        if not 2 <= count <= 8 or not selected or not selected.issubset(set(range(count))):
            raise ValueError("invalid video sampling illustration")
        markup = ['<path d="M70,290 H1590" stroke="#94a3b8" stroke-width="5"/>']
        for index in range(count):
            left = 80 + index * (1450 / count)
            fill = COLORS["orange"] if index == event_frame else COLORS["blue"] if index in selected else COLORS["gray"]
            selection = "关键事件没抽到" if index == event_frame and index not in selected else "抽到这一帧" if index in selected else "未输入模型"
            markup.append(f'<g id="{scene_id}-frame{index}"><rect x="{left}" y="125" width="{1280/count}" height="120" rx="16" fill="{fill}"/><circle cx="{left+45}" cy="175" r="16" fill="#EFBE85"/><path d="M{left+30},220 L{left+70},195 L{left+100},220" stroke="#8BAD87" stroke-width="8" fill="none"/><text x="{left+60}" y="335" font-size="28" text-anchor="middle">时刻 {index+1}</text><text x="{left+60}" y="390" font-size="26" text-anchor="middle" fill="#475569">{selection}</text></g>')
        reveal = [f"{scene_id}-frame{index}" for index in sorted(selected)]
    elif visual.get("kind") == "matrix":
        labels = visual.get("labels", ["猫", "路牌", "早餐"])
        count = len(labels)
        markup = []
        for row, row_label in enumerate(labels):
            markup.append(f'<text x="420" y="{158 + row * 85}" text-anchor="end" font-size="32">图：{escape(row_label)}</text>')
            markup.append(f'<text x="{505 + row * 180}" y="70" text-anchor="middle" font-size="30">文：{escape(row_label)}</text>')
            for column in range(count):
                matched = row == column
                markup.append(f'<g id="{scene_id}-cell{row}-{column}"><rect x="{430 + column * 180}" y="{105 + row * 85}" width="155" height="70" rx="12" fill="{"#0071E3" if matched else "#ECEEF1"}"/>'
                              f'<text x="{507 + column * 180}" y="{152 + row * 85}" text-anchor="middle" font-size="30" fill="{"white" if matched else "#68717e"}">{"配对" if matched else "不配对"}</text></g>')
        markup.append('<text x="1260" y="200" text-anchor="middle" font-size="40" font-weight="600" fill="#0071E3">配对分数 ↑</text><text x="1260" y="270" text-anchor="middle" font-size="40" fill="#68717e">不配对分数 ↓</text>')
        reveal = [f"{scene_id}-cell{index}-{index}" for index in range(count)]
    else:
        reveal = [f"{scene_id}-node{index}" for index in range(len(nodes))]
    title = escape(visual["title"])
    subtitle = escape(visual.get("subtitle", ""))
    example = escape(visual.get("example", ""))
    note = escape(visual.get("note", ""))
    section = f'''<section class="slide teaching" data-title="{title}">
      <div class="kicker"><b>{escape(series)}</b>一个问题，逐步解释</div>
      <h1>{title}</h1><div class="sub">{subtitle}</div>
      <div class="diagbox"><svg class="sv" viewBox="0 0 1660 470" xmlns="http://www.w3.org/2000/svg">{"".join(markup)}</svg></div>
      <div class="example"><b>例如：</b>{example}</div><div class="gloss">{note}</div>
    </section>'''
    return section, reveal
