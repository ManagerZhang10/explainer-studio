---
name: kexue-video
description: 将中文技术讲义中的单一知识点做成 120–180 秒讲解视频，包含事实审核、初学者例子、大字简图逐步动画、远端 AI 配音、句级字幕与成片质检。用于讲义转视频、科普动画和逐章出片；支持现有 VLM 14 章及手工脚本驱动的独立新文档项目。
---

# 中文技术讲解视频

交付让初学者能复述一个核心机制的横屏视频：大字、简图、逐步解释、当前单句字幕，120–180 秒。实拍剪辑不走本流程。

skill 源在 explainer-studio 仓库 `skills/kexue-video`，各 Agent 的 skills 目录软链过去。

执行入口是 `studio lecture`：`draft`、`render`、`audit`、`batch`、`verify` 转发到仓库 `studio/lecture/` 的配套脚本；不带参数运行查看子命令。脚本参数与下列 Python 命令相同。讲义、幻灯片和出片目录都取 config.toml 的 `[lecture]` 段。

## 判断入口

- 已有课程：讲义目录 `[lecture] course_docs` 有 14 份 `dayNN.md`，幻灯片目录 `[lecture] course_slides` 有 14 个 `parts/*_dayNN.html`（作者自己的 VLM 14 天课程 Track A）。DAY 是 1–14。
- 新文档：先读 [新资料接入](references/新资料接入.md)。Agent 按新 doc 手工构造并审核 JSON，所有 scene 都有 visual 时，用 --script 和 --project-dir 在独立项目出片，无需 VLM deck 或图片。gen_script 仍依赖课程，不接受任意 doc；混合原页模式仍依赖课程资源。

## 制作顺序

1. **选一个问题**：写清观众已知什么、看完能回答什么。选支持该答案的页，形成“问题 → 具体例子 → 机制 → 边界”，不用章节目录代替知识点。
2. **生成并审口播**：课程用生成器，新 doc 由 Agent 按 schema 构稿。读 [口播稿规范](references/口播稿规范.md)，逐条核实数字、模型名、因果和比较。至少一个初学者能跟随的输入到输出例子。字数通过不代表事实通过。
3. **设计简图**：给场景补 `scene.visual`，短标签、2–5 个 nodes，links 表达真实方向和关系；节点可用实际口播短语 `cue` 驱动 reveal。读 [动画与字幕实现](references/动画与字幕实现.md)，明确句级 marks 的近似边界。
4. **声音和页面**：远端 AI 配音；HTML 阶段也会请求未缓存的声音。先审离线页面、箭头、字幕及暂停 WAAPI 的 seek 确定性，再渲染。
5. **验收**：实际音频时间轴必须 120–180 秒；超限改稿再合成，不硬拉伸音画。检查成片轨道、分辨率、字幕同步和末段完整图，交付实际路径及未通过项。

## 已有 14 章的真实命令

在同一 shell 中设置 DAY，例如第一章：

```bash
cd <explainer-studio 仓库>/studio/lecture
DAY=1
python3 gen_script.py "$DAY"
```

先审核 `work/scripts/day01.json`，补 visual 和 cue，再继续：

```bash
python3 build_video.py "$DAY" --html
python3 audit_pages.py "$DAY"
python3 build_video.py "$DAY" --scale 0.6666666667
```

不要在人工补完 visual 后再次生成脚本，它会覆盖修改。不要用 Python 执行 .sh。

上述 work/out 相对 config 的 `[lecture] project`：
- 脚本：`work/scripts/dayNN.json`。
- 页面及导出：`work/video/dayNN/page.html`、`timeline.json`、`captions.srt`，合并声音在其 `audio/voice.wav`。
- 审核：`work/qc/repaired/audit.json`、`dayNN_contact.png`。发现页面错误、确定性失败或观察异常时退出 1；每次会覆盖报告。
- 正式片：`out/dayNN_标题.mp4`，以构建器返回路径为准。

## 运行约束

- 本机 CPU 只负责浏览器渲染、图片和 ffmpeg 媒体处理；语言生成、AI 声音和需要时的转录走远端，不运行本地 AI 模型，也不宣称“无 CPU”。
- **重渲染最多 2 路并行**，包含页面 audit。同 DAY 从改稿、HTML 到 audit、render 串行。ffmpeg 的 threads 2 不是全机 CPU 上限。
- 构建持有 `work/locks/dayNN.lock` 非阻塞 daylock；gen_script 和 audit 不持锁，调度须避免同章读写冲突。锁冲突等原任务退出，不删锁绕过。
- 实际声音合成后的 total 在 render 前检查 120–180 秒，超限抛错；改稿重建，不能用拉伸绕过。
- atomicmp4：先编码到 `out/.dayNN.partial.mp4`，成功后 `os.replace` 原子替换正式片。失败不把 partial 当交付。
- 页面离线：全 visual 模式内置 BASE_CSS/MARKERS/VISUAL_RUNTIME，不读取 VLM deck 或图片；混合原页模式只自动处理特定 media/ 属性，不能假定所有外链已处理。两种模式都检查字体和 marker。
- 全部 WAAPI 创建后 pause；每帧 seek 设置场景内毫秒 currentTime 再截图，不能靠墙钟播放。

## 验收门禁

- 一个知识点，例子讲得通，图和口播无事实冲突；links 不缺边、不误导。
- 常规字幕块目标 ≤16 字符，当前只有一块可见；完整英文及长括号允许超限，实查宽度，不能拆词凑数。
- audit 中 errors 空、deterministic true，observations 无越界、空动态箭头、坏图、字幕越界和 running animations；另人工看静态 link、marker、遮挡与末帧。
- timeline 的 caps 与 reveal_times 对得上实际口播，cue 匹配不到的等分近似须抽听检查，不称逐字精确对齐。
- 用 ffmpeg -hide_banner -i 检查 1280×720、30 fps、120–180 秒、H.264/AAC 轨道，再完整解码；试听开头、中段、结尾，无漂移。

## 独立新 doc 命令

Agent 按来源构造 `/tmp/new.json`，所有 scenes 有 visual，slide 记录来源（可重复）；渲染按每场独立 slot，timeline.source_slide 保留原来源。补 series/question/next_title/next_hint；next_title 非空，避免回退课程尾卡。`/tmp` 是演示路径，正式产物用实际项目目录。

```bash
python3 build_video.py 1 --script /tmp/new.json --project-dir /tmp/demo --html
python3 audit_pages.py 1 --project-dir /tmp/demo
python3 build_video.py 1 --script /tmp/new.json --project-dir /tmp/demo --scale 0.6666666667
```

在 pipeline 目录执行。day 可省略，默认 1；项目产物位于 `/tmp/demo/work/` 和 `/tmp/demo/out/`，不修改硬编码。HTML 之后先审核页面及 timeline/SRT，audit 通过后才渲染。audit 的报告与联系表写入该项目 work/qc/repaired/；显式传 1，省略 days 会默认检查 1–14。脚本失败退出 1，但通过仍不代替事实、静态箭头语义和试听审核。

## 课程批量生产与交付索引

以下都在 pipeline 目录运行，只支持默认课程目录，不接受独立项目参数；先完成 14 章脚本事实审核，再批量准备、审核和渲染：

```bash
python3 run_batch.py --prepare --workers 2 --days 1 2 3
python3 audit_pages.py 1 2 3
python3 run_batch.py --workers 2 --days 1 2 3
```

省略 --days 则处理 1–14。run_batch 固定 scale=2/3，workers 只能 1 或 2，记录脚本 SHA256，改稿导致失败；输出 work/prepare_report.json 或 render_report.json，有失败退出非零。prepare 也可能请求配音。审查 audit 后才渲染，不把报告写出当质量通过。

完整 14 章出片后：

```bash
python3 verify_delivery.py
python3 write_index.py
```

verify_delivery 检查 14 章目标文件、H.264/AAC、720p/30fps、时长、完整解码、timeline 时差及全场景 visual，写 work/verify.json，失败非零。通过后运行 write_index，生成项目 README.md 和 review.html。索引记录实际存在文件及核验状态，不代表人工事实/视觉审核通过；write_index 本身不是质量门禁。详见 [制作参数表](references/制作参数表.md)。

## 按需参考

- [制作参数表](references/制作参数表.md)：当前默认值、样本动态统计及证据边界。
- [口播稿规范](references/口播稿规范.md)：选点、例子、事实审核、脚本 schema。
- [动画与字幕实现](references/动画与字幕实现.md)：visual/cue、句级 marks、reveal_times、离线与逐帧。
- [新资料接入](references/新资料接入.md)：可配置路径合同与当前限制。
- [失败案例](references/失败案例.md)：缓存、锁、原子输出及恢复。
