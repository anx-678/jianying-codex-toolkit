# Codex × 剪映通用剪辑工具包

v0.1.1 · MIT · Python 3.11+

从一个项目的剪辑经验出发，整理成“场景判断＋统一计划＋可执行工具＋原生验收”的工作流。面向活动纪实、产品演示、教程、访谈、品牌与生活混剪；不固定时长、画幅、歌曲或叙事顺序。

## 获取与安装

- [GitHub 仓库](https://github.com/anx-678/jianying-codex-toolkit)
- [版本与下载](https://github.com/anx-678/jianying-codex-toolkit/releases)
- 完整工具包与独立 Skill 包分开发行；校验文件随 Release 提供。

```text
git clone https://github.com/anx-678/jianying-codex-toolkit.git
cd jianying-codex-toolkit
uv sync --locked
uv run python toolkit.py doctor
```

## 先选择使用方式

- 普通使用者：打开 `开始使用.html`，直接把素材目录与目标交给 Codex，按安装好的 Skill 协作，不必先学命令。
- 需要复用的制作者：使用六种场景策略、项目简报和 JSON 计划，逐镜明确源区间、布局、声音与目的。
- 开发者：运行 CLI、测试与合成例子，按后端能力扩展。发布入口见下方仓库与Release。

## 这版已经有的工具

| 命令 | 实际用途 |
| --- | --- |
| profiles | 查看六场景的叙事、声音和连续性建议 |
| doctor | 报告运行环境与可用依赖，不代替剪映兼容检查 |
| init | 按明确画幅、fps 和场景创建空白项目简报与计划 |
| inventory | 只读素材索引；完整元数据使用 ffprobe 或显式选择 pymediainfo |
| validate | 校验时间线、源区间、素材路径、布局和不支持字段 |
| preview | FFmpeg 渲染基础剪辑、布局、标题与声音，生成程序预览 |
| draft | Windows 基础剪映草稿，标题与独立音轨保持原生可编辑 |
| review | 生成离线 HTML 审片单，不自动宣布验收通过 |

核心只用 Python 3.11+ 标准库，预览另需 FFmpeg；Windows 草稿适配器另需锁定依赖。并非全自动剪辑器：语义选片、复杂效果、音乐实际听感、原生导出仍需 Codex 与操作者共同完成。没有自建 MCP 服务，不要求所有第三方工具先装一遍。

## 快速开始

仓库根目录运行；Windows 示例以 PowerShell 为准。Mac/Linux 将 `.venv/Scripts/python.exe` 改为 `.venv/bin/python`，并使用相同参数。

```text
uv sync
uv run python toolkit.py doctor
uv run python toolkit.py profiles
uv run python toolkit.py init --scene interview --name 访谈首剪 --width 1920 --height 1080 --fps 30 --out outputs/interview-v01
uv run python toolkit.py inventory --media-root YOUR_MEDIA --out outputs/media.json --ffprobe YOUR_FFPROBE
```

Windows 已安装 draft 依赖时，也可用 `uv run --extra draft python toolkit.py inventory --media-root YOUR_MEDIA --out outputs/media.json --mediainfo` 复用其元数据读取库；无需再安装 ffprobe。其他系统需自行确认 MediaInfo 动态库可用。

将 inventory 的素材项放入 plan.json 的 media，查看内容后补 clips、titles 和 audio。空白项目会被 validate 拒绝，因为尚未选片，不代表初始化失败。完整示例在 `examples/`；路径占位符应替换，不直接照抄运行。

```text
uv run python toolkit.py validate YOUR_PLAN --media-root YOUR_MEDIA
uv run python toolkit.py preview YOUR_PLAN --media-root YOUR_MEDIA --out outputs/preview-v01.mp4 --ffmpeg YOUR_FFMPEG
uv run python toolkit.py review YOUR_PLAN --media-root YOUR_MEDIA --out outputs/review-v01.html
```

Windows 需要基础原生草稿时先 `uv sync --extra draft`，再运行 `uv run --extra draft python toolkit.py draft YOUR_PLAN --media-root YOUR_MEDIA --out outputs/draft-v01`。每次选择新的输出路径；不覆盖已有工程。草稿保留源文件绝对引用，不能只搬 JSON；原生打开、保存、导出另行验收。分数fps计划暂不进入原生适配器。

## 安装 Skill

Skill 文件夹 `skills/jianying-codex-toolkit` 是自包含的，内含脚本、场景与参考。完整复制到 Codex 用户技能目录下的同名新目录，保留原有技能；如目标已存在先比较版本，不覆盖。常见用户目录为 `~/.codex/skills`，具体按当前环境配置。安装后在新会话确认技能发现情况。

调用示例：

```text
使用 $jianying-codex-toolkit。
素材在【目录】，这是一个【访谈/产品/教程等】视频。
目标观众是【受众】，发在【平台】，交付【画幅与时长范围】。
先看素材，选合适结构，保留必要原声，不套用上次项目的音乐。
先做可审看的小样，再完成计划、预览和适用的剪映草稿。
```

## 开发与验证

```text
uv run python -m unittest discover -s tests -v
uv run python examples/make_demo.py --ffmpeg YOUR_FFMPEG --out demo-generated
uv run python toolkit.py validate demo-generated/interview.json --media-root demo-generated
uv run python toolkit.py preview demo-generated/interview.json --media-root demo-generated --out outputs/interview.mp4 --ffmpeg YOUR_FFMPEG
uv run python tools/build_docs.py
```

例子是自生成测试画面和正弦波，不是客户媒体或正式配乐，不验证真实对白语义与审美。测试记录见 `docs/verification.json`，开发依赖、CI配置与本机真实运行分开说明。

## 目录与扩展

Skill 是决策入口，scripts 是执行核心，assets 是场景和简报，references 是按需知识；examples 是六场景计划与合成生成器，tests 是约束回归，docs 是学习及验证记录。

扩展场景可修改 scenes.json 与相应判断文档。扩展后端应显式声明能力，将统一计划映射到工具参数，保留未支持字段的错误，添加代表性测试。复杂剪映效果、第三方 MCP 和自动导出应独立适配，不把一次旧工程成功扩展为通用兼容承诺。

## 分享范围

不含客户媒体、歌曲、个人路径或第三方程序。原创代码与文档采用 [MIT](LICENSE)，第三方依赖见 [说明](THIRD_PARTY_NOTICES.md)。

贡献、问题反馈和后续维护见 [CONTRIBUTING](CONTRIBUTING.md) 与 [发布流程](docs/releasing.md)。
