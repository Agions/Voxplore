"""中文内置帮助条目。

每条 entry 是一个 ``HelpTopic`` 实例。
"""

from __future__ import annotations

from ..models import HelpTopic

__all__ = ["TOPICS"]


def _topic(
    topic_id: str,
    title: str,
    body: str,
    *,
    category: str,
    summary: str = "",
    tags: tuple[str, ...] = (),
) -> HelpTopic:
    return HelpTopic(
        id=topic_id,
        title=title,
        category=category,
        summary=summary,
        source="built-in:zh_CN",
        tags=tags,
        body=body,
    )


TOPICS: list[HelpTopic] = [
    # ─────────────── 快捷键 ───────────────
    _topic(
        topic_id="shortcut.command-palette",
        title="命令面板（Cmd+K / Ctrl+K）",
        category="shortcut",
        summary="全局搜索命令、跳转页面、切换主题与语言。",
        tags=("快捷键", "命令面板", "搜索", "command", "palette"),
        body=(
            "按 **Cmd+K**（macOS）或 **Ctrl+K**（Windows / Linux）打开命令面板。\n\n"
            "- 输入关键字模糊匹配命令（导航 / 视图 / 设置 / 帮助）。\n"
            "- 上下方向键切换，Enter 执行，Esc 关闭。\n"
            "- 输入 `帮助` 或 `help` 可直接打开帮助面板。"
        ),
    ),
    _topic(
        topic_id="shortcut.toggle-theme",
        title="切换主题（tech-dark / dark / light）",
        category="shortcut",
        summary="命令面板搜索「主题」或在状态栏点切换按钮。",
        tags=("快捷键", "主题", "切换", "theme"),
        body=(
            "在命令面板输入 `主题` / `theme`，回车即可在 tech-dark / dark / light 之间循环切换。\n\n"
            "主题状态会立即持久化到 QSettings，下次启动自动还原。"
        ),
    ),
    _topic(
        topic_id="shortcut.help-panel",
        title="打开帮助面板（F1）",
        category="shortcut",
        summary="抽屉式帮助：左侧目录、右侧全文搜索。",
        tags=("快捷键", "帮助", "F1", "help"),
        body=(
            "按 **F1** 或在命令面板输入 `帮助`，会从主窗口右侧滑出 HelpPanel。\n\n"
            "面板顶部为搜索框，输入关键字即时过滤；下方左侧是分类目录树，点击 topic 在右侧渲染 markdown 内容。"
        ),
    ),
    _topic(
        topic_id="shortcut.run-pipeline",
        title="启动生产任务（Ctrl+R）",
        category="shortcut",
        summary="在当前项目页按 Ctrl+R 直接启动流水线。",
        tags=("快捷键", "流水线", "运行", "run", "pipeline"),
        body=(
            "在「新建项目」或「批量生产」页面按 **Ctrl+R**（macOS 为 Cmd+R）可一键启动当前选中的流水线。\n\n"
            "运行期间实时进度会同步推送到 Dashboard 的「实时任务」卡片。"
        ),
    ),
    _topic(
        topic_id="shortcut.navigate",
        title="导航快捷键（Alt+1~5）",
        category="shortcut",
        summary="Alt+数字键 快速切换顶部导航。",
        tags=("快捷键", "导航", "navigate"),
        body=(
            "- **Alt+1** — Dashboard 首页\n"
            "- **Alt+2** — 新建项目\n"
            "- **Alt+3** — 素材库\n"
            "- **Alt+4** — 批量生产\n"
            "- **Alt+5** — 设置"
        ),
    ),
    # ─────────────── FAQ ───────────────
    _topic(
        topic_id="faq.first-launch",
        title="首次启动要做哪些事？",
        category="faq",
        summary="安装 → 配置 AI Key → 导入素材 → 启动流水线。",
        tags=("首次启动", "入门", "new", "first"),
        body=(
            "1. **安装 FFmpeg**：参考 `docs/guide/installation.md` 中对应的操作系统章节。\n"
            "2. **配置 AI 服务**：至少设置一个 LLM Key（DeepSeek / Qwen）；在「设置 → AI 配置」或 `config/llm.yaml` 中维护。\n"
            "3. **导入素材**：在「素材库」拖入视频文件，等待场景分析。\n"
            "4. **新建项目**：选择模板，填入解说词主题，运行流水线。\n\n"
            "首次启动会自动弹出 5 步新手引导（可在设置中重置）。"
        ),
    ),
    _topic(
        topic_id="faq.api-key",
        title="API Key 在哪里配置？",
        category="faq",
        summary="环境变量优先，其次 config/llm.yaml，最后设置页。",
        tags=("api", "key", "配置", "环境变量"),
        body=(
            "支持三层配置（按优先级降序）：\n\n"
            "1. **环境变量**：``DEEPSEEK_API_KEY``、``QWEN_API_KEY``、``OPENAI_API_KEY`` 等。\n"
            "2. **配置文件**：``config/llm.yaml`` 的 ``providers.*.api_key`` 字段。\n"
            "3. **GUI 设置页**：「设置 → AI 配置」表单（自动加密落盘）。\n\n"
            "API Key 任何时候都**不会**以明文形式出现在日志或界面 tooltip 中。"
        ),
    ),
    _topic(
        topic_id="faq.video-analysis-slow",
        title="视频分析太慢怎么办？",
        category="faq",
        summary="降抽帧频率 / 切段 / 选更快模型。",
        tags=("性能", "视频分析", "慢", "slow", "performance"),
        body=(
            "长视频（>30 分钟）分析通常耗时较长，可从以下三方面优化：\n\n"
            "- **抽帧频率**：在「项目设置 → 视频分析」中把帧间隔从 1fps 调高到 2fps。\n"
            "- **分段处理**：在 Dashboard 中拆分长视频为多个片段并行处理。\n"
            "- **模型选择**：把默认的 `qwen-vl-plus` 切换为 `qwen-vl-turbo` 或本地 Ollama。"
        ),
    ),
    _topic(
        topic_id="faq.export-platform",
        title="如何导出到抖音 / B站 / YouTube？",
        category="faq",
        summary="在导出页选择平台预设，自动套用码率与字幕格式。",
        tags=("导出", "平台", "抖音", "B站", "YouTube", "export"),
        body=(
            "「导出发布」页内置 8 个平台预设（抖音 / B站 / YouTube / TikTok / 视频号 / 小红书 / Instagram / Twitter），每个预设自动设定：\n\n"
            "- 视频分辨率与码率（H.264 / H.265）\n"
            "- 字幕格式与字体（ASS / SRT）\n"
            "- 音频采样率（44.1kHz / 48kHz）\n\n"
            "选择预设后点「开始导出」即可。生成 `.draft.json` 后可直接导入剪映二次精剪。"
        ),
    ),
    _topic(
        topic_id="faq.subtitle-out-of-sync",
        title="字幕和配音对不上？",
        category="faq",
        summary="检查音频采样率 / 重新生成字幕 / 切到 ASS 格式。",
        tags=("字幕", "同步", "配音", "subtitle"),
        body=(
            "常见原因与处理：\n\n"
            "1. 音频采样率不是 44100Hz → 在「项目设置」改成 44100Hz 后重新生成。\n"
            "2. 手动编辑过字幕时间轴 → 删掉手改段落，重新生成。\n"
            "3. 导出 SRT 丢失样式 → 改用 ASS 格式保留字体与位置信息。"
        ),
    ),
    _topic(
        topic_id="faq.update",
        title="如何升级到最新版本？",
        category="faq",
        summary="命令面板搜索「检查更新」或左侧导航「升级」。",
        tags=("升级", "更新", "update"),
        body=(
            "升级路径：\n\n"
            "- GUI：左侧导航 → 「升级」，点「检查更新」。\n"
            "- 命令面板：Cmd+K → 输入 `更新`。\n"
            "- CLI：``scenefab --update``。\n\n"
            "升级采用增量 + SHA256 校验，失败自动回滚到上一个稳定版本。"
        ),
    ),
    _topic(
        topic_id="faq.privacy",
        title="我的素材会上传云端吗？",
        category="faq",
        summary="默认本地优先，仅 AI 调用必须联网。",
        tags=("隐私", "本地", "上传", "privacy"),
        body=(
            "SceneFab 严格**本地优先**：\n\n"
            "- 视频素材、生成的解说稿、字幕、配音全程在本地落盘。\n"
            "- 仅在调用 AI 服务时（解说生成、视频语义分析、配音合成）才会向对应服务商发送必要数据。\n"
            "- 可选 Edge-TTS 本地缓存、F5-TTS 离线模式，做到「完全离线」运行。\n\n"
            "在「设置 → 隐私」可看到具体的网络出口清单。"
        ),
    ),
    # ─────────────── Onboarding ───────────────
    _topic(
        topic_id="onboarding.welcome",
        title="欢迎使用 SceneFab",
        category="onboarding",
        summary="5 步完成首次成功生产。",
        tags=("onboarding", "欢迎", "welcome"),
        body=(
            "欢迎使用 SceneFab！下面 5 步能带你完成首次成功生产。\n\n"
            "随时可以按 **Esc** 跳过；之后在「设置 → 帮助」中重新开启。"
        ),
    ),
    _topic(
        topic_id="onboarding.layout",
        title="整体布局介绍",
        category="onboarding",
        summary="顶部导航 + Dashboard + 监控 + 快捷操作。",
        tags=("onboarding", "布局", "layout"),
        body=(
            "主窗口主要分四个区域：\n\n"
            "1. **顶部导航**：切换 Dashboard / 项目 / 素材 / 批量生产 / 设置。\n"
            "2. **Dashboard**：左侧 4 个 KPI 卡片，右侧实时监控与快捷操作。\n"
            "3. **状态栏**：CPU / 内存 / 磁盘实时占用 + 主题切换 + 语言切换。\n"
            "4. **命令面板**：按 **Cmd+K** 随时呼出。"
        ),
    ),
    _topic(
        topic_id="onboarding.drag-video",
        title="导入第一段视频",
        category="onboarding",
        summary="把本地视频拖到素材库，开始场景分析。",
        tags=("onboarding", "视频", "导入"),
        body=(
            "操作步骤：\n\n"
            "1. 在左侧导航进入「素材库」。\n"
            "2. 直接把 `.mp4` / `.mkv` / `.mov` 拖入空白区。\n"
            "3. 等待场景分析完成（时长约等于视频时长的 1/3）。\n"
            "4. 在 Dashboard 上能看到「最近素材」实时更新。"
        ),
    ),
    _topic(
        topic_id="onboarding.configure-ai",
        title="配置 AI 提供商",
        category="onboarding",
        summary="至少设置一个 LLM Key 才能启动流水线。",
        tags=("onboarding", "AI", "配置"),
        body=(
            "AI 服务配置路径：「设置 → AI 配置」或编辑 ``config/llm.yaml``。\n\n"
            "- **DeepSeek** — 解说稿生成（性价比最高）。\n"
            "- **Qwen / OpenAI** — 视频语义分析（多模态）。\n"
            "- **Edge-TTS / F5-TTS** — 配音合成（Edge 免费，F5 可选克隆）。"
        ),
    ),
    _topic(
        topic_id="onboarding.run-pipeline",
        title="启动你的第一次生产",
        category="onboarding",
        summary="选择模板 → 启动 → 在 Dashboard 看实时进度。",
        tags=("onboarding", "流水线", "启动"),
        body=(
            "建议路径：\n\n"
            "1. 「新建项目」→ 选择「解说稿」模板。\n"
            "2. 选一段刚才导入的视频 + 一段提示词。\n"
            "3. 按 **Ctrl+R** 启动。\n"
            "4. 切到 Dashboard，「实时任务」卡片会显示分步骤进度。"
        ),
    ),
]
