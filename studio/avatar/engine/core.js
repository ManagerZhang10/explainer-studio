// core.js — 竖屏口播讲解视频的逐帧渲染核心（1080×1920）。
// 专题自己的画面写在专题根目录的 scenes.js：用 SCENE(id, fn) 给每句口播挂一个画面，动效都挂在词上（at('词', id)）。
// 规则：不放任何「这是数字分身」的自曝或制作统计；摄像头只缩放窗口、不收紧取景（始终整幅画高，头肩完整）。
'use strict';
const Q = new URLSearchParams(location.search);
const VER = Q.get('v') || 'main';
const W = 1080, H = 1920, FPS = 30;
const THEMES = {
  light: { bg: '#F2F3F5', panel: '#FFFFFF', panel2: '#F6F7F9', stroke: '#E3E6EB', text: '#1F2329', dim: '#7A808A', faint: '#C9CED6',
    acc: '#1769FF', accSoft: '#E8F0FF', acc2: '#FF8A1F', acc2Soft: '#FFF0E0', ok: '#1769FF', bad: '#E5484D', green: '#3DBE7A', greenSoft: '#E3F6EC',
    accInk: '#FFFFFF', grid: 'rgba(31,35,41,0.06)', hi: '#FFD84D', capBg: 'rgba(16,18,22,0.78)', shadow: 'rgba(31,35,41,0.10)' },
  dark: { bg: '#0B0B0D', panel: '#16171B', panel2: '#1D1E23', stroke: '#2B2C33', text: '#F3F3F0', dim: '#8E8F96', faint: '#3B3C44',
    acc: '#4D8DFF', accSoft: '#16233F', acc2: '#FF8A1F', acc2Soft: '#3A2410', ok: '#4D8DFF', bad: '#FF5A5F', green: '#3DBE7A', greenSoft: '#123222',
    accInk: '#FFFFFF', grid: 'rgba(243,243,240,0.05)', hi: '#FFD84D', capBg: 'rgba(0,0,0,0.70)', shadow: 'rgba(0,0,0,0.4)' },
};
let C = THEMES.light;
const F = {
  cn: '"Noto Sans SC Variable", "PingFang SC", sans-serif',
  en: '"Archivo Black", "Noto Sans SC Variable", sans-serif',
  mono: '"JetBrains Mono Variable", "Noto Sans SC Variable", monospace',
  serif: '"Noto Serif SC Variable", serif',
};
const LAYOUT = { capY: 1420, top: 400, bottom: 1340, x0: 48, x1: 1032, titleY: 330, smallY: 236, trackerY: 150 };
let BUB = { cx: 862, cy: 1636, r: 168 };
let CARD = { x: 40, y: 150, w: 1000, h: 562 };

const cv = document.getElementById('c');
cv.width = W; cv.height = H;
const ctx = cv.getContext('2d');
let D = null, CFG = {}, CAMS = [], CUES = [], T_NOW = 0, F_NOW = 0;
const IM = {};            // 专题声明的图片：ASSETS = { cat: '/assets/cat.png' }
const SCENES = [];        // [{id, fn, opt}]
let TRACKER = null;       // { items: [...], from: () => 秒, to: () => 秒, active: t => [下标] }
let PLAN = null;          // 专题追加音效：PLAN = () => { cue(at('词','id'), 'pop') }
let ASSETS = {};
const NOISE = [];

// ---------- 小工具 ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, p) => a + (b - a) * p;
const pr = (t, a, d) => clamp((t - a) / d);
const E = {
  o3: p => 1 - Math.pow(1 - p, 3),
  ox: p => (p >= 1 ? 1 : 1 - Math.pow(2, -10 * p)),
  io: p => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
  ob: p => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); },
};
function rng(seed) { let s = (seed >>> 0) || 1; return () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 1000003) / 1000003; }; }
const fmt = n => Math.round(n).toLocaleString('en-US');
const win = (t, a, b, fi = 0.18, fo = 0.16) => Math.min(pr(t, a, fi), 1 - pr(t, b - fo, fo));
const pop = (t, a, d = 0.35) => E.ob(pr(t, a, d));      // 弹出（带一点回弹）
const ease = (t, a, d = 0.4) => E.o3(pr(t, a, d));      // 平滑出现

const memo = {};
function at(key, id, nth = 0) { // 某个词在配音里开始的时刻（秒）；nth 取第几次出现
  const mk = key + '@' + id + '#' + nth;
  if (mk in memo) return memo[mk];
  const k = key.replace(/[^0-9a-zA-Z一-鿿]/g, '').toLowerCase();
  const l = L(id);
  const s = l.chars.map(c => c.c.toLowerCase()).join('');
  let i = -1; for (let n = 0; n <= nth; n++) i = s.indexOf(k, i + 1);
  if (i < 0) throw new Error('at(): 「' + key + '」不在 ' + id + ' 的配音里');
  return (memo[mk] = l.chars[i].s);
}
function atEnd(key, id) { const k = key.replace(/[^0-9a-zA-Z一-鿿]/g, '').toLowerCase(); const l = L(id); const s = l.chars.map(c => c.c.toLowerCase()).join(''); const i = s.indexOf(k); if (i < 0) throw new Error('atEnd(): ' + key); return l.chars[i + k.length - 1].e; }
const L = id => { const l = D.lines.find(l => l.id === id); if (!l) throw new Error('没有这句：' + id); return l; };

function font(o) { return `${o.w || 700} ${o.s || 40}px ${o.f || F.cn}`; }
function T(str, x, y, o = {}) {
  ctx.save();
  ctx.font = font(o);
  ctx.fillStyle = o.c || C.text;
  ctx.textAlign = o.a || 'left';
  ctx.textBaseline = o.b || 'alphabetic';
  if (o.al !== undefined) ctx.globalAlpha *= clamp(o.al);
  if (o.ls) ctx.letterSpacing = o.ls + 'px';
  if (o.glow) { ctx.shadowColor = o.glow; ctx.shadowBlur = o.gb || 30; }
  if (o.stroke) { ctx.strokeStyle = o.stroke; ctx.lineWidth = o.lw || 2; ctx.strokeText(str, x, y); }
  if (!o.strokeOnly) ctx.fillText(str, x, y);
  const m = ctx.measureText(str).width;
  ctx.restore();
  return m;
}
function MW(str, o = {}) { ctx.save(); ctx.font = font(o); if (o.ls) ctx.letterSpacing = o.ls + 'px'; const m = ctx.measureText(str).width; ctx.restore(); return m; }
// 一行里混排多段颜色：[['文字', {c}], ...]，返回总宽
function TT(parts, x, y, base = {}) {
  let w = 0; for (const [s, o] of parts) w += MW(s, { ...base, ...o });
  let cx = base.a === 'center' ? x - w / 2 : base.a === 'right' ? x - w : x;
  for (const [s, o] of parts) cx += T(s, cx, y, { ...base, ...o, a: 'left' });
  return w;
}
function rr(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function box(x, y, w, h, o = {}) { // 圆角卡片：白底 + 细边 + 轻阴影
  ctx.save();
  if (o.al !== undefined) ctx.globalAlpha *= clamp(o.al);
  if (o.shadow !== false) { ctx.shadowColor = C.shadow; ctx.shadowBlur = o.sb ?? 24; ctx.shadowOffsetY = 6; }
  rr(x, y, w, h, o.r ?? 22); ctx.fillStyle = o.fill || C.panel; ctx.fill();
  ctx.shadowColor = 'transparent';
  if (o.line !== false) { ctx.strokeStyle = o.line || C.stroke; ctx.lineWidth = o.lw || 2; if (o.dash) ctx.setLineDash(o.dash); ctx.stroke(); }
  ctx.restore();
}
function chip(str, x, y, o = {}) { // 圆角小胶囊，返回宽
  const s = o.s || 30, px = o.px ?? 18, h = o.h || s + 22;
  const w = MW(str, { s, w: o.w || 800, f: o.f }) + px * 2;
  const x0 = o.a === 'center' ? x - w / 2 : o.a === 'right' ? x - w : x;
  ctx.save(); if (o.al !== undefined) ctx.globalAlpha *= clamp(o.al);
  if (o.k !== undefined) { ctx.translate(x0 + w / 2, y); ctx.scale(o.k, o.k); ctx.translate(-(x0 + w / 2), -y); }
  rr(x0, y - h / 2, w, h, o.r ?? h / 2);
  if (o.fill !== false) { ctx.fillStyle = o.bg || C.acc; ctx.fill(); }
  if (o.line) { ctx.strokeStyle = o.line; ctx.lineWidth = o.lw || 2.5; ctx.stroke(); }
  T(str, x0 + w / 2, y + 1, { s, w: o.w || 800, f: o.f, c: o.fg || C.accInk, a: 'center', b: 'middle' });
  ctx.restore();
  return w;
}
function tag(str, x, y, o = {}) { // 等宽小标签
  return chip(str, x, y, { f: F.mono, s: o.s || 26, w: o.w || 700, px: o.px ?? 14, r: o.r ?? 8, ...o });
}
function arrow(x1, y1, x2, y2, color, lw = 3, p = 1, o = {}) {
  const x = lerp(x1, x2, p), y = lerp(y1, y2, p);
  ctx.save(); ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round';
  if (o.al !== undefined) ctx.globalAlpha *= clamp(o.al);
  if (o.dash) ctx.setLineDash(o.dash);
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x, y); ctx.stroke(); ctx.setLineDash([]);
  if (p > 0.2 && o.head !== false) {
    const a = Math.atan2(y2 - y1, x2 - x1), s = o.hs || 10 + lw * 2;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - s * Math.cos(a - 0.45), y - s * Math.sin(a - 0.45));
    ctx.lineTo(x - s * Math.cos(a + 0.45), y - s * Math.sin(a + 0.45)); ctx.closePath(); ctx.fill();
  }
  ctx.restore();
}
function mark(ok, x, y, r = 22, al = 1) { // 圆圈里的 ✓ / ✗
  ctx.save(); ctx.globalAlpha *= clamp(al);
  const col = ok ? C.ok : C.bad;
  ctx.beginPath(); ctx.arc(x, y, r, 0, 7);
  if (ok) { ctx.fillStyle = col; ctx.fill(); } else { ctx.strokeStyle = col; ctx.lineWidth = 3.5; ctx.stroke(); }
  ctx.strokeStyle = ok ? '#fff' : col; ctx.lineWidth = 4; ctx.lineCap = 'round'; ctx.beginPath();
  if (ok) { ctx.moveTo(x - r * 0.42, y + r * 0.02); ctx.lineTo(x - r * 0.1, y + r * 0.34); ctx.lineTo(x + r * 0.45, y - r * 0.3); }
  else { const k = r * 0.36; ctx.moveTo(x - k, y - k); ctx.lineTo(x + k, y + k); ctx.moveTo(x + k, y - k); ctx.lineTo(x - k, y + k); }
  ctx.stroke(); ctx.restore();
}
function strike(x, y, w, p, color = C.bad, lw = 6) { if (p <= 0) return; ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w * clamp(p), y); ctx.stroke(); ctx.restore(); }
function cue(t, type, gain = 1) { CUES.push({ t: +Math.max(0, t).toFixed(3), type, gain }); }

// ---------- 图片 ----------
const IMGC = new Map();
function loadImg(url) {
  if (IMGC.has(url)) return IMGC.get(url);
  const p = new Promise(res => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = url; });
  IMGC.set(url, p);
  if (IMGC.size > 60) { const k = IMGC.keys().next().value; IMGC.delete(k); }
  return p;
}
// 等比铺满（cover）画一张图；o.zoom、o.dx、o.dy 做轻微运镜（表示视频里不同的帧）
function img(im, x, y, w, h, o = {}) {
  if (!im) return;
  const z = o.zoom || 1, iw = im.width, ih = im.height;
  let sw = iw, sh = ih; const ar = w / h;
  if (sw / sh > ar) sw = sh * ar; else sh = sw / ar;
  sw /= z; sh /= z;
  const sx = clamp((iw - sw) / 2 + (o.dx || 0) * iw, 0, iw - sw), sy = clamp((ih - sh) / 2 + (o.dy || 0) * ih, 0, ih - sh);
  ctx.save(); if (o.al !== undefined) ctx.globalAlpha *= clamp(o.al);
  if (o.r) { rr(x, y, w, h, o.r); ctx.clip(); }
  ctx.drawImage(im, sx, sy, sw, sh, x, y, w, h);
  ctx.restore();
}
// 块状灰度噪声（和小红书配图同款），sigma=1 全是噪声，0 没有噪声
function noise(x, y, w, h, sigma = 1, seed = 0, o = {}) {
  if (sigma <= 0.001) return;
  const n = NOISE[((seed % NOISE.length) + NOISE.length) % NOISE.length];
  ctx.save(); ctx.globalAlpha *= clamp(sigma);
  if (o.r) { rr(x, y, w, h, o.r); ctx.clip(); }
  ctx.imageSmoothingEnabled = false; ctx.drawImage(n, 0, 0, o.cells || 8, Math.round((o.cells || 8) * h / w) || 1, x, y, w, h); ctx.imageSmoothingEnabled = true;
  ctx.restore();
}
// 一叠帧（表示视频）：从后往前画 n 张，每张偏移 (dx, dy)
function stack(n, x, y, w, h, drawOne, o = {}) {
  const dx = o.dx ?? 10, dy = o.dy ?? -10;
  for (let i = n - 1; i >= 0; i--) {
    const fx = x + i * dx, fy = y + i * dy;
    ctx.save(); ctx.shadowColor = C.shadow; ctx.shadowBlur = 8; rr(fx, fy, w, h, o.r ?? 6); ctx.fillStyle = C.panel; ctx.fill(); ctx.restore();
    drawOne(i, fx, fy, w, h);
    rr(fx, fy, w, h, o.r ?? 6); ctx.strokeStyle = o.line || C.faint; ctx.lineWidth = 2; ctx.stroke();
  }
}

// ---------- 摄像头 ----------
// 取景永远是整幅画高（头 + 肩），只左右跟脸；窗口大小、位置变化不改变取景松紧
function faceX(f) { const a = D.face[clamp(f, 0, D.face.length - 1)]; return a[0]; }
function camState(name, f) {
  const S = D.src;
  if (name === 'card') return { dst: { ...CARD }, src: { x: 0, y: 0, w: S.w, h: S.h }, r: 28 };
  if (name === 'bubble') {
    const side = S.h, sx = clamp(faceX(f) - side / 2, 0, S.w - side);
    return { dst: { x: BUB.cx - BUB.r, y: BUB.cy - BUB.r, w: 2 * BUB.r, h: 2 * BUB.r }, src: { x: sx, y: 0, w: side, h: side }, r: BUB.r };
  }
  return null;
}
function camAt(t, f) {
  let i = 0;
  while (i + 1 < CAMS.length && CAMS[i + 1][0] <= t) i++;
  const [t0, name, dur] = CAMS[i];
  const cur = camState(name, f);
  if (i === 0 || !dur) return cur;
  const prev = camState(CAMS[i - 1][1], f);
  if (!prev || !cur) return cur;
  const p = E.io(pr(t, t0, dur));
  if (p >= 1) return cur;
  const mix = (a, b) => ({ x: lerp(a.x, b.x, p), y: lerp(a.y, b.y, p), w: lerp(a.w, b.w, p), h: lerp(a.h, b.h, p) });
  // 取景从 16:9 收到正方形时保持整幅画高，只收左右，不会放大到脸上
  return { dst: mix(prev.dst, cur.dst), src: mix(prev.src, cur.src), r: lerp(prev.r, cur.r, p) };
}
function drawCam(st, im) {
  if (!st || !im || st.dst.w < 2) return;
  const { dst, src, r } = st;
  ctx.save();
  ctx.save(); ctx.shadowColor = 'rgba(0,0,0,0.25)'; ctx.shadowBlur = 36; ctx.shadowOffsetY = 10;
  rr(dst.x, dst.y, dst.w, dst.h, r); ctx.fillStyle = '#000'; ctx.fill(); ctx.restore();
  rr(dst.x, dst.y, dst.w, dst.h, r); ctx.clip();
  ctx.drawImage(im, src.x, src.y, src.w, src.h, dst.x, dst.y, dst.w, dst.h);
  ctx.restore();
  const v = D.env[clamp(F_NOW, 0, D.env.length - 1)] || 0;
  ctx.save(); rr(dst.x, dst.y, dst.w, dst.h, r); ctx.strokeStyle = C.acc; ctx.lineWidth = 4 + v * 2.5; ctx.shadowColor = C.acc; ctx.shadowBlur = 4 + v * 18; ctx.stroke(); ctx.restore();
}

// ---------- 背景、标题、进度条、字幕 ----------
function bg() {
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = C.grid;
  for (let y = 24; y < H; y += 48) for (let x = 24; x < W; x += 48) { ctx.beginPath(); ctx.arc(x, y, 1.6, 0, 7); ctx.fill(); }
}
// 每段顶部标题：小标签 + 「黑字结论，蓝字关键词」；放不下时蓝字换行
function headline(t, a, b, small, big, accent, o = {}) {
  const al = win(t, a - 0.07, b + 0.18, 0.22, 0.22), p = E.o3(pr(t, a - 0.07, 0.4));
  if (al <= 0) return;
  ctx.save(); ctx.globalAlpha *= al;
  const s = o.s || 76, y = LAYOUT.titleY + (1 - p) * 26;
  if (small) T(small, LAYOUT.x0 + 4, LAYOUT.smallY, { f: F.mono, s: 30, w: 700, c: C.acc });
  const w1 = MW(big, { s, w: 900 }), w2 = accent ? MW(accent, { s, w: 900 }) : 0;
  T(big, LAYOUT.x0, y, { s, w: 900 });
  if (accent) {
    if (w1 + w2 <= LAYOUT.x1 - LAYOUT.x0) T(accent, LAYOUT.x0 + w1, y, { s, w: 900, c: C.acc });
    else T(accent, LAYOUT.x0, y + s * 1.18, { s, w: 900, c: C.acc });
  }
  ctx.restore();
}
function headlineH(big, accent, s = 76) { const w1 = MW(big, { s, w: 900 }), w2 = accent ? MW(accent, { s, w: 900 }) : 0; return w1 + w2 <= LAYOUT.x1 - LAYOUT.x0 ? 1 : 2; }
function tracker(t) {
  if (!TRACKER) return;
  const t0 = TRACKER.from(), t1 = TRACKER.to();
  if (t < t0 - 0.1 || t > t1 + 0.3) return;
  const fade = 1 - pr(t, t1, 0.3);
  const cur = TRACKER.active(t) || [], done = TRACKER.done ? TRACKER.done(t) : [];
  const n = TRACKER.items.length, g = 10, w = (LAYOUT.x1 - LAYOUT.x0 - g * (n - 1)) / n, y = LAYOUT.trackerY;
  for (let i = 0; i < n; i++) {
    const p = E.ob(pr(t, t0 + i * 0.08, 0.35)); if (p <= 0) continue;
    const x = LAYOUT.x0 + i * (w + g), on = cur.includes(i), past = done.includes(i);
    ctx.save(); ctx.globalAlpha *= clamp(p) * fade;
    ctx.translate(x + w / 2, y); ctx.scale(lerp(0.6, 1, p), lerp(0.6, 1, p));
    rr(-w / 2, -32, w, 64, 14);
    if (on) { ctx.fillStyle = C.acc; ctx.fill(); }
    else { ctx.fillStyle = C.panel; ctx.fill(); ctx.strokeStyle = past ? C.acc : C.stroke; ctx.lineWidth = 2; ctx.stroke(); }
    T('0' + (i + 1), -w / 2 + 14, 2, { f: F.mono, s: 22, w: 800, c: on ? C.accInk : past ? C.acc : C.dim, b: 'middle' });
    T(TRACKER.items[i], -w / 2 + 50, 2, { s: 33, w: 900, c: on ? C.accInk : C.text, al: on || past ? 1 : 0.6, b: 'middle' });
    ctx.restore();
  }
}
function caption(t) {
  const c = D.caps.find(c => t >= c.start - 0.06 && t < c.end);
  if (!c) return;
  const s = 50, o = { s, w: 800 };
  const ws = [...c.text].map(ch => MW(ch, o));
  const tw = ws.reduce((a, b) => a + b, 0);
  const x0 = W / 2 - tw / 2, y = LAYOUT.capY;
  ctx.save(); ctx.globalAlpha = clamp((t - c.start + 0.06) / 0.08);
  rr(x0 - 26, y - s * 0.78, tw + 52, s * 1.56, 16); ctx.fillStyle = C.capBg; ctx.fill();
  let x = x0;
  [...c.text].forEach((ch, i) => {
    const k = c.chars[i];
    const spoken = k && t >= k.s, curr = k && t >= k.s && t < Math.max(k.e, k.s + 0.12);
    T(ch, x, y + 2, { ...o, b: 'middle', c: curr ? C.hi : spoken ? '#FFFFFF' : 'rgba(255,255,255,0.42)', glow: curr ? C.hi : null, gb: 18 });
    x += ws[i];
  });
  ctx.restore();
}

// ---------- 场景 ----------
function SCENE(id, fn, opt = {}) { SCENES.push({ id, fn, opt }); }
function sceneWindows() { // 每个场景从自己那句开始前 0.3 秒，到下一个场景开始前 0.25 秒；最后一个持续到片尾
  const end = D.nFrames / FPS;
  return SCENES.map((s, i) => {
    const a = L(s.id).start, nx = i + 1 < SCENES.length ? L(SCENES[i + 1].id).start - 0.25 : end + 1;
    return { ...s, a, b: nx };
  });
}
let WINS = [];

function plan() {
  CAMS = [];
  const open = CFG.camera_open || 'card', openUntil = CFG.camera_open_until;
  CAMS.push([0, open, 0]);
  if (open === 'card') CAMS.push([openUntil ? L(openUntil).end + 0.1 : 3, 'bubble', 0.8]);
  CUES = [];
  WINS.forEach((w, i) => { if (i > 0) cue(w.a - 0.22, 'whoosh', 0.28); });
  if (PLAN) PLAN();
  CUES.sort((a, b) => a.t - b.t);
}

// ---------- 主渲染 ----------
const pad5 = n => String(n).padStart(5, '0');
const personUrl = i => `/work/frames/person/${pad5(i + 1)}.jpg`;
async function renderFrame(f) {
  const t = f / FPS; T_NOW = t; F_NOW = f;
  const pf = clamp(f, 0, D.nPerson - 1);
  const st = camAt(t, pf);
  const extra = (window.PRELOAD ? window.PRELOAD(t) : []).map(loadImg);
  const [im, ...ex] = await Promise.all([loadImg(personUrl(pf)), ...extra]);
  window.EXTRA = ex;
  loadImg(personUrl(clamp(pf + 1, 0, D.nPerson - 1)));
  ctx.save();
  bg();
  for (const w of WINS) {
    if (t < w.a - 0.4 || t > w.b + 0.3) continue;
    const al = win(t, w.a - 0.3, w.b + 0.18, 0.24, 0.22);
    if (al <= 0) continue;
    ctx.save(); ctx.globalAlpha = al; w.fn(t, w.a, w.b, al); ctx.restore();
  }
  tracker(t);
  if (window.OVERLAY) window.OVERLAY(t);
  drawCam(st, im);
  caption(t);
  ctx.restore();
  return true;
}

async function init() {
  D = await (await fetch('/work/data.json?' + Date.now())).json();
  CFG = D.cfg || {};
  C = THEMES[(Q.get('theme') || CFG.theme || 'light')];
  const txt = D.caps.map(c => c.text).join('') + (window.FONT_TEXT || '') + 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789×→≈✓✗·—…%²′';
  const faces = ['900 100px "Noto Sans SC Variable"', '800 100px "Noto Sans SC Variable"', '700 100px "Noto Sans SC Variable"', '600 100px "Noto Sans SC Variable"', '500 100px "Noto Sans SC Variable"',
    '400 100px "Archivo Black"', '800 40px "JetBrains Mono Variable"', '700 40px "JetBrains Mono Variable"', '600 40px "JetBrains Mono Variable"', '500 40px "JetBrains Mono Variable"', '700 100px "Noto Serif SC Variable"'];
  await Promise.all(faces.map(fc => document.fonts.load(fc, txt)));
  for (const [k, u] of Object.entries(ASSETS)) IM[k] = await loadImg(u);
  for (let k = 0; k < 8; k++) { // 块状灰度噪声
    const c = document.createElement('canvas'); c.width = 32; c.height = 32; const x = c.getContext('2d'); const r = rng(77 + k * 13);
    const id = x.createImageData(32, 32);
    for (let i = 0; i < id.data.length; i += 4) { const v = 70 + Math.floor(r() * 170); id.data[i] = v; id.data[i + 1] = v; id.data[i + 2] = v; id.data[i + 3] = 255; }
    x.putImageData(id, 0, 0); NOISE.push(c);
  }
  if (window.SETUP) await window.SETUP();
  WINS = sceneWindows();
  plan();
  window.CUES = CUES;
  window.META = { W, H, FPS, nFrames: D.nFrames, version: VER };
  return true;
}
window.renderFrame = renderFrame;
window.ready = new Promise(res => window.addEventListener('load', () => res(init())));
