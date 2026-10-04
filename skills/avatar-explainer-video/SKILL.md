---
name: avatar-explainer-video
description: 把一篇技术图文（如小红书拆解帖及其配图）做成本人出镜的竖屏口播讲解短视频：克隆本人声音配音、对口型（HeyGen 或百炼）、右下角圆形摄像头小窗、代码逐帧渲染的信息图动效（动效踩在口播的词上）、卡拉 OK 字幕、配乐和音效。用于「把这篇做成视频」「做个数字人口播」「出一条竖屏讲解短视频」「改一下那条口播视频」。
---

# 口播讲解竖屏视频

交付一条 1080×1920、30fps 的成片：右下角是本人摄像头小窗（AI 对口型），上方是逐句出现的信息图，底部是逐字高亮字幕。整条片子由 `scenes.js` 里的代码逐帧画出来，所以改一处、重渲只要几十秒。

入口是 `studio avatar`（explainer-studio 仓库的 `bin/studio`），代码在仓库 `studio/avatar/`。每条片子一个专题目录（放在工作区 `projects/<名字>/`，工作区路径见 config.toml），除 `init` 外的命令都在专题目录里运行。完整范例：仓库 `examples/h3-five-parts/`（`scenes.js` 有 15 段写法可抄）。

## 硬规则（用户纠正过，默认执行）

1. **不自曝数字分身，不秀制作效率。**开场和结尾都不说「这是 AI/数字分身做的」，不放「今日录制 0 分钟、代码 N 行」这类统计。开场直接用内容的结论句当钩子。
2. **摄像头取景永远是整幅画高（头+肩完整）。**窗口变大变小只缩放窗口，不收紧取景，转场插值也不许出现切进脸里的镜头。`core.js` 的 `camState` 已这么写，别改成按人脸放大。
3. **示意图不用本人头像**，图片或视频帧的占位一律用同一张示意图（`assets/demo.png`，`init` 从 config 的 `[me] demo_image` 拷进去，没配就生成占位图）。表示「视频」就叠几张轻微错位的示意图，表示噪声用块状灰度噪声（`noise()`）。
4. **信息表达照作者自己的图文稿。**口播尽量用原稿措辞，数字只用原稿里有的。一句口播配一个画面，版式照原稿配图：标题是「黑字结论 + 蓝字关键词」，内容放在白卡片里，用对照表、✓/✗ 下判断。先把原稿和配图读一遍，再写 `scenes.js`。
5. **先对齐再花钱。**时长、版本数、讲哪几段先和用户确认（对口型约 0.1 美元/秒）。

## 制作顺序

1. **建专题**：`studio avatar init <工作区>/projects/<名字>`，然后改 `topic.json`。
   - 字段：录像 `camera.video`、`camera.mic`、驱动起点 `camera.start`、配色 `theme`、开场大窗持续到哪句 `camera_open_until`、片尾留白 `tail`。
   - 已克隆过的声音写进 `voice.clone_result` 复用，不必重复克隆。
2. **写稿 `script/script.json`**：每句有 `id`、`show`（字幕显示）、`say`（给 TTS 念）。
   - 语速 1.12 时约 4.3 字/秒，2 分钟约 500 个汉字、580 个字符。
   - 英文名的读法写进 `say`：Wan → 万相，Qwen3-VL → 千问三VL，4K token → 4千个token，20% → 百分之二十。屏幕上照常显示 `show`。
3. **配音 + 对齐**：`studio avatar voice`，会打出 whisper 听写。
   - 听写里把同音字写错（噪声→造声）不要紧；英文名被听成别的词（Wan 被听成 One）说明 TTS 读错了，改 `say` 重配。
   - `work/timeline.json` 的 match_ratio 要 ≥ 0.9。
4. **对口型**：先 `studio avatar driver`，再在后台跑 `studio avatar lipsync`，2 分钟片要 10–15 分钟。
   - 驱动段要挑人在正常说话、手不挡嘴的一段；挑好的起点写进 config 的 `[me] camera_start`，以后新专题自动带上。
5. **写画面 `scenes.js`**：每句一个 `SCENE(id, (t, a, b) => {...})`，动效用 `at('词', id)` 踩点。API 见 [画面写法](references/画面写法.md)。
   - 对口型还没回来时，先 `studio avatar prep work/lipsync/driver.mp4` 用驱动底片抽帧，`studio avatar stills 3.0 9.5 …` 出静帧检查版式，再 `studio avatar sheet` 拼成联系表看。
6. **配乐**：`studio avatar bgm`（约 3 美元，按时间轴分开场、讲解、收尾三段）。
7. **出片**：对口型回来后 `studio avatar prep`，再 `studio avatar build`，产出 `out/<out_name>.mp4`。
8. **质检**：`studio avatar qc out/x.mp4 r1`，交给视觉模型连看带听（Gemini，或百炼千问全模态）。
   - 模型看的是 270×480 的压缩片，「字幕挡住画面」「字太小」常是误判。先在静帧上核实再改。
   - 改完重新 build，再抽静帧确认。
9. **交付**：给成片绝对路径和一条 `open` 命令，说明花费和已知限制。长任务做完主动通知用户。

## 服务选哪家

`config.toml` 的 `[providers]` 决定每个环节走哪家，`studio setup` 会列出当前选择和缺的密钥。

- 国内用户全选 `bailian`：一把 `DASHSCOPE_API_KEY`，配音、对口型、质检都在百炼；配乐填 `none`，在 `topic.json` 写 `bgm.file` 用自己的曲子。
- 对口型画质 HeyGen（`fal`）最好；百炼 VideoRetalk 嘴型偏夸张，但便宜十倍，单段最长 120 秒，`lipsync` 会自动切段再拼。
- 配音 `providers.voice` 四选一：`fal` / `bailian`（都是 MiniMax speech-2.8-hd）、`qwen`（千问 Qwen-Audio-3.0-TTS）、`cosyvoice`（CosyVoice v3.5）。三家并排听过音色都像；MiniMax 一次合成整稿，语速用 `voice.speed`（默认 1.12），千问和 CosyVoice 逐句合成再拼，语速用 `voice.rate`（默认 1.0，快慢和 MiniMax 1.12 相当）。
- 各家克隆的声音互不通用，分别存 `work/voice/clone_result[_<家>].json`；切换 `providers.voice` 后要重新 `clone`（千问和 CosyVoice 克隆免费，样本取 20 秒）。
- 比较几家配音时先统一响度再听：MiniMax 原始输出比千问小约 6 dB，容易被误听成「声音小」；成片 `mix` 会统一响度。
- 百炼报「product is not activated」：去百炼控制台模型广场开通对应模型（MiniMax 配音要单独开通）。

## 已知会出错的地方

| 现象 | 处理 |
| --- | --- |
| HeyGen 422「durations too different」或「audio missing」 | 驱动必须和配音几乎等长且带音轨；`driver.py` 已按「配音时长 + 0.3 秒，混入同段麦克风」处理 |
| ElevenLabs 422 | `composition_plan` 不能和 `force_instrumental` 一起用，靠 `negative_styles` 去人声 |
| Gemini 返回 404 或空 | 部分 API 中转服务拒收约 1.5MB 以上的请求体；`qc.py` 已切两半、压到 270×480 |
| Python 报 SSL 证书错 | python.org 版 Python 不带根证书；`config.ca_file()` 先用 certifi，其次系统证书包 |
| `at()` 报「不在配音里」 | 关键词要用 `say` 里的写法（万相、千问三VL），标点空格会自动忽略 |
| 标题太长 | `headline()` 放不下时把蓝字换到第二行，内容区要从 y≈480 开始 |
| 画面元素压在一起 | 内容区 y 400–1340，字幕在 1420，小窗在右下 1460–1800；横向 48–1032 |

## 花费参考（2 分 15 秒）

配音约 0.2 美元，对口型约 13.5 美元，配乐约 3 美元，Gemini 质检不到 1 美元。声音克隆约 1.5 美元，只做一次。
