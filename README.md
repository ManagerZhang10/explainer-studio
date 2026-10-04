# explainer-studio

做中文技术讲解短视频的工具箱：拆别人的视频学手法，再用自己的声音和形象，把一个知识点做成逐帧动画讲解。

> A toolkit for making Chinese tech-explainer videos: study reference videos from other creators, then turn one concept into a narrated, frame-by-frame animated explainer with your own cloned voice and lip-synced camera bubble. Everything is driven by one CLI (`studio`) and a set of agent skills (Claude Code / Codex).

## 能做什么

| 模块 | 命令 | 产出 |
| --- | --- | --- |
| 竖屏口播 | `studio avatar …` | 1080×1920 讲解片：克隆声音配音、本人小窗对口型、逐句挂词的 Canvas 信息图、配乐和音效 |
| 录屏剪辑 | `studio cut …` | 录屏讲课（屏幕 / 摄像头 / 麦克风三轨）去气口、删卡壳、逐字字幕、圆形摄像头 |
| 参考视频 | `studio refs …` | 抓博主视频、转写、切镜、算语速和切镜频率、让 Gemini 拆开场钩子和画面层 |

每个模块配一个 skill（`skills/`），告诉 Agent 什么时候用、怎么判断好坏；真正干活的都在 `studio/` 的脚本里，裸终端也能直接跑。

## 安装

需要 macOS（Apple 芯片跑 mlx-whisper 对齐；其他平台换任意 whisper，输出同格式 JSON 即可）、Python ≥ 3.11、ffmpeg。

```bash
git clone https://github.com/ManagerZhang10/explainer-studio.git
cd explainer-studio
pip install playwright numpy pillow "opencv-python-headless<5" mlx-whisper certifi edge-tts
playwright install chromium
ln -s "$PWD/bin/studio" ~/.local/bin/studio        # 任意目录可调用

mkdir -p ~/.config/explainer-studio
cp config.example.toml ~/.config/explainer-studio/config.toml   # 改工作区、密钥文件、本人素材路径
studio setup                                                     # 下载开源字体，检查依赖和密钥
```

密钥写在 config 指定的 env 文件里（`KEY=VALUE` 一行一个），代码只在内存里读，不落盘、不打印：

| 变量 | 用途 |
| --- | --- |
| `FAL_KEY` | 声音克隆与配音（MiniMax）、对口型（HeyGen）、配乐（ElevenLabs），都走 fal |
| `GEMINI_API_KEY` / `GEMINI_BASE_URL` / `GEMINI_MODEL` | 看片质检、参考视频拆解 |
| `OPENAI_API_KEY`（可选 `OPENAI_BASE_URL`） | 参考视频转写 |

## 目录：代码在仓库，素材在工作区

```text
explainer-studio/                 ← 本仓库，只有代码、模板和 skill
├── bin/studio                    统一入口
├── studio/
│   ├── avatar/                   竖屏口播：tools/*.py + engine/（Canvas 渲染引擎）
│   ├── cut/                      录屏剪辑
│   ├── refs/                     参考视频库
│   └── common/                   配置、密钥、fal 调用
├── skills/                       给 Agent 的判断规则（软链到 ~/.claude/skills、~/.codex/skills）
├── examples/                     专题示例
└── config.example.toml

<工作区>/                         ← config.toml 的 paths.workspace，不进仓库
├── references/                   参考视频库：creators/ saved/ analysis/ jobs.tsv
├── projects/<专题>/              每条片子一个目录：topic.json script/ scenes.js assets/ work/ out/
└── me/                           本人素材：克隆好的声音等
```

## 做一条竖屏口播

```bash
studio avatar init <工作区>/projects/my-topic && cd <工作区>/projects/my-topic
# 1. 写 script/script.json：每句 show（字幕）和 say（给配音读的写法）
# 2. 照 scenes.js 模板给每句写画面，动画挂在词上：at('词', '句id') 返回这个词开口的时刻
studio avatar voice          # 配音 + 转写 + 逐字对齐
studio avatar driver && studio avatar lipsync     # 对口型，2 分钟片约 10–15 分钟
studio avatar prep && studio avatar stills 3 9.5 20   # 出静帧检查版式
studio avatar bgm && studio avatar build              # 配乐 + 渲染 + 混音 -> out/
studio avatar qc out/my-topic.mp4 r1                  # Gemini 看片打分
```

`examples/h3-five-parts/` 是一条完整的 2 分钟片（拆解开源视频生成模型 H3 的五个零件）的脚本和全部画面代码，
可以当写法参考；录像、示意图和视频截帧素材不随仓库分发。`examples/minimal/` 是 `init` 生成的空骨架。

## 拆参考视频

```bash
studio refs fetch https://www.douyin.com/user/<sec_uid> --limit 10   # 抓博主最近 10 条
studio refs jobs                  # 新视频补进 jobs.tsv，检查 slug/分组
studio refs run                   # 转写 → 切镜 → 指标 → Gemini 拆解（已有结果跳过）
studio refs report                # 按分组看语速、切镜频率、字幕长度、开场钩子
```

抓取只用于个人学习拆解：不转载、不二次分发原视频，遵守平台条款，引用画面注明作者。

## Agent skills

| skill | 什么时候用 |
| --- | --- |
| [avatar-explainer-video](skills/avatar-explainer-video/SKILL.md) | 做竖屏口播讲解（本人小窗 + 信息图） |
| [lecture-video-cut](skills/lecture-video-cut/SKILL.md) | 剪录屏讲课 |
| [reference-study](skills/reference-study/SKILL.md) | 拆别的博主的视频 |

```bash
for s in skills/*/; do ln -s "$PWD/$s" ~/.claude/skills/; ln -s "$PWD/$s" ~/.codex/skills/; done
```

## 费用参考

2 分钟竖屏口播一条约 15–20 美元：对口型 HeyGen 约 0.1 美元/秒是大头，配音和配乐各几美元。
`studio avatar clone` 只在第一次克隆声音时花钱，结果写进 config 的 `[me] voice_clone_result` 复用。

## 许可

代码 MIT（见 [LICENSE](LICENSE)）。`studio setup` 下载的字体来自 Fontsource，各自 SIL Open Font License。
