# 计划格式 v1

JSON 使用 UTF-8。`schema_version` 为 1；`project` 包含 name、scene、width、height、fps，可附 audience、goal、platform。尺寸必须为 2–8192 内偶数；fps 可写 `30` 或 `30000/1001`。原生适配器暂限整数 fps。

`media` 来自 inventory，再补来源日期、credit 与 rights；不要以改元数据的方式绕过时长或过期校验。路径相对 `--media-root`，禁止盘符绝对路径、越界或指向根外的符号链接。迁移机器只改素材根目录并重新盘点核对，不改原始文件。mtime/大小变化要求复核，它们不代替内容哈希或身份鉴定。

`clips` 为顺序连续的主画面数组：id、media_id、start_frame、in_frame（默认0）、duration_frames、fit（contain/cover）、volume（默认1），可附 purpose 与 caption_note。所有帧值以项目 fps 为时间单位，源视频本身帧率可以不同。in_frame 表示源入点的时间，不是原视频第几个解码帧。静态图片 in_frame 为0，持续时长由计划指定。

`titles` 每项 text、start_frame、duration_frames；当前统一为底部居中白字，不支持自定义字号位置。重叠标题会叠放，需人工检查。`audio` 每项 media_id、start_frame、in_frame、duration_frames、volume、role（music/dialogue/ambient/effect），只引用独立音频文件，可重叠混音；没有自动闪避或峰值响度保证。需要侧链或 J/L cut 请用支持的后端。

未知字段作为错误，不能把 transition、speed、crop 或 keyframes 填进计划并期待被忽略。v1 不是任意剪映效果的完整表达。可把复杂布局预合成为新媒体，再在原生编辑中保留外层字幕与音轨；交付说明哪些元素已烘焙。

机器校验：连续主画面、源区间、正整数帧、标题/音轨边界、媒体存在与范围、尺寸、重复ID和不支持字段。不验证视觉内容、对白语义、实际听感、权利或剪映兼容性。旋转元数据与非方形像素先规范成代理再盘点，避免两后端方向不同。

修改建议使用“成片时间＋问题＋预期结果”。可在 notes 记录音乐候选点、步骤依赖与来源；notes 不自动执行。源区间转微秒时，从起止帧分别计算后相减，避免累计舍入误差。
