# explainer-studio 仓库约定

> 适用范围：本仓库全部内容。各模块怎么用见 `skills/*/SKILL.md`，本文件只管仓库本身。

## 一、代码和素材分开

- 仓库里只放代码、模板、skill 和示例。成片、录像、配音、参考视频、转写结果、缓存一律放工作区
  （`~/.config/explainer-studio/config.toml` 的 `paths.workspace`）。
- 代码里**不写任何本机绝对路径**。路径、密钥、个人素材都从 `studio/common/config.py` 读；新增配置项先加进
  `config.example.toml` 并写注释。
- 能力放脚本，skill 只放判断：新功能先做成 `studio <模块> <命令>`，再在对应 `SKILL.md` 写什么时候用、怎么判断。

## 二、公开仓库的脱敏纪律

本仓库是 **public**。提交前确认新增内容不含：

- 本机绝对路径（`/Users/...`）、真实邮箱、手机号；
- 内部项目代号、公司内部系统名；
- 任何密钥、token、内网地址；
- 未授权分发的素材：本人录像、克隆声音、第三方视频和截帧、来源不明的图片。

提交前自查：

```bash
grep -rniE "/Users/|@[a-z0-9-]+\.(com|cn)|sk-[a-z0-9]{8}|api[_-]?key\s*=\s*['\"][^'\"]" . --exclude-dir=.git
```

Git 身份只用个人 noreply 邮箱，仓库级配置，不加 `--global`。

## 三、改动后怎么验

| 改了什么 | 至少跑 |
| --- | --- |
| `studio/avatar/` | 在一个已有专题目录 `studio avatar stills <秒…>`，看静帧 |
| `studio/refs/` | `studio refs report` |
| `studio/motion/` | `studio motion init` 一个临时目录，`preview` 出总览图，`render --dur 1` 出片 |
| `studio/common/config.py` | `studio setup` |

## 四、对外动作停点

`git push`、改仓库可见性、建 Release、加协作者都是对外动作，执行前先问一次。
