"""Pull structured facts out of an existing Track A slide part: titles, sub, gloss, SVG ids."""
import html
import re
from pathlib import Path

from common import config
PARTS = config.path("lecture", "course_slides") / "parts"
DECK = PARTS.parent / "deck.html"


def _text(fragment):
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def part_for(day):
    """day: 1..14 -> parts/NN_dayNN.html"""
    for p in sorted(PARTS.glob("*_day*.html")):
        if p.stem.endswith(f"day{day:02d}"):
            return p
    raise FileNotFoundError(f"no part for day{day:02d}")


def split_sections(markup):
    out, depth, start = [], 0, None
    for m in re.finditer(r"<section\b|</section>", markup):
        if m.group(0) == "<section":
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start is not None:
                out.append(markup[start:m.end()])
                start = None
    return out


def extract(day):
    part = part_for(day)
    markup = part.read_text(encoding="utf-8")
    slides = []
    for sec in split_sections(markup):
        classes = re.search(r'class="([^"]*)"', sec)
        classes = classes.group(1) if classes else ""
        title = re.search(r'data-title="([^"]*)"', sec)
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", sec, re.S)
        sub = re.search(r'<div class="sub"[^>]*>(.*?)</div>', sec, re.S)
        gloss = re.search(r'<div class="gloss"[^>]*>(.*?)</div>', sec, re.S)
        talk = re.search(r'<div class="talk"[^>]*>(.*?)</div>', sec, re.S)
        word = re.search(r'<div class="word"[^>]*>(.*?)</div>', sec, re.S)
        dq = re.search(r'<div class="dq"[^>]*>(.*?)</div>', sec, re.S)
        svg_ids = re.findall(r'\bid="([^"]+)"', sec)
        slides.append({
            "classes": classes,
            "data_title": title.group(1) if title else "",
            "is_divider": "divider" in classes,
            "h1": _text(h1.group(1)) if h1 else "",
            "sub": _text(sub.group(1)) if sub else "",
            "gloss": _text(gloss.group(1)) if gloss else "",
            "talk": _text(talk.group(1)) if talk else "",
            "word": _text(word.group(1)) if word else "",
            "dq": _text(dq.group(1)) if dq else "",
            "svg_ids": [i for i in svg_ids if not i.startswith("ar")],
            "raw_len": len(sec),
        })
    return part, slides


if __name__ == "__main__":
    import json, sys
    day = int(sys.argv[1])
    part, slides = extract(day)
    print(part)
    print(json.dumps(slides, ensure_ascii=False, indent=1))
