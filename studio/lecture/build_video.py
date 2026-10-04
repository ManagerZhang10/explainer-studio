#!/usr/bin/env python3
"""Scene script -> AI voice + animated explainer mp4.

Pipeline per chapter:
  script JSON -> per-scene edge-tts audio -> padded wav timeline
               -> one standalone HTML (deck CSS + chosen slides + overlay)
               -> deterministic WAAPI frames via Playwright -> ffmpeg mp4
"""
import hashlib
import base64
import fcntl
import mimetypes
from html import escape
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import extract_slides as E
import tts as T
import visuals

from common import config
ROOT = config.path("lecture", "project")
WORK = ROOT / "work"
DECKDIR = config.path("lecture", "course_slides")
SCRIPTS = WORK / "scripts"
OUT = ROOT / "out"
SCRIPT_OVERRIDE = None

BASE_CSS = """
:root{--bg:#F5F5F7;--ink:#1D1D1F;--muted:#6E6E73;--faint:#A1A1A6;--accent:#0071E3;--font:'PingFang SC','Helvetica Neue',Arial,sans-serif;--mono:Menlo,monospace}
*{box-sizing:border-box;margin:0;padding:0}
body{color:var(--ink);font-family:var(--font)}
.slide{position:absolute;inset:0;display:none;flex-direction:column}
.slide.active{display:flex}
.kicker{font-size:22px;color:var(--muted);letter-spacing:.1em}
.kicker b{color:var(--accent);margin-right:20px}
.sub{color:var(--muted)}
.diagbox{flex:1;min-height:0;position:relative;background:white;border-radius:26px;box-shadow:0 14px 48px #0000000d}
.diagbox svg{position:absolute;inset:0;width:100%;height:100%}
.sv text{font-family:'PingFang SC','Helvetica Neue',sans-serif}
.gloss{position:absolute;color:var(--muted)}
"""
MARKERS = '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs></svg>'
VISUAL_RUNTIME = """
function layoutArrows(slide){}
function boxIn(element, reference){
  const bounds=element.getBBox(), matrix=reference.getCTM().inverse().multiply(element.getCTM());
  const points=[[bounds.x,bounds.y],[bounds.x+bounds.width,bounds.y],[bounds.x,bounds.y+bounds.height],[bounds.x+bounds.width,bounds.y+bounds.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(matrix));
  const xs=points.map(point=>point.x), ys=points.map(point=>point.y);
  return {l:Math.min(...xs),t:Math.min(...ys),r:Math.max(...xs),b:Math.max(...ys)};
}
"""

W, H, FPS = 1920, 1080, 30
GAP = 0.28          # silence between scenes
GAP_BIG = 0.55      # before the outro card


# ---------------------------------------------------------------- audio
def build_audio(day, scenes, outdir):
    """synth each scene, pad to exact slot length, concat to one wav."""
    outdir.mkdir(parents=True, exist_ok=True)
    wavs = []
    for sc in scenes:
        # content hash in the key: a reworded scene must never reuse old audio
        key = f"day{day:02d}_{sc['id']}_{hashlib.md5(sc['narration'].encode()).hexdigest()[:8]}"
        mp3 = WORK / "audio" / f"{key}.mp3"
        marks_path = WORK / "audio" / f"{key}.marks.json"
        if mp3.exists() and mp3.stat().st_size > 0 and marks_path.exists():
            marks = json.loads(marks_path.read_text())
        else:
            mp3, marks = T.synth(key, sc["narration"])
            marks_path.write_text(json.dumps(marks))
        sc["speech_ms"] = round(T.duration_of(mp3) * 1000)
        sc["marks"] = marks
        slot = sc["speech_ms"] + round(sc.get("gap", GAP) * 1000)
        padded = outdir / f"{key}.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-af", "apad", "-t",
             f"{slot/1000:.3f}", "-ar", "24000", "-ac", "1", str(padded)],
            check=True,
        )
        wavs.append(padded)
    lst = outdir / "concat.txt"
    lst.write_text("\n".join(f"file '{w.name}'" for w in wavs), encoding="utf-8")
    final = outdir / "voice.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(final)], check=True)
    return final


# ---------------------------------------------------------------- timeline
def build_timeline(day, scenes):
    t = 0.0
    out = []
    for sc in scenes:
        gap = sc.get("gap", GAP)
        slot = sc["speech_ms"] + gap * 1000
        caps = []
        speech = sc["speech_ms"] / 1000.0
        marks = sc.pop("marks", [])
        spans = marks or [{"offset": 0.1, "duration": speech - 0.1,
                           "text": sc["narration"]}]
        for mark in spans:
            chunks = T.split_captions(mark["text"])
            total_chars = sum(len(chunk) for chunk in chunks) or 1
            current = t + mark["offset"]
            for chunk in chunks:
                duration = mark["duration"] * len(chunk) / total_chars
                caps.append({"t0": round(current, 3),
                             "t1": round(min(t + speech, current + duration), 3),
                             "text": chunk})
                current += duration
        for previous, following in zip(caps, caps[1:]):
            if following["t0"] < previous["t1"]:
                following["t0"] = previous["t1"]
            if following["t1"] <= following["t0"]:
                raise ValueError("invalid or overlapping caption boundaries")
        sc["t0"] = round(t, 3)
        sc["dur"] = round(slot / 1000.0, 3)
        sc["caps"] = caps
        reveal_times = []
        cues = sc.pop("cues", [])
        for index, target in enumerate(sc.get("reveal", [])):
            cue = cues[index] if index < len(cues) else ""
            compact_cue = re.sub(r"\s+", "", cue)
            elapsed = None
            combined = ""
            for caption in caps:
                combined += re.sub(r"\s+", "", caption["text"])
                if compact_cue and compact_cue in combined:
                    elapsed = max(0.0, caption["t0"] - t - 0.20)
                    break
            reveal_times.append(elapsed if elapsed is not None else
                                index * speech * 0.65 / max(1, len(sc.get("reveal", []))))
        sc["reveal_times"] = reveal_times
        out.append(sc)
        t += slot / 1000.0
    return out


# ---------------------------------------------------------------- html
RUNTIME = r"""
const TL = window.__TL__;
let cur = -1, anims = [], capIdx = -1;

function slideEl(i){ return document.querySelectorAll('#stage .slide')[i]; }

function buildScene(i){
  if(window.__ring){window.__ring.remove();window.__ring=null;}
  anims.forEach(a=>{try{a.cancel()}catch(e){}}); anims=[];
  const nodes = document.querySelectorAll('#stage .slide');
  nodes.forEach(n=>n.classList.remove('active'));
  const sc = TL.scenes[i];
  window.__visualNodes = [];
  const el = nodes[sc.slide];
  el.classList.add('active');
  layoutArrows(el);
  const D = sc.dur*1000;

  // whole-slide motion: short rise, then a slow push-in
  const kb = 1.0;
  anims.push(el.animate([
    {opacity:1, transform:'translateY(0) scale(1)'},
    {opacity:1, transform:'translateY(0) scale(1)', offset:0.05},
    {opacity:1, transform:`translateY(0) scale(${kb})`}
  ], {duration:D, fill:'forwards', easing:'cubic-bezier(.22,.8,.3,1)'}));

  // header copy lifts in behind the push
  const head = el.querySelectorAll(':scope > .kicker, :scope > h1, :scope > .sub');
  head.forEach((h,i)=>{
    anims.push(h.animate([{opacity:0,transform:'translateY(14px)'},{opacity:1,transform:'none'}],
      {duration:460, delay:90+i*80, fill:'backwards', easing:'cubic-bezier(.22,.8,.3,1)'}));
  });

  // progressive reveal of the diagram, in narration order
  const rev = sc.reveal || [];
  if(rev.length){
    const svg = el.querySelector('svg');
    const scope = svg || el;
    const kids = Array.from(scope.children).filter(n=>n.tagName!=='defs'&&n.tagName!=='marker');
    const step = (D*0.70)/rev.length;
    const start = 260;
    rev.forEach((id,j)=>{
      const tgt = el.querySelector('#'+CSS.escape(id));
      if(tgt){
        if(!id.includes('-cell')) tgt.querySelectorAll('rect').forEach(rectangle=>{
          const fill = rectangle.dataset.originalFill || rectangle.getAttribute('fill');
          rectangle.dataset.originalFill = fill;
          window.__visualNodes.push({rectangle, fill, delay:(sc.reveal_times[j] ?? ((start+j*step)/1000))*1000});
        });
      }
    });
    // everything not in the reveal list recedes, then comes back for the final read
    const revSet = new Set(rev);
    kids.forEach(k=>{
      if(el.classList.contains('teaching')) return;
      if(revSet.has(k.id) || revSet.has((k.querySelector('[id]')||{}).id)) return;
      anims.push(k.animate([{opacity:1},{opacity:0.86}],
        {duration:260, delay:start, fill:'forwards', easing:'ease-out'}));
      anims.push(k.animate([{opacity:0.86},{opacity:1}],
        {duration:420, delay:Math.max(start+120, D*0.78), fill:'backwards', easing:'ease-in'}));
    });
    // marching ring on the element being talked about
    if(rev.length && svg){
      const ring = document.createElementNS('http://www.w3.org/2000/svg','rect');
      ring.setAttribute('fill','none'); ring.setAttribute('stroke','#0071E3');
      ring.setAttribute('stroke-width','3'); ring.setAttribute('rx','12');
      ring.setAttribute('opacity','0'); svg.appendChild(ring);
      window.__ring = ring;
    }
  }

  const gloss = el.querySelector('.gloss');
  if(gloss) anims.push(gloss.animate([{opacity:0,transform:'translateY(10px)'},{opacity:1,transform:'none'}],
    {duration:420, delay:Math.min(D*0.45, 1400), fill:'backwards'}));
  anims.forEach(animation=>animation.pause());
}

function seek(t){
  let i = TL.scenes.findIndex(s => t >= s.t0 && t < s.t0 + s.dur);
  if(i<0) i = TL.scenes.length-1;
  if(i !== cur){ buildScene(i); cur = i; capIdx = -1; }
  const sc = TL.scenes[i];
  const local = Math.max(0, (t - sc.t0))*1000;
  anims.forEach(a=>{ try{ a.currentTime = local; }catch(e){} });
  window.__visualNodes.forEach(node=>{
    const progress = Math.max(0,Math.min(1,(local-node.delay)/420));
    const target = node.fill.match(/^#([a-f0-9]{6})$/i);
    if(target){
      const channels=[0,2,4].map(offset=>parseInt(target[1].slice(offset,offset+2),16));
      node.rectangle.setAttribute('fill','rgb('+channels.map(channel=>Math.round(245+(channel-245)*progress)).join(',')+')');
    }
  });

  // marching ring geometry follows the element currently being named
  if(window.__ring && (sc.reveal||[]).length){
    const el = slideEl(sc.slide);
    const localSeconds = Math.max(0,t-sc.t0);
    const times = sc.reveal_times.length ? sc.reveal_times : sc.reveal.map((_, index)=>index*sc.dur*.70/sc.reveal.length);
    const eligible = times.map((time,index)=>({time,index})).filter(cue=>cue.time<=localSeconds).sort((first,second)=>first.time-second.time);
    const idx = eligible.length ? eligible[eligible.length-1].index : 0;
    window.__ring.setAttribute('opacity', eligible.length && localSeconds<sc.dur*.86 ? '.9' : '0');
    const tgt = el && el.querySelector('#'+CSS.escape(sc.reveal[idx]||''));
    if(tgt){ const bounds = boxIn(tgt,window.__ring);
      window.__ring.setAttribute('x', bounds.l-7); window.__ring.setAttribute('y', bounds.t-7);
      window.__ring.setAttribute('width', bounds.r-bounds.l+14); window.__ring.setAttribute('height', bounds.b-bounds.t+14); }
  }

  // progress bar
  const pct = Math.min(100, (t/TL.total)*100);
  document.getElementById('bar').style.width = pct.toFixed(2)+'%';
  const sn = document.getElementById('pagenum');
  if(sn) sn.textContent = (sc.label||'');

  // caption
  let k = sc.caps.findIndex(c => t >= c.t0 && t < c.t1);
  if(k < 0) k = t < sc.caps[0].t0 ? 0 : sc.caps.length-1;
  if(k !== capIdx){
    capIdx = k;
    const box = document.getElementById('caps');
    box.innerHTML = '';
    sc.caps.forEach((c,j)=>{
      const d = document.createElement('div');
      const rel = j - k;
      d.className = 'capline' + (rel===0 ? ' on' : ' gone');
      Array.from(c.text).forEach(ch=>{ const s=document.createElement('span'); s.textContent=ch; d.appendChild(s); });
      box.appendChild(d);
    });
  }
  const lines = document.querySelectorAll('.capline');
  const cur2 = lines[capIdx];
  if(cur2){
    const spans = cur2.children, n = spans.length;
    const c = sc.caps[capIdx];
    const p = Math.max(0, Math.min(1, (t - c.t0) / Math.max(0.01, c.t1 - c.t0)));
    for(let k2=0;k2<n;k2++) spans[k2].style.opacity = (k2 <= p*n) ? '1' : '0.42';
  }
  return i;
}

window.__seek = seek;
window.__ready = false;
requestAnimationFrame(()=>{ buildScene(0); cur=0; window.__ready = true; });
"""

PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title>
<style>{css}</style>
<style>
html,body{{height:100%;background:var(--bg);overflow:hidden}}
#stage{{position:absolute;left:50%;top:50%;width:1920px;height:1080px;transform:translate(-50%,-50%)}}
/* ---- video-only overlay layer ---- */
#ui{{position:absolute;inset:0;pointer-events:none;z-index:50}}
/* reserve a bottom band for captions; shrink the slide so nothing collides */
#stage .slide{{padding:66px 92px 190px}}
#stage h1{{font-size:58px;margin-top:14px}}
#stage .sub{{font-size:28px;line-height:1.3}}
#stage .diagbox,#stage .fig,#stage .tblwrap{{margin-top:26px}}
#stage .diagbox.pad svg{{width:calc(100% - 36px);height:calc(100% - 28px)}}
#stage .gloss{{bottom:106px;font-size:22px;line-height:1.3;left:92px;right:92px}}
#stage .glpad{{display:none}}
#stage .teaching h1{{font-size:72px}}
#stage .teaching .sub{{font-size:34px}}
#stage .teaching .example{{margin-top:20px;font-size:32px;line-height:1.4}}
#stage .teaching .gloss{{font-size:27px;color:var(--muted)}}
#barwrap{{position:absolute;left:0;right:0;top:0;height:5px;background:rgba(0,0,0,.07)}}
#bar{{height:100%;width:0;background:var(--accent);transition:none}}
#pagenum{{position:absolute;right:56px;top:38px;font:500 22px/1 var(--mono);color:var(--faint);letter-spacing:.1em}}
#caps{{position:absolute;left:0;right:0;bottom:26px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:8px}}
.capline{{font-size:42px;font-weight:600;line-height:1.32;color:#fff;letter-spacing:.01em;
  padding:10px 26px;border-radius:16px;background:rgba(20,20,22,.82);
  box-shadow:0 10px 34px rgba(0,0,0,.24);white-space:nowrap;
  opacity:0;transform:none}}
.capline.on{{opacity:1;transform:none}}
.capline.past{{opacity:.46}}
.capline.gone{{display:none}}
.capline span{{transition:none}}
/* full-bleed title / end cards */
#card{{position:absolute;inset:0;display:none;flex-direction:column;align-items:center;justify-content:center;
  background:var(--bg);text-align:center;padding:0 220px}}
#card.show{{display:flex}}
#card .k{{font:500 22px/1 var(--font);letter-spacing:.14em;color:var(--accent);margin-bottom:26px}}
#card .t{{font-size:96px;font-weight:600;letter-spacing:-.02em;line-height:1.16}}
#card .s{{font-size:34px;color:var(--muted);margin-top:30px;line-height:1.5}}
#card .rule{{width:96px;height:5px;background:var(--accent);border-radius:3px;margin:44px 0}}
</style></head>
<body>
<div id="stage">
{markers}
{sections}
<section class="slide" id="endcard"><div id="card" class="show">
  <div class="k">{end_label}</div>
  <div class="t">{next_title}</div>
  <div class="rule"></div>
  <div class="s">{next_hint}</div>
</div></section>
</div>
<div id="ui">
  <div id="barwrap"><div id="bar"></div></div>
  <div id="pagenum"></div>
  <div id="caps"></div>
</div>
<script>window.__TL__ = {timeline};</script>
<script>{runtime}</script>
</body></html>
"""


# ---------------------------------------------------------------- render
def render(html_path, timeline, outdir, scale=1):
    from playwright.sync_api import sync_playwright

    outdir.mkdir(parents=True, exist_ok=True)
    total = timeline["total"]
    nframes = int(total * FPS) + 1
    url = html_path.as_uri()
    with sync_playwright() as p:
        b = p.chromium.launch(args=[
            "--disable-gpu", "--hide-scrollbars", "--force-color-profile=srgb",
            "--disable-frame-rate-limit", "--disable-gpu-vsync",
            "--disable-lcd-text", "--font-render-hinting=none",
        ])
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=scale)
        pg.goto(url)
        pg.wait_for_function("window.__ready === true", timeout=30000)
        pg.evaluate("document.fonts.ready")
        import time as _t
        t0 = _t.time()
        for i in range(nframes):
            t = i / FPS
            pg.evaluate("t => window.__seek(t)", t)
            pg.screenshot(path=str(outdir / f"{i:06d}.jpg"), type="jpeg", quality=92)
            if i % 300 == 0:
                rate = (i + 1) / max(1e-6, _t.time() - t0)
                print(f"    {i}/{nframes}  {rate:.1f} fps  eta {(nframes-i)/max(rate,1e-6)/60:.1f} min", flush=True)
        b.close()
    got = len(list(outdir.glob("*.jpg"))) if outdir.exists() else 0
    if got < nframes * 0.98:
        raise RuntimeError(f"frame capture incomplete: {got}/{nframes}")
    return got


def mux(frames_dir, audio, out_mp4, fps=FPS):
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-framerate", str(fps), "-i", str(frames_dir / "%06d.jpg"),
        "-i", str(audio),
        "-c:v", "libx264", "-threads", "2", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(out_mp4),
    ], check=True)
    return out_mp4


# ---------------------------------------------------------------- main
def main(day, keep_frames=False, scale=1, html_only=False):
    lockdir = WORK / "locks"
    lockdir.mkdir(parents=True, exist_ok=True)
    with (lockdir / f"day{day:02d}.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return build_chapter(day, keep_frames, scale, html_only)


def embed_assets(markup):
    def replace(match):
        asset = DECKDIR / match.group(2)
        if not asset.is_file():
            raise FileNotFoundError(f"missing slide asset: {asset}")
        mime = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
        encoded = base64.b64encode(asset.read_bytes()).decode("ascii")
        return f'{match.group(1)}="data:{mime};base64,{encoded}"'
    return re.sub(r'(src|href)="(media/[^"<>]+)"', replace, markup)


def build_chapter(day, keep_frames=False, scale=1, html_only=False):
    script_path = SCRIPT_OVERRIDE or SCRIPTS / f"day{day:02d}.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))
    self_contained = all(scene.get("visual") for scene in script["scenes"])
    if self_contained:
        slides = [{"dq": script.get("question", script["scenes"][0]["visual"].get("subtitle", "")), "word": ""}]
    else:
        _, slides = E.extract(day)
    series = script.get("series", "知识点讲解" if SCRIPT_OVERRIDE else "VLM 基本功")
    visual_sections = {}
    for scene_index, scene in enumerate(script["scenes"]):
        if scene.get("visual"):
            section, reveal = visuals.render_visual(scene["visual"], f"d{day:02d}s{scene_index}", series)
            visual_sections[scene_index + 1 if self_contained else scene["slide"]] = section
            scene["_reveal"] = reveal

    raw = [{"id": "hook", "kind": "card", "slide": -1, "narration": script["hook"],
            "label": "", "gap": GAP}]
    for k, s in enumerate(script["scenes"]):
        raw.append({"id": f"s{k}", "kind": "slide", "slide": k + 1 if self_contained else s["slide"],
                    "source_slide": s["slide"],
                    "narration": s["narration"], "reveal": s.get("_reveal") or [],
                    "cues": [node.get("cue", node["label"]) for node in s.get("visual", {}).get("nodes", [])],
                    "label": f"{k + 1}/{len(script['scenes'])}", "gap": GAP})
    raw.append({"id": "outro", "kind": "end", "slide": -2,
                "narration": script["outro"], "label": "", "gap": GAP_BIG})

    vdir = WORK / "video" / f"day{day:02d}"
    vdir.mkdir(parents=True, exist_ok=True)
    audio = build_audio(day, raw, vdir / "audio")
    timeline = build_timeline(day, raw)

    # card scenes are not real slides; point them at the last element index and
    # let the runtime overlay its own markup instead.
    hook_html = f"""<section class="slide" id="hookcard"><div id="card" class="show">
  <div class="k">{escape(series)} · Day {day:02d}</div>
  <div class="t">{escape(script['title'])}</div>
  <div class="rule"></div>
  <div class="s">{escape(slides[0]['dq'] if slides[0]['dq'] else slides[0]['word'])}</div>
</div></section>"""

    order, seen = [], set()
    for s_ in timeline:
        if s_["kind"] == "slide" and s_["slide"] not in seen:
            seen.add(s_["slide"]); order.append(s_["slide"])
    secs = [] if self_contained else E.split_sections(E.part_for(day).read_text(encoding="utf-8"))
    chosen = [visual_sections.get(index) or embed_assets(secs[index - 1]) for index in order]
    # node 0 is the hook card, then one node per slide in narration order,
    # last node is the end card.
    pos = {sl: 1 + i for i, sl in enumerate(order)}
    for s_ in timeline:
        if s_["kind"] == "slide":
            s_["slide"] = pos[s_["slide"]]
        elif s_["kind"] == "card":
            s_["slide"] = 0
        else:
            s_["slide"] = 1 + len(order)
    import chapters
    nxt, nxt_hint = script.get("next_title", ""), script.get("next_hint", "")
    if not nxt:
        if SCRIPT_OVERRIDE:
            nxt, nxt_hint = "试着解释一个新例子", script["scenes"][-1].get("visual", {}).get("note", "")
        else:
            nxt, nxt_hint = chapters.next_card(day)
    if self_contained:
        arrow_runtime, markers = VISUAL_RUNTIME, MARKERS
    else:
        deck_source = (DECKDIR / "deck.html").read_text(encoding="utf-8")
        arrow_runtime = deck_source[deck_source.index("  function boxIn("):
                                    deck_source.index("  window.deckShow=show;")]
        markers = re.search(r'<svg width="0".*?</svg>', deck_source, re.S).group(0)
    css = BASE_CSS if self_contained else (WORK / "deck.css").read_text(encoding="utf-8") + "\n" + (DECKDIR.parent / "_base" / "extra.css").read_text(encoding="utf-8")
    html = PAGE.format(
        title=escape(script["title"]), css=css,
        sections=hook_html + "\n" + "\n".join(chosen),
        next_title=escape(nxt), next_hint=escape(nxt_hint),
        end_label=escape(script.get("end_label", "带走这一点" if SCRIPT_OVERRIDE and not script.get("next_title") else "下一支")),
        timeline=json.dumps(timeline, ensure_ascii=False), runtime=arrow_runtime + RUNTIME,
        markers=markers,
    )
    tl = {"scenes": timeline, "total": timeline[-1]["t0"] + timeline[-1]["dur"]}
    if not 120 <= tl["total"] <= 180:
        raise RuntimeError(f"chapter duration outside 120-180s: {tl['total']}")
    html = html.replace(
        "<script>window.__TL__ = " + json.dumps(timeline, ensure_ascii=False) + ";",
        "<script>window.__TL__ = " + json.dumps(tl, ensure_ascii=False) + ";",
    )
    html_path = vdir / "page.html"
    html_path.write_text(html, encoding="utf-8")
    (vdir / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=2), encoding="utf-8")
    def timestamp(seconds):
        milliseconds = round(seconds * 1000)
        hours, remainder = divmod(milliseconds, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        whole_seconds, milliseconds = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"
    captions = [caption for scene in timeline for caption in scene["caps"]]
    (vdir / "captions.srt").write_text("\n\n".join(
        f"{index}\n{timestamp(caption['t0'])} --> {timestamp(caption['t1'])}\n{caption['text']}"
        for index, caption in enumerate(captions, 1)), encoding="utf-8")
    if html_only:
        return html_path, tl
    frames = vdir / "frames"
    if frames.exists():
        shutil.rmtree(frames)
    n = render(html_path, tl, frames, scale=scale)
    destination = OUT / f"day{day:02d}_{script['title']}.mp4"
    temporary = OUT / f".day{day:02d}.partial.mp4"
    mp4 = mux(frames, audio, temporary)
    os.replace(mp4, destination)
    mp4 = destination
    if not keep_frames:
        shutil.rmtree(frames, ignore_errors=True)
    print(json.dumps({
        "day": day, "mp4": str(mp4), "frames": n,
        "total_sec": round(tl["total"], 2),
        "speech_sec": round(sum(s["speech_ms"] for s in timeline) / 1000, 2),
        "total_cn": script.get("_total_cn"), "scenes": len(timeline),
    }, ensure_ascii=False))
    return mp4


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("day", nargs="?", type=int, default=1)
    parser.add_argument("--script", type=Path)
    parser.add_argument("--project-dir", type=Path)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--html", action="store_true")
    arguments = parser.parse_args()
    d, keep, sc = arguments.day, arguments.keep, arguments.scale
    SCRIPT_OVERRIDE = arguments.script.resolve() if arguments.script else None
    if arguments.project_dir:
        ROOT = arguments.project_dir.resolve()
        WORK, OUT, SCRIPTS = ROOT / "work", ROOT / "out", ROOT / "work" / "scripts"
        T.OUT = WORK / "audio"
    if arguments.html:
        html, tl = main(d, scale=sc, html_only=True)
        print(json.dumps({"day": d, "html": str(html), "total_sec": round(tl["total"], 2),
                          "scenes": len(tl["scenes"]),
                          "speech_sec": round(sum(s["speech_ms"] for s in tl["scenes"]) / 1000, 2)},
                         ensure_ascii=False))
    else:
        main(d, keep_frames=keep, scale=sc)
