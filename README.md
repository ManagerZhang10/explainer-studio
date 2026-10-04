# explainer-studio

做中文技术讲解短视频的工具箱：拆别人的视频学手法，再用自己的声音和形象，把一个知识点做成逐帧动画讲解。

> A toolkit for making Chinese tech-explainer videos: study reference videos from other creators, then turn one concept into a narrated, frame-by-frame animated explainer with your own cloned voice and lip-synced camera bubble. Everything is driven by one CLI (`studio`) and a set of agent skills (Claude Code / Codex).

## 能做什么

| 模块 | 命令 | 产出 |
| --- | --- | --- |
| 竖屏口播 | `studio avatar …` | 1080×1920 讲解片：克隆声音配音、本人小窗对口型、逐句挂词的 Canvas 信息图、配乐和音效 |
| 录屏剪辑 | `studio cut …` | 录屏讲课（屏幕 / 摄像头 / 麦克风三轨）去气口、删卡壳、逐字字幕、圆形摄像头 |
| 参考视频 | `studio refs …` | 抓博主视频、转写、切镜、算语速和切镜频率、让视觉模型拆开场钩子和画面层 |

每个模块配一个 skill（`skills/`），告诉 Agent 什么时候用、怎么判断好坏；真正干活的都在 `studio/` 的脚本里，裸终端也能直接跑。

## 安装

需要 macOS（Apple 芯片跑 mlx-whisper 对齐；其他平台换任意 whisper，输出同格式 JSON 即可）、Python ≥ 3.11、ffmpeg。

```bash
git clone https://github.com/ManagerZhang10/explainer-studio.git
cd explainer-studio
pip install playwright numpy pillow "opencv-python-headless<5" mlx-whisper certifi
playwright install chromium
ln -s "$PWD/bin/studio" ~/.local/bin/studio        # 任意目录可调用

mkdir -p ~/.config/explainer-studio
cp config.example.toml ~/.config/explainer-studio/config.toml   # 改工作区、密钥文件、本人素材路径
studio setup                                                     # 下载开源字体，检查依赖和密钥
```

国内装不动时：pip 加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`；Chromium 设 `PLAYWRIGHT_DOWNLOAD_HOST=https://registry.npmmirror.com/-/binary/playwright` 再装。

## 选服务：国内一把百炼 key，或海外几家

每个环节用哪家在 `config.toml` 的 `[providers]` 里选，密钥写在 config 指定的 env 文件里（`KEY=VALUE` 一行一个），代码只在内存里读，不落盘、不打印。

| 环节 | 国内（推荐） | 海外 |
| --- | --- | --- |
| 克隆声音 + 配音 | 百炼上的 MiniMax speech-2.8-hd：克隆 9.9 元/次，配音 3.5 元/万字 | fal 上的同一个 MiniMax |
| 对口型 | 百炼 VideoRetalk：0.08 元/秒 | fal 上的 HeyGen：约 0.1 美元/秒，**画质最好** |
| 看片质检、参考视频拆解 | 百炼千问（视觉 / 全模态） | Gemini |
| 参考视频转写 | 百炼 Fun-ASR，或本机 mlx-whisper（免费） | OpenAI whisper |
| 配乐 | 百炼没有：用自己的免版税曲子（`topic.json` 的 `bgm.file`），或不配乐 | fal 上的 ElevenLabs |
| 要的密钥 | 只要 `DASHSCOPE_API_KEY`（阿里云百炼，北京地域） | `FAL_KEY`、`GEMINI_API_KEY` + `GEMINI_BASE_URL`、`OPENAI_API_KEY` |

国内这套直连、人民币付费，2 分钟一条约 10 元；海外这套约 15–20 美元，大头是对口型。
我们并排比过同一段底片：HeyGen 的嘴型最自然；百炼 VideoRetalk 嘴型偏夸张，但便宜、国内能直接用。

百炼上的 MiniMax 配音要先开通：[百炼控制台](https://bailian.console.aliyun.com/) → 模型广场 → 搜 `speech-2.8-hd` → 开通。

## 做数字人口播要准备什么

| 物料 | 要求 |
| --- | --- |
| 一段本人口播录像 | 正常说话、正面、光线稳定，坐远一点露出肩膀和胸口，手不挡嘴。比成片长就行，对口型只改嘴，眨眼和动作都是真的 |
| 同一段录像的音轨 | 单独的麦克风文件或录像自带声音都行；截其中 90 秒干净口播用来克隆声音（只克隆一次） |
| 一张示意图 | 画面里表示「一张图」时用，不要用本人头像；不配就自动生成占位图 |
| 讲稿 | 一篇图文稿，改成逐句的 `script.json`；画面 `scenes.js` 照 `examples/h3-five-parts` 写，建议交给 Claude Code / Codex |

## 目录：代码在仓库，素材在工作区

```text
explainer-studio/                 ← 本仓库，只有代码、模板和 skill
├── bin/studio                    统一入口
├── studio/
│   ├── avatar/                   竖屏口播：tools/*.py + engine/（Canvas 渲染引擎）
│   ├── cut/                      录屏剪辑
│   ├── refs/                     参考视频库
│   └── common/                   配置、密钥、fal / 百炼 / 视觉模型调用
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

2 分钟竖屏口播一条：全走百炼约 10 元；走海外约 15–20 美元，大头是 HeyGen 对口型（约 0.1 美元/秒）。
`studio avatar clone` 只在第一次克隆声音时花钱，结果写进 config 的 `[me] voice_clone_result`（百炼的写 `voice_clone_result_bailian`）复用。

## 许可

代码 MIT（见 [LICENSE](LICENSE)）。`studio setup` 下载的字体来自 Fontsource，各自 SIL Open Font License。
