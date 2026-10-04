// scenes.js — 本专题的画面。每句口播（script.json 的 id）挂一个 SCENE；动效用 at('词', 'id') 踩在配音上。
// 可用：headline / box / chip / tag / arrow / mark / strike / T / TT / img / noise / stack / pop / ease / cue，颜色用 C.*，字体 F.*。
ASSETS = { demo: '/assets/demo.png' };  // 示意图用一张固定的 demo 图（不用本人头像）
TRACKER = null;                          // 需要「一线到底」进度条时：{ items: [...], from: () => 秒, to: () => 秒, active: t => [下标] }

SCENE('hook', (t, a, b) => {
  headline(t, a, b, '', '开场一句', '结论');
  const p = pop(t, a + 0.3);
  img(IM.demo, 340, 820, 400, 400, { r: 24, al: p });
});
SCENE('p01', (t, a, b) => {
  headline(t, a, b, '01 · 要点', '第一个', '要点');
});
SCENE('outro', (t, a, b) => {
  headline(t, a, b, '', '想看哪个，', '评论区说');
});
PLAN = () => { /* cue(at('词', 'p01'), 'pop', 0.7); 音效：tick pop swipe whoosh hit boom glitch riser sparkle type */ };
