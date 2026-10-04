// scenes.js — 拆解 H3：视频生成的五个零件。
// 每句口播一个画面，版式照图文版配图：白卡片、黑字结论 + 蓝字关键词、Wan / H3 对照、✓ ✗ 判断；示意图统一用一张 demo 图。
ASSETS = { cat: '/assets/demo.png' };  // 示意图（init 会拷 config 的 me.demo_image）
const X0 = 48, X1 = 1032, CW = X1 - X0;
const PARTS = ['VAE', '主干', '文字', '参考', '采样'];
const h3clip = i => `/assets/h3clip/${String((i % 304) + 1).padStart(4, '0')}.jpg`;
window.PRELOAD = t => { const a = L('intro').start - 0.6, b = L('p01').start + 0.3; return t >= a && t < b ? [h3clip(Math.floor((t - a) * 30))] : []; };
window.FONT_TEXT = 'Context-IR Regenerate-2K H3-Base umT5 Qwen3-VL CFG shift SD3 Transformer ①②③④⑤ σ';

TRACKER = {
  items: PARTS,
  from: () => at('五个零件', 'p03'),
  to: () => L('p11').start - 0.35,
  active: t => t < L('p04').start - 0.2 ? [] : t < L('p07').start - 0.2 ? [0] : t < L('p08').start - 0.2 ? [1] : t < L('p09').start - 0.2 ? [2] : t < L('p10').start - 0.2 ? [3] : [4],
  done: t => { const a = TRACKER.active(t); return a.length ? [...Array(a[0]).keys()] : []; },
};

// ---------- 本专题小部件 ----------
function catF(i, x, y, w, h, o = {}) { // 猫图当「一帧」：每帧轻微平移缩放，看得出是视频里不同的帧
  img(IM.cat, x, y, w, h, { zoom: 1.08 + 0.03 * Math.sin(i * 0.8), dx: 0.025 * Math.sin(i * 1.3), dy: 0.02 * Math.cos(i * 0.9), r: o.r ?? 6, al: o.al });
  if (o.sigma) noise(x, y, w, h, o.sigma, i + (o.seed || 0), { r: o.r ?? 6, cells: o.cells || 8 });
}
function frameBox(x, y, w, h, col = C.faint, lw = 2, r = 6) { rr(x, y, w, h, r); ctx.strokeStyle = col; ctx.lineWidth = lw; ctx.stroke(); }
function token(x, y, s, fill, line) { rr(x, y, s, s, Math.max(3, s * 0.18)); ctx.fillStyle = fill; ctx.fill(); if (line) { ctx.strokeStyle = line; ctx.lineWidth = 2; ctx.stroke(); } }
function lock(x, y, s = 26, col = C.dim) { // 小锁：闭源
  ctx.save(); ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = s * 0.14;
  ctx.beginPath(); ctx.arc(x, y - s * 0.12, s * 0.28, Math.PI, 0); ctx.stroke();
  rr(x - s * 0.42, y - s * 0.12, s * 0.84, s * 0.62, 4); ctx.fill(); ctx.restore();
}
function verdict(ok, str, x, y, p) { if (p <= 0) return; mark(ok, x, y, 24, p); T(str, x + 36, y + 10, { s: 30, w: 800, c: ok ? C.ok : C.bad, al: p }); }
function vcol(ok, str, cx, y, p) { if (p <= 0) return; ctx.save(); ctx.translate(cx, y); const k = lerp(0.6, 1, clamp(p)); ctx.scale(k, k); mark(ok, 0, 0, 26, p); ctx.restore(); T(str, cx, y + 62, { s: 29, w: 800, c: ok ? C.ok : C.bad, a: 'center', al: p }); }
const cnt = (t, a, d, v) => v * E.o3(pr(t, a, d));

// ---------- hook：结论先行 ----------
SCENE('hook', (t, a, b) => {
  const tg = at('生图', 'hook'), tt = at('时间轴', 'hook'), tp = at('配方没变', 'hook'), tz = at('几个零件', 'hook');
  const pt = ease(t, 0.05, 0.5);
  TT([['拆解 ', {}], ['H3', { c: C.acc, f: F.en, w: 400 }], ['  视频生成的五个零件', { s: 48, c: C.dim }]], X0, 785 + (1 - pt) * 20, { s: 64, w: 900, al: pt });
  // 生图 = 1 帧
  const pg = pop(t, Math.min(tg - 0.1, 0.35)), y0 = 850, s = 230;
  if (pg > 0) {
    ctx.save(); ctx.globalAlpha *= clamp(pg); box(X0, y0, s, s, { r: 14, sb: 18 }); catF(0, X0 + 8, y0 + 8, s - 16, s - 16, { r: 10 });
    T('生图 = 1 帧', X0 + s / 2, y0 + s + 52, { s: 36, w: 800, a: 'center' }); ctx.restore();
  }
  // + 时间轴：一叠帧沿 t 排开
  const pf = E.io(pr(t, tt - 0.1, 0.8));
  if (pf > 0) {
    const n = 6;
    for (let i = n - 1; i >= 0; i--) {
      const x = 330 + i * 84 * pf, y = y0 + 20 - i * 6 * pf, sz = 190;
      ctx.save(); ctx.globalAlpha *= clamp(pf * 2) * (1 - i * 0.07);
      box(x, y, sz, sz, { r: 12, sb: 10 }); catF(i + 1, x + 6, y + 6, sz - 12, sz - 12, { r: 8 }); ctx.restore();
    }
    arrow(330, y0 + 240, 330 + 660 * pf, y0 + 240, C.acc, 5, 1);
    T('t', 1002, y0 + 252, { f: F.mono, s: 44, w: 800, c: C.acc, al: pf });
    T('视频 = 很多帧', 330 + 300, y0 + s + 52, { s: 36, w: 800, a: 'center', al: pf });
  }
  // 配方没变 / 改几个零件
  const pp = ease(t, tp - 0.1, 0.35);
  if (pp > 0) {
    const ys = 1222; let x = X0;
    ['噪声', '去噪 N 步', 'VAE 解码'].forEach((s2, i) => { const w = chip(s2, x, ys, { s: 30, bg: C.panel, fg: C.text, line: C.stroke, al: clamp(pp * 2 - i * 0.4) }); if (i < 2) arrow(x + w + 6, ys, x + w + 30, ys, C.faint, 3, 1, { al: pp }); x += w + 36; });
    mark(true, x + 26, ys, 22, pp); T('配方没变', x + 58, ys + 11, { s: 32, w: 900, c: C.acc, al: pp });
  }
  const pz = pop(t, tz - 0.05, 0.35);
  if (pz > 0) PARTS.forEach((nm, i) => chip(nm, X0 + i * 120 + 470, 1292, { s: 26, h: 44, px: 14, bg: C.acc2, k: lerp(0.5, 1, clamp(pop(t, tz + i * 0.07, 0.3))), al: clamp(pz) }));
});

// ---------- intro：拿 H3 入门，Wan 当对照 ----------
SCENE('intro', (t, a, b) => {
  headline(t, a, b, '为什么是这两个', '拿 H3 入门，', 'Wan 当对照');
  const tm = at('minimax', 'intro'), tr = at('技术报告', 'intro'), tq = at('全公开', 'intro'), tw = at('阿里万相', 'intro'), td = at('对照', 'intro');
  const y0 = 470, w = 470, h = 760;
  const ph = pop(t, tm - 0.1, 0.4);
  if (ph > 0) {
    ctx.save(); ctx.globalAlpha *= clamp(ph); box(X0, y0, w, h, { line: C.acc, lw: 3 });
    T('H3', X0 + 32, y0 + 96, { f: F.en, s: 84, w: 400, c: C.acc }); T('MiniMax · 新开源', X0 + 34, y0 + 146, { s: 32, w: 700, c: C.dim });
    const clip = window.EXTRA && window.EXTRA[0]; if (clip) img(clip, X0 + 24, y0 + 180, w - 48, (w - 48) * 9 / 16, { r: 12 });
    T('官方样例', X0 + w - 36, y0 + 180 + (w - 48) * 9 / 16 + 36, { f: F.mono, s: 22, w: 600, c: C.dim, a: 'right' });
    const pr2 = ease(t, tr, 0.3);
    T('技术报告', X0 + 32, y0 + 520, { s: 38, w: 800, al: pr2 }); verdict(false, '还没发', X0 + 230, y0 + 508, pr2);
    T('权重', X0 + 32, y0 + 610, { s: 38, w: 800, al: pr2 }); verdict(true, '开源', X0 + 230, y0 + 598, pr2);
    ctx.restore();
  }
  const pw = pop(t, tq - 0.25, 0.4);
  if (pw > 0) {
    const x = X1 - w; ctx.save(); ctx.globalAlpha *= clamp(pw); box(x, y0, w, h);
    T('Wan', x + 32, y0 + 96, { f: F.en, s: 84, w: 400 }); T('阿里 · 全公开', x + 34, y0 + 146, { s: 32, w: 700, c: C.dim });
    const pr3 = ease(t, tq, 0.3);
    [['论文', '有'], ['代码', '有'], ['训练细节', '有']].forEach((r, i) => { T(r[0], x + 32, y0 + 270 + i * 90, { s: 38, w: 800, al: pr3 }); verdict(true, r[1], x + 230, y0 + 258 + i * 90, ease(t, tq + i * 0.12, 0.3)); });
    const pd = pop(t, td - 0.05, 0.35); if (pd > 0) chip('当对照', x + w / 2, y0 + 620, { s: 40, h: 76, px: 34, k: lerp(0.6, 1, clamp(pd)), al: clamp(pd) });
    ctx.restore();
  }
});

// ---------- 01 H3 分三段 ----------
SCENE('p01', (t, a, b) => {
  headline(t, a, b, '01 · H3 分三段', 'H3 分三段，', '开源的只有中间');
  const t1 = at('闭源的', 'p01'), tk = at('分镜', 'p01'), t2 = at('开源的33b', 'p01'), t7 = at('768p', 'p01'), t3 = at('重画', 'p01'), te = atEnd('2k', 'p01');
  const dim = ease(t, te + 0.25, 0.4);
  const rows = [
    { at: t1, n: '①', k: '理解', open: false, name: 'Context-IR', d1: '读需求和素材', d2: '文字、图、视频、音频都行', out: '约 4K token 的分镜', tOut: tk },
    { at: t2, n: '②', k: '生成', open: true, name: 'H3-Base · 33B', d1: '按分镜出 768p', d2: '视频 + 音频一起出', out: '768p 视频', tOut: t7 },
    { at: t3, n: '③', k: '重画', open: false, name: 'Regenerate-2K', d1: '768p 重画成 2K', d2: '再看一遍原分镜', out: '2K 视频', tOut: te - 0.2 },
  ];
  const y0 = 490, rh = 236, g = 34;
  rows.forEach((r, i) => {
    const p = pop(t, r.at - 0.1, 0.4); if (p <= 0) return;
    const y = y0 + i * (rh + g), al = clamp(p) * (r.open ? 1 : 1 - 0.5 * dim);
    ctx.save(); ctx.globalAlpha *= al; ctx.translate(0, (1 - clamp(p)) * 30);
    box(X0, y, CW, rh, { fill: r.open && dim > 0 ? C.accSoft : C.panel, line: r.open ? C.acc : C.stroke, lw: r.open ? 3 : 2 });
    T(r.n, X0 + 30, y + 66, { s: 50, w: 800, c: r.open ? C.acc : C.text });
    T(r.k, X0 + 96, y + 64, { s: 46, w: 900, c: r.open ? C.acc : C.text });
    if (r.open) chip('开源', X0 + 210, y + 48, { s: 28, h: 46 }); else { lock(X0 + 228, y + 50, 30); T('闭源', X0 + 252, y + 61, { s: 30, w: 800, c: C.dim }); }
    T(r.name, X0 + 30, y + 130, { f: F.mono, s: 36, w: 700 });
    T(r.d1, X0 + 30, y + 182, { s: 32, w: 700, c: C.dim }); T(r.d2, X0 + 30, y + 222, { s: 28, w: 600, c: C.dim });
    const po = pop(t, r.tOut - 0.05, 0.35);
    if (po > 0) { arrow(X0 + 560, y + rh / 2, X0 + 610, y + rh / 2, C.faint, 4, 1, { al: po }); chip(r.out, X0 + 760, y + rh / 2, { s: 32, h: 64, bg: r.open ? C.acc : C.panel2, fg: r.open ? C.accInk : C.text, line: r.open ? null : C.stroke, a: 'center', k: lerp(0.6, 1, clamp(po)), al: clamp(po) }); }
    ctx.restore();
    if (i < 2 && pop(t, rows[i + 1].at - 0.1) > 0) arrow(X0 + 60, y + rh + 4, X0 + 60, y + rh + g - 4, C.faint, 4, 1, { hs: 12 });
  });
});

// ---------- 02 输入输出 ----------
SCENE('p02', (t, a, b) => {
  headline(t, a, b, '02 · 输入输出', '生视频只比生图', '多一维 T');
  const tn = at('一块噪声', 'p02'), td = at('去噪n步', 'p02'), tv = at('vae解码', 'p02'), tt = at('多一维', 'p02'), tf = at('开始前', 'p02');
  const cw = 470, xs = [X0, X1 - cw], hl = E.o3(pr(t, tt, 0.3)), pulse = hl * (1 + 0.5 * Math.max(0, Math.sin((t - tt) * 8)) * (1 - pr(t, tt + 1.2, 0.4)));
  const tC = (x, y, parts, o) => TT(parts.map(s => s === 'T′' || s === 'T' ? [s, { c: C.acc, s: (o.s || 34) * (1 + 0.15 * pulse) }] : [s, {}]), x, y, o);
  const ph = ease(t, a, 0.4);
  ['生图', '生视频'].forEach((h2, i) => T(h2, xs[i] + cw / 2, 490, { s: 44, w: 900, a: 'center', al: ph, c: i ? C.acc : C.text }));
  const rows = [{ y: 520, h: 262, at: tn, k: '起点' }, { y: 812, h: 156, at: td, k: '去噪' }, { y: 998, h: 280, at: tv, k: '输出' }];
  rows.forEach((r, ri) => {
    const p = pop(t, r.at - 0.1, 0.4); if (p <= 0) return;
    for (let i = 0; i < 2; i++) {
      const x = xs[i]; ctx.save(); ctx.globalAlpha *= clamp(p); ctx.translate(0, (1 - clamp(p)) * 24);
      box(x, r.y, cw, r.h, { r: 18, sb: 14 });
      T(r.k, x + 22, r.y + 40, { f: F.mono, s: 24, w: 700, c: C.dim });
      if (ri === 0) {
        T(i ? '一叠噪声' : '一张噪声', x + 24, r.y + 110, { s: 38, w: 900, c: i ? C.acc : C.text });
        if (i) tC(x + 24, r.y + 196, ['C×', 'T′', '×H′×W′'], { f: F.mono, s: 36, w: 800 }); else T('C×H′×W′', x + 24, r.y + 196, { f: F.mono, s: 36, w: 800 });
        if (i) stack(4, x + 300, r.y + 120, 110, 110, (k, fx, fy, fw, fh) => noise(fx, fy, fw, fh, 1, k + 3, { r: 6, cells: 6 }), { dx: 10, dy: -12 });
        else noise(x + 320, r.y + 90, 120, 120, 1, 1, { r: 6, cells: 6 });
      } else if (ri === 1) {
        T('Transformer × N 步', x + 24, r.y + 88, { s: 34, w: 800 });
        T(i ? '所有帧一起' : '4,096 个 token', x + 24, r.y + 134, { s: 28, w: 800, c: i ? C.acc : C.dim });
      } else {
        T('VAE 解码 →', x + 24, r.y + 100, { s: 32, w: 800 });
        T(i ? '一段视频' : '一张图', x + 24, r.y + 152, { s: 38, w: 900, c: i ? C.acc : C.text });
        if (i) tC(x + 24, r.y + 240, ['T', '×H×W×3'], { f: F.mono, s: 36, w: 800 }); else T('H×W×3', x + 24, r.y + 240, { f: F.mono, s: 36, w: 800 });
        if (i) stack(4, x + 300, r.y + 120, 110, 110, (k, fx, fy, fw, fh) => catF(k, fx, fy, fw, fh)); else catF(0, x + 320, r.y + 90, 120, 120);
      }
      ctx.restore();
      if (ri > 0) arrow(x + cw / 2, rows[ri - 1].y + rows[ri - 1].h + 6, x + cw / 2, r.y - 6, C.faint, 4, 1, { al: p, hs: 12 });
    }
  });
  const pf = pop(t, tf - 0.05, 0.35);
  if (pf > 0) chip('帧数 T 开始前就定好', W / 2, 1322, { s: 30, h: 56, a: 'center', k: lerp(0.6, 1, clamp(pf)), al: clamp(pf) });
});

// ---------- 03 五个零件：Wan / H3 对照表 ----------
SCENE('p03', (t, a, b) => {
  headline(t, a, b, '03 · 架构对照', '五个零件，', 'Wan 和 H3 各怎么选');
  const rows = [['VAE', '压 8×', '压 16×'], ['主干', '两个 14B 专家', '33B 单流'], ['文字', 'umT5 · 交叉注意力', 'Qwen3-VL · 拼进序列'], ['参考', '首帧拼到通道上', '全部拼成一条序列'], ['采样', '40 步 · 每步算 2 次', 'N 步 · 每步算 1 次']];
  const keys = ['vae', '主干', '文字', '参考', '采样'], th = at('各选各的', 'p03'), hl = ease(t, th - 0.1, 0.4);
  const y0 = 560, rh = 132, xW = 290, xH = 672, ph = ease(t, a, 0.4);
  if (hl > 0) box(xH - 24, y0 - 96, X1 - xH + 16, rows.length * rh + 108, { fill: C.accSoft, line: C.acc, lw: 3, al: hl, shadow: false });
  T('Wan', xW, y0 - 34, { f: F.en, s: 44, w: 400, al: ph }); T('H3', xH, y0 - 34, { f: F.en, s: 44, w: 400, c: C.acc, al: ph });
  rows.forEach((r, i) => {
    const p = pop(t, at(keys[i], 'p03') - 0.08, 0.35); if (p <= 0) return;
    const y = y0 + i * rh;
    ctx.save(); ctx.globalAlpha *= clamp(p); ctx.translate((1 - clamp(p)) * -30, 0);
    if (i) { ctx.fillStyle = C.stroke; ctx.fillRect(X0, y, CW, 2); }
    T('0' + (i + 1), X0 + 4, y + 78, { f: F.mono, s: 26, w: 800, c: C.acc });
    T(r[0], X0 + 52, y + 80, { s: 44, w: 900 });
    T(r[1], xW, y + 78, { s: 30, w: 700, c: C.dim });
    T(r[2], xH, y + 78, { s: 30, w: 900, c: C.acc });
    ctx.restore();
  });
});

// ---------- 04 3D 因果 VAE ----------
SCENE('p04', (t, a, b) => {
  headline(t, a, b, '零件 01 · VAE', '视频 VAE 是 3D 的，', '而且只往前看');
  const t3 = at('3d的', 'p04'), tk = at('取3帧', 'p04'), tn = at('相邻帧', 'p04'), tc = at('因果的', 'p04'), tf = at('只往前看', 'p04');
  const y0 = 500, rh = 250, g = 22, fs = 104, fg = 14, fx0 = 250;
  const rows = [
    { at: a + 0.2, big: '2D', sub: '图片 VAE', note: '核 3×3：只看本帧一小块', ok: false, v: '时间压不了', tv: t3, ker: [2] },
    { at: t3, big: '3D', sub: '普通 3D', note: '核 3×3×3：前后 3 帧各取一块', ok: false, v: '首帧要看未来', tv: tc, ker: [1, 2, 3] },
    { at: tc, big: '因果 3D', sub: 'Wan 用的', note: '核 3×3×3：当前帧和前 2 帧', ok: true, v: '图和视频共用', tv: tf, ker: [0, 1, 2], fut: true },
  ];
  rows.forEach((r, i) => {
    const p = pop(t, r.at - 0.1, 0.4); if (p <= 0) return;
    const y = y0 + i * (rh + g), hi = r.ok ? ease(t, tf, 0.4) : 0;
    ctx.save(); ctx.globalAlpha *= clamp(p); ctx.translate(0, (1 - clamp(p)) * 24);
    box(X0, y, CW, rh, { fill: hi > 0 ? C.accSoft : C.panel, line: hi > 0 ? C.acc : C.stroke, lw: hi > 0 ? 3 : 2 });
    T(r.big, X0 + 26, y + 108, { s: r.big.length > 2 ? 44 : 58, w: 900, c: r.ok ? C.acc : C.text });
    T(r.sub, X0 + 28, y + 152, { s: 26, w: 700, c: C.dim });
    T(r.note, fx0, y + 44, { s: 26, w: 800, c: C.acc });
    const pk = i === 1 ? ease(t, tk - 0.1, 0.4) : 1;
    for (let k = 0; k < 5; k++) {
      const x = fx0 + k * (fs + fg), fy = y + 64, future = r.fut && k > 2;
      catF(k, x, fy, fs, fs, { al: future ? 0.3 : 1 });
      frameBox(x, fy, fs, fs, k === 2 ? C.acc : C.faint, k === 2 ? 3.5 : 2);
      if (r.ker.includes(k)) { ctx.save(); ctx.globalAlpha *= pk; const pulse = i === 1 ? 1 + 0.08 * Math.max(0, Math.sin((t - tn) * 9)) * (t > tn && t < tn + 1.4 ? 1 : 0) : 1; ctx.translate(x + 30, fy + 30); ctx.scale(pulse, pulse);
        rr(-22, -22, 44, 44, 4); ctx.fillStyle = 'rgba(23,105,255,0.22)'; ctx.fill(); ctx.strokeStyle = C.acc; ctx.lineWidth = 3; ctx.setLineDash([6, 4]); ctx.stroke(); ctx.setLineDash([]);
        for (let q = 1; q < 3; q++) { ctx.beginPath(); ctx.moveTo(-22 + q * 14.7, -22); ctx.lineTo(-22 + q * 14.7, 22); ctx.moveTo(-22, -22 + q * 14.7); ctx.lineTo(22, -22 + q * 14.7); ctx.strokeStyle = C.acc; ctx.lineWidth = 1.2; ctx.stroke(); }
        ctx.restore(); }
    }
    if (r.ker.length > 1) { const xa = fx0 + r.ker[0] * (fs + fg) + 8, xb = fx0 + r.ker[r.ker.length - 1] * (fs + fg) + 52; ctx.save(); ctx.globalAlpha *= pk; ctx.strokeStyle = C.acc; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(xa, y + 60); ctx.lineTo(xa, y + 54); ctx.lineTo(xb, y + 54); ctx.lineTo(xb, y + 60); ctx.stroke(); ctx.restore(); }
    T('当前帧', fx0 + 2 * (fs + fg) + fs / 2, y + 206, { s: 24, w: 700, c: C.dim, a: 'center' });
    arrow(fx0 + 5 * (fs + fg) - 6, y + 116, fx0 + 5 * (fs + fg) + 30, y + 116, C.faint, 3, 1); T('时间', fx0 + 5 * (fs + fg) + 12, y + 96, { s: 20, w: 700, c: C.dim, a: 'center' });
    vcol(r.ok, r.v, 935, y + 100, ease(t, r.tv - 0.05, 0.35));
    ctx.restore();
  });
});

// ---------- 05 81 帧压成 21 帧 ----------
SCENE('p05', (t, a, b) => {
  headline(t, a, b, '零件 01 · VAE', '视频 VAE：', '81 帧压成 21 帧');
  const t81 = at('81帧', 'p05'), t21 = at('21帧', 'p05'), t1 = at('第1帧', 'p05'), ts = at('单独压', 'p05'), ti = at('图就是', 'p05'), t4 = at('每4帧', 'p05'), tsp = at('空间上', 'p05'), tw = at('万相压8倍', 'p05'), th = at('h3压16倍', 'p05');
  const y0 = 470, ph = ease(t, t81 - 0.15, 0.4);
  ctx.save(); ctx.globalAlpha *= ph; box(X0, y0, CW, 420, { r: 22 });
  T('像素帧：81 帧', X0 + 24, y0 + 48, { s: 30, w: 800 });
  const ts2 = 30, gg = 3, groups = [[1], [2, 5], [6, 9], [10, 13], [14, 17], null, [78, 81]];
  let x = X0 + 30; const fy = y0 + 76, centers = [];
  groups.forEach((gp, gi) => {
    if (!gp) { T('…', x + 6, fy + 26, { s: 36, w: 900, c: C.dim }); x += 46; centers.push(null); return; }
    const n = gp.length === 1 ? 1 : 4, gw = n * ts2 + (n - 1) * gg, first = gi === 0, lit = first ? ease(t, t1 - 0.05, 0.3) : ease(t, t4 + (gi - 1) * 0.12, 0.25);
    for (let k = 0; k < n; k++) catF(gi * 4 + k, x + k * (ts2 + gg), fy, ts2, ts2, { r: 3 });
    rr(x - 5, fy - 5, gw + 10, ts2 + 10, 6); ctx.strokeStyle = lit > 0.5 ? (first ? C.acc : C.acc) : C.faint; ctx.lineWidth = lit > 0.5 ? 3 : 2; ctx.stroke();
    T(first ? '第 1 帧' : `${gp[0]}–${gp[1]}`, x + gw / 2, fy + 76, { s: 24, w: 700, c: first ? C.acc : C.dim, a: 'center' });
    centers.push([x + gw / 2, lit]); x += gw + 22;
  });
  T('潜帧：21 帧', X0 + 24, y0 + 390, { s: 30, w: 800, al: ease(t, t21 - 0.1, 0.3) });
  const ly = y0 + 250, labels = ['1', '2', '3', '4', '5', '…', '21'];
  centers.forEach((c2, gi) => {
    const p = pop(t, (gi === 0 ? t21 - 0.1 : t21 + gi * 0.06), 0.35); if (p <= 0 || !c2) { if (p > 0 && !c2) T('…', X0 + 30 + 4 * 0 + 0, 0, {}); return; }
    const [cx, lit] = c2; const s2 = 66;
    arrow(cx, fy + 92, cx, ly - 8, lit > 0.5 ? C.acc : C.faint, 3, clamp(p), { hs: 10 });
    ctx.save(); ctx.translate(cx, ly + s2 / 2); const k = lerp(0.5, 1, clamp(p)); ctx.scale(k, k);
    rr(-s2 / 2, -s2 / 2, s2, s2, 12); ctx.fillStyle = gi === 0 ? C.acc : C.accSoft; ctx.fill(); ctx.strokeStyle = C.acc; ctx.lineWidth = 2.5; ctx.stroke();
    T(labels[gi], 0, 2, { f: F.en, s: 30, w: 400, c: gi === 0 ? C.accInk : C.acc, a: 'center', b: 'middle' }); ctx.restore();
  });
  if (ease(t, t21, 0.3) > 0) T('…', centers[4][0] + 82, ly + 44, { s: 36, w: 900, c: C.acc, al: ease(t, t21 + 0.3, 0.3) });
  if (pop(t, ts - 0.1, 0.3) > 0) chip('单独压', centers[0][0] + 6, fy + 140, { s: 24, h: 40, px: 12, a: 'center', al: ease(t, ts - 0.1, 0.3) });
  if (ease(t, t4, 0.3) > 0) chip('4 帧 → 1 帧', centers[2][0], fy + 140, { s: 24, h: 40, px: 12, bg: C.panel, fg: C.acc, line: C.acc, a: 'center', al: ease(t, t4, 0.3) });
  ctx.restore();
  // 下左：第 1 帧单独压 -> 图 = 1 帧视频
  const yb = 920, bw = 470, bh = 390;
  const pl = pop(t, ts - 0.1, 0.4);
  if (pl > 0) {
    ctx.save(); ctx.globalAlpha *= clamp(pl); box(X0, yb, bw, bh);
    T('第 1 帧前面没东西', X0 + 24, yb + 52, { s: 32, w: 900 }); T('只能单独压', X0 + 24, yb + 96, { s: 32, w: 900 });
    catF(0, X0 + 40, yb + 130, 150, 150, { r: 10 }); arrow(X0 + 210, yb + 205, X0 + 290, yb + 205, C.acc, 5, 1);
    rr(X0 + 310, yb + 160, 90, 90, 14); ctx.fillStyle = C.acc; ctx.fill(); T('1', X0 + 355, yb + 207, { f: F.en, s: 44, w: 400, c: C.accInk, a: 'center', b: 'middle' });
    const pi = ease(t, ti - 0.05, 0.35);
    T('所以 图 = 1 帧视频', X0 + 24, yb + 330, { s: 36, w: 900, c: C.acc, al: pi }); T('图和视频共用一个 VAE', X0 + 24, yb + 370, { s: 26, w: 700, c: C.dim, al: pi });
    ctx.restore();
  }
  // 下右：空间也压
  const pr2 = pop(t, tsp - 0.1, 0.4);
  if (pr2 > 0) {
    const x = X1 - bw; ctx.save(); ctx.globalAlpha *= clamp(pr2); box(x, yb, bw, bh);
    T('空间也压', x + 24, yb + 52, { s: 32, w: 900 });
    const gx = x + 24, gy = yb + 80, gs = 200; catF(3, gx, gy, gs, gs, { r: 4 });
    const pw = ease(t, tw - 0.05, 0.3), p16 = ease(t, th - 0.05, 0.3);
    ctx.save(); ctx.globalAlpha *= pw * (1 - 0.7 * p16); ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; for (let q = 1; q < 8; q++) { ctx.beginPath(); ctx.moveTo(gx + q * gs / 8, gy); ctx.lineTo(gx + q * gs / 8, gy + gs); ctx.moveTo(gx, gy + q * gs / 8); ctx.lineTo(gx + gs, gy + q * gs / 8); ctx.stroke(); } ctx.restore();
    if (pw > 0) { rr(gx, gy, gs / 8, gs / 8, 2); ctx.strokeStyle = C.text; ctx.lineWidth = 3; ctx.globalAlpha = clamp(pw * (1 - p16)) * ctx.globalAlpha; ctx.stroke(); ctx.globalAlpha = 1 * clamp(pr2); }
    if (p16 > 0) { ctx.save(); ctx.globalAlpha *= p16; ctx.strokeStyle = C.acc; ctx.lineWidth = 2.5; for (let q = 1; q < 4; q++) { ctx.beginPath(); ctx.moveTo(gx + q * gs / 4, gy); ctx.lineTo(gx + q * gs / 4, gy + gs); ctx.moveTo(gx, gy + q * gs / 4); ctx.lineTo(gx + gs, gy + q * gs / 4); ctx.stroke(); } rr(gx, gy, gs / 4, gs / 4, 2); ctx.lineWidth = 4; ctx.stroke(); ctx.restore(); }
    T('Wan', x + 250, yb + 130, { f: F.en, s: 30, w: 400, al: pw }); T('8×8 像素', x + 250, yb + 172, { s: 34, w: 800, al: pw }); T('→ 1 格', x + 250, yb + 210, { s: 34, w: 800, c: C.dim, al: pw });
    T('H3', x + 250, yb + 268, { f: F.en, s: 30, w: 400, c: C.acc, al: p16 }); T('16×16 像素', x + 250, yb + 310, { s: 34, w: 900, c: C.acc, al: p16 }); T('→ 1 格', x + 250, yb + 348, { s: 34, w: 800, c: C.acc, al: p16 });
    ctx.restore();
  }
});

// ---------- 06 为什么压 16 倍 ----------
SCENE('p06', (t, a, b) => {
  headline(t, a, b, '零件 01 · VAE', 'H3 为什么压 16 倍：', '注意力按平方涨');
  const t15 = at('15秒', 'p06'), tn = at('92万', 'p06'), tsq = at('平方', 'p06'), t5 = at('500倍', 'p06'), t8 = at('只压8倍', 'p06'), t80 = at('8000倍', 'p06'), te = atEnd('8000倍', 'p06');
  const y0 = 510, ph = ease(t, t15 - 0.1, 0.35);
  T('H3 视频 = 15 秒 768p', X0 + 8, y0, { s: 30, w: 800, c: C.dim, al: ph });
  T('token 数', 430, y0, { s: 28, w: 800, c: C.dim, al: ph }); T('注意力计算量', X1 - 8, y0, { s: 28, w: 800, c: C.dim, a: 'right', al: ease(t, tsq - 0.1, 0.3) });
  const rows = [
    { y: y0 + 40, at: tsq - 0.15, l1: '一张图', l2: '1024 × 1024', tok: 4096, txt: '4,096', att: '1 倍', ta: tsq, col: C.text },
    { y: y0 + 270, at: t8 - 0.1, l1: 'H3 视频，只压 8 倍', l2: '每 token 管 16×16 像素', tok: 367000, txt: '36.7 万', att: '≈ 8,000 倍', ta: t80, col: C.bad, bar: C.faint },
    { y: y0 + 500, at: tn - 0.15, l1: 'H3 视频，压 16 倍', l2: '每 token 管 32×32 像素', tok: 92000, txt: '9.2 万', att: '≈ 500 倍', ta: t5, col: C.acc, bar: C.acc, hi: true },
  ];
  rows.forEach(r => {
    const p = pop(t, r.at, 0.4); if (p <= 0) return;
    ctx.save(); ctx.globalAlpha *= clamp(p);
    box(X0, r.y, CW, 200, { fill: r.hi ? C.accSoft : C.panel, line: r.hi ? C.acc : C.stroke, lw: r.hi ? 3 : 2, shadow: !r.hi });
    T(r.l1, X0 + 24, r.y + 82, { s: 36, w: 900, c: r.hi ? C.acc : C.text }); T(r.l2, X0 + 24, r.y + 132, { s: 26, w: 700, c: C.dim });
    const g2 = E.o3(pr(t, r.at - 0.05, 0.7)), bw = Math.max(6, 170 * r.tok / 367000) * g2;
    rr(430, r.y + 74, bw, 56, 6); ctx.fillStyle = r.bar || C.text; ctx.fill();
    T(r.tok > 5000 ? (r.tok === 92000 ? `${(9.2 * g2).toFixed(1)} 万` : `${(36.7 * g2).toFixed(1)} 万`) : r.txt, 430 + bw + 14, r.y + 114, { s: 34, w: 800 });
    const pa = pop(t, r.ta - 0.05, 0.4);
    if (pa > 0) { ctx.save(); ctx.translate(X1 - 24, r.y + 112); const k = lerp(0.6, 1, clamp(pa)); ctx.scale(k, k); T(r.att, 0, 0, { s: 46, w: 900, c: r.col, a: 'right', al: clamp(pa) }); ctx.restore(); }
    ctx.restore();
  });
  const pf = ease(t, te + 0.25, 0.4);
  if (pf > 0) TT([['边长压 2 倍', {}], [' → ', { c: C.dim }], ['token 少 4 倍', {}], [' → ', { c: C.dim }], ['注意力少 16 倍', { c: C.acc }]], W / 2, 1300, { s: 34, w: 900, a: 'center', al: pf });
});

// ---------- 07 主干：所有帧的 token 互相看 ----------
SCENE('p07', (t, a, b) => {
  headline(t, a, b, '零件 02 · 主干', '主干：', '所有帧的 token 互相看');
  const tp = at('位置编码', 'p07'), tb = at('变成', 'p07'), t1 = at('一个token', 'p07'), ta = at('所有帧', 'p07');
  const pp = ease(t, tp - 0.1, 0.35), pb = E.ob(pr(t, tb, 0.45));
  const yP = 640;
  if (pp > 0) {
    T('位置编码', X0 + 8, yP - 110, { s: 30, w: 800, c: C.dim, al: pp });
    const o = { f: F.mono, s: 120, w: 800 };
    const parts = pb > 0 ? [['(', C.text], ['t', C.acc], [', ', C.acc], ['h, w)', C.text]] : [['(', C.text], ['h, w)', C.text]];
    let x = X0;
    for (const [s, col] of parts) {
      const isT = col === C.acc, w = MW(s, o) * (isT ? clamp(pb) : 1);
      if (isT) { ctx.save(); ctx.translate(x + w / 2, yP); const k = lerp(1.8, 1, clamp(pb)); ctx.scale(k, k); T(s, -MW(s, o) / 2, 0, { ...o, c: col, al: clamp(pb), b: 'middle' }); ctx.restore(); }
      else T(s, x, yP, { ...o, c: col, al: pp, b: 'middle' });
      x += w;
    }
    T('多了时间 t 这一轴', X0 + 8, yP + 100, { s: 30, w: 700, c: C.acc, al: clamp(pb) });
  }
  // 四帧 token 网格，斜向叠放
  const pg = ease(t, t1 - 0.25, 0.4);
  if (pg > 0) {
    const gs = 200, n = 4, cells = 4, cs = gs / cells, frames = [];
    for (let k = 0; k < 4; k++) frames.push([370 + k * 136, 1090 - k * 112]);
    for (let k = n - 1; k >= 0; k--) {
      const [fx, fy] = frames[k]; ctx.save(); ctx.globalAlpha *= clamp(pg * 2 - k * 0.3);
      box(fx, fy, gs, gs, { r: 6, sb: 10 });
      const lit = ease(t, ta + 0.25 + k * 0.15, 0.3);
      for (let i = 0; i < cells; i++) for (let j = 0; j < cells; j++) { rr(fx + j * cs + 4, fy + i * cs + 4, cs - 8, cs - 8, 4); ctx.fillStyle = k > 0 && lit > 0 ? `rgba(23,105,255,${0.06 + 0.16 * lit})` : C.panel2; ctx.fill(); ctx.strokeStyle = C.stroke; ctx.lineWidth = 1.5; ctx.stroke(); }
      T(`帧 ${k + 1}`, fx + gs + 10, fy + gs - 8, { s: 24, w: 700, c: C.dim });
      ctx.restore();
    }
    const [f0x, f0y] = frames[0], src = [f0x + cs * 1.5, f0y + cs * 2.5];
    const p1 = pop(t, t1, 0.35);
    if (p1 > 0) { rr(src[0] - cs / 2 + 4, src[1] - cs / 2 + 4, cs - 8, cs - 8, 4); ctx.fillStyle = C.acc; ctx.fill(); }
    for (let k = 1; k < n; k++) {
      const [fx, fy] = frames[k]; const dst = [fx + cs * (1.5 + (k % 2)), fy + cs * (0.5 + k * 0.7)];
      const q = ease(t, ta + (k - 1) * 0.18, 0.4); if (q <= 0) continue;
      arrow(src[0], src[1], lerp(src[0], dst[0], q), lerp(src[1], dst[1], q), C.acc, 3, 1, { head: false, dash: [6, 6] });
      if (q >= 1) { rr(dst[0] - cs / 2 + 6, dst[1] - cs / 2 + 6, cs - 12, cs - 12, 4); ctx.strokeStyle = C.acc; ctx.lineWidth = 3; ctx.stroke(); }
    }
    T('注意力不分帧', X0 + 8, 880, { s: 30, w: 800, c: C.dim, al: pg });
    T('一个 token', X0 + 8, 950, { s: 40, w: 900, al: p1 }); T('能看到', X0 + 8, 1006, { s: 40, w: 900, al: p1 });
    T('所有帧的', X0 + 8, 1074, { s: 40, w: 900, c: C.acc, al: ease(t, ta, 0.3) }); T('所有 token', X0 + 8, 1130, { s: 40, w: 900, c: C.acc, al: ease(t, ta, 0.3) });
  }
});

// ---------- 08 文字：交叉注意力 vs 拼进序列 ----------
SCENE('p08', (t, a, b) => {
  headline(t, a, b, '零件 03 · 文字', '文字：', '拼进同一条序列');
  const tw = at('万相编码', 'p08'), tc = at('交叉注意力', 'p08'), th = at('h3换成', 'p08'), tq = at('千问三vl', 'p08'), tj = at('拼进序列', 'p08');
  const ts = 38, tg = 7;
  const pw = pop(t, tw - 0.1, 0.4);
  if (pw > 0) {
    const y = 470; ctx.save(); ctx.globalAlpha *= clamp(pw); box(X0, y, CW, 360);
    T('Wan', X0 + 28, y + 70, { f: F.en, s: 50, w: 400 }); chip('umT5', X0 + 180, y + 54, { s: 28, h: 48, bg: C.acc2Soft, fg: C.acc2 });
    const vy = y + 170;
    for (let i = 0; i < 12; i++) token(X0 + 30 + i * (ts + tg), vy, ts, C.accSoft, C.acc);
    for (let i = 0; i < 4; i++) token(X0 + 750 + i * (ts + tg), vy, ts, C.acc2Soft, C.acc2);
    T('视频', X0 + 30 + 6 * (ts + tg) - 20, vy + 84, { s: 28, w: 800, c: C.dim, a: 'center' }); T('文字', X0 + 750 + 2 * (ts + tg) - 4, vy + 84, { s: 28, w: 800, c: C.dim, a: 'center' });
    const pc = ease(t, tc - 0.1, 0.4);
    if (pc > 0) {
      for (let k = 0; k < 3; k++) { const q = clamp(((t - tc) * 1.4 - k * 0.33) % 1.2); arrow(X0 + 735, vy + 19, lerp(X0 + 735, X0 + 590, q || pc), vy + 19, C.acc2, 4, 1, { al: pc }); }
      T('每层都走一次交叉注意力', X0 + 590, vy + 150, { s: 30, w: 800, c: C.acc2, al: pc });
    }
    ctx.restore();
  }
  const pH = pop(t, th - 0.1, 0.4);
  if (pH > 0) {
    const y = 870; ctx.save(); ctx.globalAlpha *= clamp(pH); box(X0, y, CW, 400, { fill: C.accSoft, line: C.acc, lw: 3, shadow: false });
    T('H3', X0 + 28, y + 70, { f: F.en, s: 50, w: 400, c: C.acc });
    const pq = pop(t, tq - 0.05, 0.35); if (pq > 0) chip('Qwen3-VL', X0 + 150, y + 54, { s: 28, h: 48, bg: C.acc2Soft, fg: C.acc2, k: lerp(0.6, 1, clamp(pq)), al: clamp(pq) });
    const pj = E.io(pr(t, tj - 0.1, 0.9)), sy = y + 200, total = 20, x0s = X0 + (CW - (total * (ts + tg) - tg)) / 2;
    const groups = [[4, C.acc2Soft, C.acc2, '文字'], [12, '#FFFFFF', C.acc, '视频'], [4, C.greenSoft, C.green, '音频']];
    let idx = 0; const startX = [X0 + 40, X0 + 240, X0 + 760], startY = [sy - 70, sy + 40, sy - 70];
    groups.forEach((g2, gi) => {
      for (let k = 0; k < g2[0]; k++, idx++) {
        const q = E.io(clamp(pj * 1.4 - idx / total * 0.4));
        const fx = startX[gi] + k * (gi === 1 ? 44 : 44), fy = startY[gi];
        token(lerp(fx, x0s + idx * (ts + tg), q), lerp(fy, sy, q), ts, g2[1], g2[2]);
      }
      const cx = x0s + (idx - g2[0] / 2) * (ts + tg) - tg / 2;
      T(g2[3], cx, sy + 86, { s: 28, w: 800, c: C.dim, a: 'center', al: pj });
    });
    if (pj > 0.7) { const q = pr(pj, 0.7, 0.3); rr(x0s - 14, sy - 14, total * (ts + tg) - tg + 28, ts + 28, 12); ctx.strokeStyle = C.acc; ctx.lineWidth = 3; ctx.globalAlpha *= q; ctx.stroke(); T('拼成一条序列，一起做注意力', W / 2, sy + 160, { s: 34, w: 900, c: C.acc, a: 'center' }); }
    ctx.restore();
  }
});

// ---------- 09 参考素材三种接法 ----------
SCENE('p09', (t, a, b) => {
  headline(t, a, b, '零件 04 · 参考', '参考素材三种接法，', 'H3 全用序列拼');
  const t1 = at('拼到通道', 'p09'), v1 = at('要改输入层', 'p09'), t2 = at('替换第一个', 'p09'), v2 = at('只能管首帧', 'p09'), t3 = at('变成token', 'p09'), v3 = at('结构不用改', 'p09'), tl = at('最后一种', 'p09');
  const last = ease(t, tl - 0.1, 0.4), y0 = 500, rh = 250, g = 22, vx = 470;
  const rows = [{ at: t1, n: '拼通道', s: 'Wan 图生视频', ok: false, v: '输入层要改', tv: v1 }, { at: t2, n: '替换首帧', s: 'Wan 5B', ok: false, v: '只能管首帧', tv: v2 }, { at: t3, n: '拼序列', s: 'H3', ok: true, v: '结构不用改', tv: v3 }];
  rows.forEach((r, i) => {
    const p = pop(t, r.at - 0.1, 0.4); if (p <= 0) return;
    const y = y0 + i * (rh + g), hi = r.ok ? last : 0;
    ctx.save(); ctx.globalAlpha *= clamp(p) * (r.ok ? 1 : 1 - 0.45 * last); ctx.translate(0, (1 - clamp(p)) * 24);
    box(X0, y, CW, rh, { fill: hi > 0 ? C.accSoft : C.panel, line: hi > 0 ? C.acc : C.stroke, lw: hi > 0 ? 3 : 2 });
    T(r.n, X0 + 24, y + 104, { s: 40, w: 900, c: r.ok ? C.acc : C.text }); T(r.s, X0 + 26, y + 146, { s: 25, w: 700, c: C.dim });
    const vx0 = 250, vy = y + 70;
    if (i === 0) {
      T('16', vx0 + 50, vy - 12, { f: F.mono, s: 26, w: 800, a: 'center' }); T('+ 4 +', vx0 + 150, vy - 12, { f: F.mono, s: 26, w: 800, a: 'center' }); T('16', vx0 + 250, vy - 12, { f: F.mono, s: 26, w: 800, a: 'center' }); T('= 36 通道', vx0 + 310, vy - 12, { s: 26, w: 900, c: C.acc });
      noise(vx0, vy + 8, 100, 100, 1, 2, { r: 6, cells: 6 }); rr(vx0 + 138, vy + 8, 24, 100, 4); ctx.fillStyle = '#fff'; ctx.fill(); ctx.strokeStyle = C.faint; ctx.lineWidth = 2; ctx.stroke();
      catF(0, vx0 + 200, vy + 8, 100, 100); frameBox(vx0 + 200, vy + 8, 100, 100, C.acc, 3);
      [['噪声', 50], ['掩码', 150], ['首帧', 250]].forEach(([s2, dx]) => T(s2, vx0 + dx, vy + 146, { s: 24, w: 700, c: C.dim, a: 'center' }));
    } else if (i === 1) {
      catF(0, vx0, vy + 8, 90, 90); frameBox(vx0, vy + 8, 90, 90, C.acc, 3);
      for (let k = 1; k < 6; k++) noise(vx0 + k * 100, vy + 8, 90, 90, 1, k + 4, { r: 6, cells: 6 });
      T('首帧不加噪', vx0 + 45, vy + 140, { s: 24, w: 800, c: C.acc, a: 'center' });
    } else {
      catF(0, vx0 + 20, vy - 30, 70, 70, { r: 6 }); frameBox(vx0 + 20, vy - 30, 70, 70, C.acc, 2.5);
      for (let k = 0; k < 4; k++) token(vx0 + k * 32, vy + 60, 28, C.accSoft, C.acc);
      for (let k = 0; k < 10; k++) token(vx0 + 140 + k * 32, vy + 60, 28, '#D5D9E0', null);
      T('参考图 token', vx0 + 60, vy + 130, { s: 24, w: 800, c: C.acc, a: 'center' }); T('待生成视频 token', vx0 + 300, vy + 130, { s: 24, w: 700, c: C.dim, a: 'center' });
    }
    vcol(r.ok, r.v, 935, y + 100, ease(t, r.tv - 0.05, 0.35));
    ctx.restore();
  });
});

// ---------- 10 采样：整段一起去噪 ----------
function shiftCurve(s, u) { return s * u / (1 + (s - 1) * u); } // u：1 -> 0 的均匀时间；返回噪声水平
SCENE('p10', (t, a, b) => {
  headline(t, a, b, '零件 05 · 采样', '整段一起去噪，', '不是一帧帧画');
  const tz = at('整段', 'p10'), tn = at('不是一帧', 'p10'), tt = at('token多了', 'p10'), th = at('高噪声段', 'p10'), tc = at('cfg蒸馏', 'p10'), t1 = at('只算一次', 'p10');
  const y0 = 470, pz = ease(t, tz - 0.15, 0.4);
  if (pz > 0) {
    ctx.save(); ctx.globalAlpha *= pz; box(X0, y0, CW, 330);
    const sig = [1, 0.66, 0.33, 0], prog = E.io(pr(t, tz, 2.0));
    for (let s = 0; s < 4; s++) {
      const x = X0 + 44 + s * 245, y = y0 + 70, sz = 150, on = prog * 4 >= s;
      ctx.save(); ctx.globalAlpha *= on ? 1 : 0.25;
      stack(3, x, y, sz, sz, (k, fx, fy, fw, fh) => catF(k + s, fx, fy, fw, fh, { sigma: sig[s], seed: s * 3, cells: 6 }), { dx: 10, dy: -10 });
      ctx.restore();
      if (s < 3) arrow(x + 178, y + 70, x + 222, y + 70, C.faint, 4, 1);
    }
    T('第 1 步', X0 + 110, y0 + 270, { s: 28, w: 800, a: 'center' }); T('第 N 步', X0 + 44 + 3 * 245 + 75, y0 + 270, { s: 28, w: 800, a: 'center' });
    T('所有帧同时从噪声变清楚', W / 2, y0 + 312, { s: 26, w: 700, c: C.dim, a: 'center' });
    ctx.restore();
  }
  // shift 曲线
  const pc = pop(t, tt - 0.15, 0.4);
  if (pc > 0) {
    const y = 830, h = 430; ctx.save(); ctx.globalAlpha *= clamp(pc); box(X0, y, CW, h);
    T('shift 越大，越多步数留在高噪声段', X0 + 24, y + 50, { s: 30, w: 900 });
    const gx = X0 + 70, gy = y + 80, gw = 560, gh = 290;
    ctx.strokeStyle = C.faint; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(gx, gy); ctx.lineTo(gx, gy + gh); ctx.lineTo(gx + gw, gy + gh); ctx.stroke();
    T('1', gx - 14, gy + 8, { f: F.mono, s: 22, w: 700, c: C.dim, a: 'right' }); T('0', gx - 14, gy + gh + 6, { f: F.mono, s: 22, w: 700, c: C.dim, a: 'right' });
    T('第 1 步', gx, gy + gh + 34, { s: 22, w: 700, c: C.dim }); T('第 40 步', gx + gw, gy + gh + 34, { s: 22, w: 700, c: C.dim, a: 'right' });
    const y8 = gy + gh * 0.2; ctx.setLineDash([8, 6]); ctx.beginPath(); ctx.moveTo(gx, y8); ctx.lineTo(gx + gw, y8); ctx.stroke(); ctx.setLineDash([]);
    T('0.8', gx - 14, y8 + 8, { f: F.mono, s: 22, w: 700, c: C.dim, a: 'right' }); T('高噪声段', gx + gw - 6, y8 - 12, { s: 22, w: 700, c: C.dim, a: 'right' });
    const curves = [[1, '#C3C8D0', 3, 'shift 1（均匀）', '20%'], [3, '#7A808A', 3.5, 'shift 3（SD3 生图）', '43%'], [12, C.acc, 6, 'shift 12（Wan、H3）', '75%']];
    curves.forEach(([s, col, lw, name, pct], ci) => {
      const pd = ci < 2 ? ease(t, tt + ci * 0.25, 0.7) : ease(t, th - 0.2, 0.9); if (pd <= 0) return;
      ctx.strokeStyle = col; ctx.lineWidth = lw; ctx.beginPath();
      for (let q = 0; q <= 60 * pd; q++) { const u = 1 - q / 60, x = gx + gw * q / 60, yy = gy + gh * (1 - shiftCurve(s, u)); q ? ctx.lineTo(x, yy) : ctx.moveTo(x, yy); }
      ctx.stroke();
      const ly = y + 150 + ci * 80; ctx.fillStyle = col; ctx.fillRect(gx + gw + 40, ly - 8, 34, lw + 2);
      T(name, gx + gw + 84, ly, { s: 22, w: 700, c: ci === 2 ? C.acc : C.dim, al: pd });
      T(pct + ' 的步数 > 0.8', gx + gw + 84, ly + 32, { s: ci === 2 ? 28 : 22, w: 900, c: ci === 2 ? C.acc : C.dim, al: pd });
    });
    ctx.restore();
  }
  const pf = ease(t, tc - 0.1, 0.35);
  if (pf > 0) {
    const p1 = pop(t, t1, 0.35), y = 1318;
    const w1 = T('CFG 蒸馏：每步算', X0 + 8, y, { s: 38, w: 900, al: pf });
    T('2 次', X0 + 20 + w1, y, { s: 38, w: 900, c: C.dim, al: pf * (1 - 0.5 * clamp(p1)) }); strike(X0 + 16 + w1, y - 13, 80, p1, C.bad, 5);
    if (p1 > 0) T('→ 1 次', X0 + 116 + w1, y, { s: 38 * lerp(0.7, 1, clamp(p1)), w: 900, c: C.acc, al: clamp(p1) });
  }
});

// ---------- 11 训练（Wan）----------
SCENE('p11', (t, a, b) => {
  headline(t, a, b, '训练 · 以 Wan 为例', 'Wan 怎么训：', '任务不变，只换数据');
  const tk = at('任务', 'p11'), tj = at('文生图加', 'p11'), td = at('变的是数据', 'p11'), t256 = at('256', 'p11'), tv = at('再加视频', 'p11'), t192 = at('192p', 'p11'), t720 = at('720p', 'p11'), tf = at('精选数据', 'p11'), te = L('p11').end;
  const cx0 = 190, cw = 164, cg = 6, ys = 470;
  const st = [['阶段 0', '只训图片'], ['阶段 1', '图 + 视频'], ['阶段 2', '升到 480px'], ['阶段 3', '升到 720px'], ['后训练', '精选数据']];
  const sAt = [t256 - 0.1, tv - 0.1, t720 - 0.5, t720, tf - 0.1];
  const ph = ease(t, a, 0.4);
  st.forEach((s, i) => {
    const x = cx0 + i * (cw + cg), on = ease(t, sAt[i], 0.3);
    box(x, ys, cw, 100, { r: 14, fill: on > 0.5 ? C.accSoft : C.panel, line: on > 0.5 ? C.acc : C.stroke, lw: on > 0.5 ? 3 : 2, shadow: false, al: ph });
    T(s[0], x + cw / 2, ys + 42, { s: 28, w: 900, a: 'center', c: on > 0.5 ? C.acc : C.text, al: ph }); T(s[1], x + cw / 2, ys + 80, { s: 22, w: 700, a: 'center', c: C.dim, al: ph });
    if (i < 4) arrow(x + cw + 1, ys + 50, x + cw + cg + 1, ys + 50, C.faint, 2, 1, { al: ph, hs: 6 });
  });
  const rl = (s, y, p) => T(s, X0 + 8, y, { s: 32, w: 900, al: p });
  const pk = ease(t, tk - 0.1, 0.35);
  rl('任务', 640, pk);
  if (pk > 0) { chip('文生图', cx0 + cw / 2, 628, { s: 26, h: 54, bg: C.accSoft, fg: C.acc, a: 'center', al: pk }); }
  const pj = pop(t, tj, 0.4);
  if (pj > 0) { ctx.save(); ctx.globalAlpha *= clamp(pj); rr(cx0 + cw + cg, 601, 4 * (cw + cg) - cg, 54, 12); ctx.fillStyle = C.accSoft; ctx.fill(); T('文生图 + 文生视频，混在一起训', cx0 + cw + cg + (4 * (cw + cg) - cg) / 2, 638, { s: 28, w: 900, c: C.acc, a: 'center' }); ctx.restore(); }
  const pd = ease(t, td - 0.1, 0.35);
  rl('图片', 800, pd); rl('视频', 1070, pd);
  const imgSz = [56, 56, 100, 140, 140], imgL = ['256px', '256px', '480px', '720px', '480/720px'];
  const vidSz = [0, 44, 92, 124, 124], vidL = ['不训视频', '192px·5 秒', '480px·5 秒', '720px·5 秒', '480/720px'];
  for (let i = 0; i < 5; i++) {
    const x = cx0 + i * (cw + cg) + cw / 2, on = ease(t, sAt[i], 0.35); if (on <= 0) continue;
    ctx.save(); ctx.globalAlpha *= on;
    const s = imgSz[i] * lerp(0.6, 1, on); catF(i, x - s / 2, 860 - s, s, s, { r: 4 }); frameBox(x - s / 2, 860 - s, s, s, C.faint, 1.5, 4);
    T(imgL[i], x, 898, { s: 22, w: 700, c: C.dim, a: 'center' });
    if (i === 0) { rr(x - 50, 1024, 100, 100, 10); ctx.setLineDash([6, 5]); ctx.strokeStyle = C.faint; ctx.lineWidth = 2; ctx.stroke(); ctx.setLineDash([]); T('不训视频', x, 1080, { s: 22, w: 700, c: C.dim, a: 'center' }); }
    else { const v = vidSz[i] * lerp(0.6, 1, on); stack(3, x - v / 2 - 8, 1128 - v, v, v, (k, fx, fy, fw, fh) => catF(k + i, fx, fy, fw, fh, { r: 3 }), { dx: 8, dy: -8 }); }
    T(vidL[i], x, 1166, { s: 22, w: i === 1 && t > t192 ? 900 : 700, c: i === 1 && t > t192 ? C.acc : C.dim, a: 'center' });
    ctx.restore();
  }
  const pe = ease(t, te - 1.0, 0.4);
  if (pe > 0) { box(X0, 1205, CW, 120, { fill: C.panel2, shadow: false, al: pe }); T('图生视频、续写、首尾帧：在这之后另训', X0 + 24, 1255, { s: 30, w: 900, al: pe }); T('文字编码器和 VAE 全程冻住，只训主干', X0 + 24, 1301, { s: 24, w: 700, c: C.dim, al: pe }); }
});

// ---------- 12 数据（Wan）----------
SCENE('p12', (t, a, b) => {
  headline(t, a, b, '训练 · 以 Wan 为例', 'Wan 的数据：', '数十亿图片和视频');
  const t0 = at('数十亿', 'p12'), t1 = at('滤掉水印', 'p12'), tc = at('砍掉一半', 'p12'), tp = at('后训练', 'p12'), t20 = at('前百分之二十', 'p12'), th = at('h3只说', 'p12');
  const p0 = ease(t, t0 - 0.1, 0.35);
  T('原始：数十亿图片和视频，万亿级 token', X0 + 8, 490, { s: 34, w: 900, al: p0 });
  const stages = [
    ['① 基础过滤', '水印、黑边、模糊、过曝、AIGC…', t1 - 0.1], ['② 画质打分', '聚成 100 类，人工打分训打分模型', tp - 0.9], ['③ 运动分 6 档', '静态、纯运镜降权，抖动删除', tp - 0.65],
    ['④ 补文字数据', '合成上亿张带字图片', tp - 0.4], ['⑤ 后训练精选', '图片只留前 20%，视频数百万条', tp - 0.1]];
  const fx = X0 + 10, fw0 = 300, y0 = 540, sh = 128, sg = 12;
  stages.forEach((s, i) => {
    const p = ease(t, s[2], 0.35); if (p <= 0) return;
    const y = y0 + i * (sh + sg), wTop = fw0 * (1 - i * 0.14), wBot = fw0 * (1 - (i + 1) * 0.14), cx = fx + fw0 / 2, last = i === 4;
    ctx.save(); ctx.globalAlpha *= p;
    ctx.beginPath(); ctx.moveTo(cx - wTop / 2, y); ctx.lineTo(cx + wTop / 2, y); ctx.lineTo(cx + wBot / 2, y + sh); ctx.lineTo(cx - wBot / 2, y + sh); ctx.closePath();
    ctx.fillStyle = last ? C.acc : i === 0 ? '#C9CED6' : C.panel2; ctx.fill();
    T(s[0], fx + fw0 + 36, y + 52, { s: 34, w: 900, c: last ? C.acc : C.text }); T(s[1], fx + fw0 + 36, y + 96, { s: 25, w: 700, c: C.dim });
    ctx.restore();
  });
  const pc = pop(t, tc - 0.1, 0.4);
  if (pc > 0) { const n = Math.round(50 * E.o3(pr(t, tc - 0.1, 0.6))); T('砍掉', fx + fw0 / 2, y0 + 50, { s: 26, w: 800, a: 'center', al: clamp(pc) }); T(`约 ${n}%`, fx + fw0 / 2, y0 + 100, { s: 40, w: 900, c: C.bad, a: 'center', al: clamp(pc) }); }
  const p20 = pop(t, t20 - 0.05, 0.35);
  if (p20 > 0) { const y = y0 + 4 * (sh + sg); T('20%', fx + fw0 / 2, y + 80, { f: F.en, s: 40 * lerp(0.6, 1, clamp(p20)), w: 400, c: C.accInk, a: 'center', al: clamp(p20) }); }
  const ph = pop(t, th - 0.1, 0.4);
  if (ph > 0) { ctx.save(); ctx.globalAlpha *= clamp(ph); box(X0, 1250, CW, 90, { fill: C.accSoft, line: C.acc, lw: 3, shadow: false }); TT([['H3 只说：', { c: C.acc }], ['全是真实数据，量没公开', {}]], X0 + 28, 1308, { s: 36, w: 900 }); ctx.restore(); }
});

// ---------- outro：评论区见 ----------
SCENE('outro', (t, a, b) => {
  headline(t, a, b, '下期', '想看哪个零件', '深挖？');
  const td = at('深挖', 'outro'), tq = at('想看哪个', 'outro'), tp = at('评论区', 'outro');
  PARTS.forEach((nm, i) => {
    const p = pop(t, td - 0.2 + i * 0.08, 0.35); if (p <= 0) return;
    const x = X0 + (i % 3) * 330, y = 520 + Math.floor(i / 3) * 170;
    ctx.save(); ctx.globalAlpha *= clamp(p); ctx.translate(x + 150, y + 60); ctx.scale(lerp(0.6, 1, clamp(p)), lerp(0.6, 1, clamp(p)));
    box(-150, -60, 300, 120, { r: 20 }); T('0' + (i + 1), -120, 10, { f: F.mono, s: 26, w: 800, c: C.acc, b: 'middle' }); T(nm, 10, 6, { s: 46, w: 900, a: 'center', b: 'middle' });
    ctx.restore();
  });
  const pq = ease(t, tq - 0.1, 0.3);
  if (pq > 0) {
    const x = X0, y = 900, w = CW, hh = 130;
    ctx.save(); ctx.globalAlpha *= pq;
    box(x, y, w, hh, { r: 65, line: C.acc, lw: 4 });
    const msg = '想看哪个零件深挖？', n = Math.floor(clamp(pr(t, tq, 1.0)) * msg.length);
    T(msg.slice(0, n) + (Math.floor(t * 3) % 2 ? '|' : ''), x + 50, y + 82, { s: 44, w: 700 });
    const ps = E.ob(pr(t, tp, 0.35));
    if (ps > 0) {
      const k = (ps < 1 ? lerp(0.7, 1, ps) : 1) * (1 + 0.05 * Math.max(0, Math.sin((t - tp) * 9)) * clamp(pr(t, tp + 0.35, 0.1)));
      ctx.save(); ctx.translate(x + w - 135, y + 65); ctx.scale(k, k); rr(-115, -47, 230, 94, 47); ctx.fillStyle = C.acc; ctx.fill(); T('评论区见', 0, 14, { s: 40, w: 900, c: C.accInk, a: 'center' }); ctx.restore();
      const pa = E.o3(pr(t, tp + 0.25, 0.35));
      if (pa > 0) { const yy = y + hh + 30 + 10 * Math.sin(t * 7); arrow(x + w - 135, yy + 70, x + w - 135, yy, C.acc, 6, 1, { al: pa }); }
    }
    ctx.restore();
  }
  T('你的署名 · 栏目名', X0 + 8, 1300, { s: 36, w: 900, c: C.dim, al: ease(t, tp + 0.4, 0.4) });
});

// ---------- 音效：挂在词上 ----------
PLAN = () => {
  cue(at('生图', 'hook'), 'pop', 0.7); cue(at('时间轴', 'hook'), 'whoosh', 0.7); cue(at('配方没变', 'hook'), 'tick', 0.6); PARTS.forEach((_, i) => cue(at('几个零件', 'hook') + i * 0.07, 'tick', 0.5));
  cue(at('minimax', 'intro'), 'pop', 0.6); cue(at('技术报告', 'intro'), 'tick', 0.6); cue(at('全公开', 'intro'), 'pop', 0.6); cue(at('对照', 'intro'), 'hit', 0.6);
  cue(at('闭源的', 'p01'), 'pop', 0.6); cue(at('开源的33b', 'p01'), 'pop', 0.7); cue(at('重画', 'p01'), 'pop', 0.6);
  cue(at('一块噪声', 'p02'), 'pop', 0.6); cue(at('去噪n步', 'p02'), 'tick', 0.6); cue(at('vae解码', 'p02'), 'tick', 0.6); cue(at('多一维', 'p02'), 'hit', 0.7);
  ['vae', '主干', '文字', '参考', '采样'].forEach(k => cue(at(k, 'p03'), 'tick', 0.6)); cue(at('各选各的', 'p03'), 'swipe', 0.6);
  cue(at('3d的', 'p04'), 'pop', 0.6); cue(at('取3帧', 'p04'), 'tick', 0.6); cue(at('因果的', 'p04'), 'pop', 0.6); cue(at('只往前看', 'p04'), 'sparkle', 0.5);
  cue(at('81帧', 'p05'), 'tick', 0.6); cue(at('21帧', 'p05'), 'pop', 0.7); cue(at('每4帧', 'p05'), 'riser', 0.4); cue(at('h3压16倍', 'p05'), 'hit', 0.7);
  cue(at('92万', 'p06') - 0.2, 'riser', 0.32); cue(at('500倍', 'p06'), 'pop', 0.55); cue(at('只压8倍', 'p06'), 'riser', 0.35); cue(at('8000倍', 'p06'), 'boom', 0.38);
  cue(at('变成', 'p07'), 'hit', 0.7); cue(at('所有帧', 'p07'), 'sparkle', 0.5);
  cue(at('交叉注意力', 'p08'), 'swipe', 0.5); cue(at('千问三vl', 'p08'), 'pop', 0.6); cue(at('拼进序列', 'p08'), 'whoosh', 0.6);
  cue(at('要改输入层', 'p09'), 'tick', 0.6); cue(at('只能管首帧', 'p09'), 'tick', 0.6); cue(at('结构不用改', 'p09'), 'pop', 0.7); cue(at('最后一种', 'p09'), 'hit', 0.6);
  cue(at('整段', 'p10'), 'riser', 0.45); cue(at('不是一帧', 'p10'), 'swipe', 0.55); cue(at('高噪声段', 'p10'), 'tick', 0.6); cue(at('只算一次', 'p10'), 'hit', 0.7);
  cue(at('文生图加', 'p11'), 'pop', 0.6); cue(at('256', 'p11'), 'tick', 0.6); cue(at('再加视频', 'p11'), 'tick', 0.6); cue(at('720p', 'p11'), 'tick', 0.6); cue(at('精选数据', 'p11'), 'pop', 0.6);
  cue(at('滤掉水印', 'p12'), 'swipe', 0.5); cue(at('砍掉一半', 'p12'), 'hit', 0.6); cue(at('前百分之二十', 'p12'), 'pop', 0.7); cue(at('h3只说', 'p12'), 'tick', 0.6);
  PARTS.forEach((_, i) => cue(at('深挖', 'outro') - 0.2 + i * 0.08, 'tick', 0.5));
  const tq = at('想看哪个', 'outro'); for (let i = 0; i < 9; i++) cue(tq + i * 0.11, 'type', 0.3);
  cue(at('评论区', 'outro'), 'pop', 0.8);
};
