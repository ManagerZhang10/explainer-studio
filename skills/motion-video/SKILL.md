---
name: motion-video
description: 做无配音的文字动效短视频（宣传片、发布会风功能介绍、仓库/skill 推广短片）：先写单文件 HTML 动画，`studio motion preview` 出关键帧总览图 + 浏览器循环预览给用户确认，确认后 `studio motion render` 逐帧渲染并按音效时间表混音出 mp4。用于「做个宣传片」「做条文字动效短视频」「发布会风的短片」「把这个 HTML 动画导成视频」。有口播、要本人出镜的讲解视频不用它，走 avatar-explainer-video。
---

# 文字动效短视频

只有文字、图形、动效和配乐，没有配音和人。逐帧渲染慢，所以流程的核心是**先给人看、确认了再渲染**。

## 什么时候用

| 情况 | 走哪条 |
| --- | --- |
| 宣传片、发布会风、功能/仓库推广，全片靠上屏文字 + 动效 + 配乐 | 本 skill（`studio motion`） |
| 要本人出镜、有配音口播的讲解 | avatar-explainer-video（`studio avatar`） |
| 录屏讲课剪辑 | lecture-video-cut（`studio cut`） |

## 流程（四步，第 3 步必须停下等确认）

1. **对齐分镜表**：时间段 / 画面 / 上屏文字一张表，先和用户对齐，再写代码。
2. **写 HTML 动画**：`studio motion init <专题目录>` 复制模板（`index.html` + `motion.json`）。
   - 所有画面状态写成 `render(t)` 的纯函数：同一个 t 永远同一帧，不用 CSS transition / animation、不读真实时间。
   - 模板里有 `P(t,a,b,ease)` 进度、`L` 插值、`show` 淡入位移、`type` 逐字打出、`scene` 镜头区间和几种缓动，时间点直接照分镜表填。
   - HTML 里的 `DUR` 和 `motion.json` 的 `duration` 保持一致。
3. **预览给用户看**：`studio motion preview index.html --open`。
   - 出 `<名字>_keyframes.png` 总览图（每格标秒数），同时浏览器循环播放。把总览图路径和 HTML 路径都给用户。
   - 时间点：`--times 0.5,3,7.2` 指定，`--n 12` 均匀取，或写进 `motion.json` 的 `preview`。挑每个镜头「到位」的那一刻，不要挑过渡中间。
   - 自己先看一遍总览图：字有没有出界、相邻镜头有没有叠在一起、关键帧有没有空屏。
   - **停在这里等用户确认**，改动都在这一步来回。
4. **确认后渲染**：先 `studio motion render index.html --dur 2 -o <临时.mp4>` 确认能出片、有音轨，再全长渲染：
   `studio motion render index.html -o out/<名字>.mp4`。

## motion.json 怎么写

```json
{"duration": 20, "fps": 30, "width": 1080, "height": 1920, "selector": "#stage",
 "output_size": "1080x1920", "preview": [0.5, 3, 7.2],
 "bgm":  {"file": "bgm-tech.mp3", "volume": 0.45, "fade_in": 0.2, "fade_out": 1.8},
 "cues": [{"t": 1.35, "file": "keyboard/type-fast.mp3", "volume": 0.55}]}
```

- `width`/`height` 是舞台 CSS 尺寸，要和 HTML 里 `#stage` 一致；`output_size` / `--size` 只做同比例缩放。
- 音效 cue 的 `t` 对齐 `render(t)` 里对应动作开始的时刻（字砸下、卡片弹出、转场起点），不要按分镜段落粗放。
- 素材路径相对 `motion.json` 或 config 的 `[motion] sfx_dir` / `bgm_dir`；临时换目录用 `--sfx-dir` / `--bgm-dir`。

## 判断要点

1. 手机竖屏看：上屏文字 ≥ 44px（1080 宽），主标题 ≥ 96px，一屏只讲一句话。
2. 小红书等平台的成片里不放网址，写「GitHub 搜 仓库名」。
3. 渲染报「页面报错」就别交片，先修 JS 报错；渲染出来和预览不一致，多半是用了 CSS transition 或真实时间。
