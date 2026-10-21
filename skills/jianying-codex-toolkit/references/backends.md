# 后端与平台

| 能力 | 标准库核心 | FFmpeg 预览 | pyJianYingDraft 适配器 | 剪映原生界面 |
| --- | --- | --- | --- | --- |
| 本地盘点/计划校验 | 支持；完整元数据需 ffprobe 或显式 --mediainfo | 消费已验证计划 | 消费同一计划 | 人工核对 |
| 基础连续剪辑 | 计划 | 支持 | 支持 | 支持 |
| contain / cover | 校验策略 | 黑底完整保留 / 居中裁切 | 按画幅缩放 / 居中放大 | 检查实际构图 |
| 原声/独立音轨 | 原声默认1 | 支持，静音源补静音 | 支持 | 实际试听 |
| 标题 | 定时文字 | ASS 烧录 | 原生文本轨 | 可继续改字 |
| 转场/复杂分屏/关键帧 | v1不执行 | 不执行 | 不执行 | 手工或外部可验证后端 |
| 输出 MP4 | 不支持 | 程序预览 | 不支持 | 实际原生导出 |

核心使用 Python 3.11+ 标准库。`inventory --mediainfo` 可显式复用已安装的 pymediainfo（Windows draft 依赖包含它）；其他系统需要其本地动态库可用，不自动安装。Windows、macOS、Linux 可执行核心命令，跨系统行为以各自测试为准。FFmpeg/ffprobe 是外部依赖，不随包分发；preview 需具备 libx264、AAC、subtitles/libass 与可用字体的构建。不能把程序预览当作剪映导出；标题字体、排版与原生工程未必逐像素一致。

原生草稿适配器当前锁定 pyJianYingDraft 0.3.0，在 Windows 可测试。不会自动查找或写入用户剪映草稿首页，不注册工程，不控制鼠标，不自动导出。只写用户指定的全新输出目录，媒体仍为绝对引用；移动工程要保留源媒体并重新链接。先用剪映打开代表小样，检查画幅、字幕、原声、保存重开和导出，再用于正式项目。当前运行的剪映版本需单独记录，旧项目成功不证明本次适配器的新草稿已经打开。

Mac 可先执行盘点、计划、校验、审片单与 FFmpeg 预览。当前草稿适配器对非 Windows 显式拒绝；不把 Windows 的依赖锁或应用控制当成 Mac 支持。

可选研究接入，未捆绑、未安装、未宣称本包已兼容：

- [pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft)：本包基础草稿后端的外部依赖，新版本及自动导出有自己的限制。
- [jianying-ai-mcp](https://github.com/Xanthus-Sanslab/jianying-ai-mcp)：Windows 素材与草稿工具候选，接入前核对当前能力与基线。
- [jianying-local-mcp](https://github.com/Capricornus-joe/jianying-local-mcp)：Mac 本地候选，按其兼容性与原生导出边界单独验证。

核对日期 2026-10-21。MCP 与 Skill 不是同一层：Skill 决策，CLI/MCP 执行，剪映验证原生结果。接入第三方时通过显式适配器映射并声明可执行字段；不按工具同名猜参数，不静默降级。
