/**
 * splicr v1.0.0 · 全量双语 (i18n) 字典与翻译函数
 */

export type Locale = "zh-CN" | "en-US";

export const TRANSLATIONS: Record<Locale, Record<string, string>> = {
  "zh-CN": {
    // 基础导航
    "nav.home": "工作台",
    "nav.production": "制作流水线",
    "nav.assets": "项目管理",
    "nav.settings": "大模型与引擎中心",
    "nav.help": "帮助中心",

    // 顶栏
    "topbar.help": "帮助与支持",
    "topbar.docs": "官方文档",
    "topbar.about": "关于 splicr",
    "topbar.search_placeholder": "搜索全域命令与解说工程...",
    "topbar.search_title": "打开命令面板 ⌘K",
    "topbar.connected": "已连接",
    "topbar.disconnected": "未连接",

    // 常用动作
    "action.save": "保存设置",
    "action.cancel": "取消",
    "action.create": "新建解说工程",
    "action.import": "批量素材扫描",
    "action.delete": "删除工程",
    "action.start": "启动 7 步全自动流水线",
    "action.stop": "终止 / 取消流水线",
    "action.enter": "进入制作工作台 →",

    // 首页 Dashboard
    "home.welcome_title": "splicr 叙影 AI 视频叙事工作室",
    "home.welcome_subtitle": "打造下一部爆款电影级短剧与影视解说作品 · 7 步全自动 AI 极速流水线",
    "home.recent_title": "最近视频解说工程",
    "home.see_all": "查看资产库 →",
    "home.no_project": "暂无历史解说工程",
    "home.no_project_sub": "点击下方按钮快速建立第一个 7 步 AI 短剧/影视解说工程",
    "home.create_project": "➕ 新建解说工程",
    "home.project_file_tag": "工程文件 · 本地极速处理",
    "home.pipeline_title": "7 步 AI 叙事工作流",
    "home.quick_actions": "快捷控制中心",
    "home.action_new": "新建解说工程",
    "home.action_scan": "批量目录扫描",
    "home.action_settings": "引擎与 API 配置",
    "home.action_help": "使用教程与指南",

    // 项目管理页
    "assets.title": "项目与资产中心",
    "assets.subtitle": "管理解说工程、高清媒体素材、AI 脚本与渲染导出库",
    "assets.stat_projects": "解说工程总数",
    "assets.stat_media": "视频与音频素材",
    "assets.stat_scripts": "AI 叙事脚本",
    "assets.stat_renders": "已导出解说草稿",
    "assets.recent": "历史解说工程",
    "assets.recent_subtitle": "按最后编辑时间倒序排列",
    "assets.no_project": "暂无活动解说工程",
    "assets.create_now": "立即新建工程",
    "assets.batch_import": "批量目录扫描",
    "assets.single_import": "📥 导入视频素材",
    "assets.search_placeholder": "🔎 搜索媒体文件名...",
    "assets.delete_confirm": "确认删除此工程？",
    "assets.media_list_title": "当前工程媒体素材库",

    // 设置页 (大模型与引擎中心)
    "settings.title": "大模型与引擎中心",
    "settings.subtitle": "配置 11 大 AI LLM 大模型 Key、TTS 语音合成引擎与 FFmpeg 渲染路径",
    "settings.tab_llm": "🤖 大语言模型 (LLM)",
    "settings.tab_tts": "🎙️ TTS 语音合成",
    "settings.tab_ffmpeg": "⚙️ FFmpeg 渲染引擎",
    "settings.tab_appearance": "🎨 主题与语言",
    "settings.language": "界面语言 (Language)",
    "settings.theme": "显示主题",
    "settings.saved": "✓ 设置已同步保存",
    "settings.llm_provider": "大模型 AI 供应商",
    "settings.api_key": "API 密钥 (API Key)",
    "settings.base_url": "自定 Base URL (可选)",
    "settings.model_name": "指定 Model 模型标识",
    "settings.tts_engine": "TTS 配音引擎选型",
    "settings.voice_select": "默认发音人",
    "settings.probe_btn": "🔌 测试连通性",
    "settings.probe_ok": "✓ 状态正常",

    // 帮助中心
    "help.title": "帮助中心与教程指南",
    "help.subtitle": "获取 7 步 AI 叙事工作流教程、快捷键指南与常见问题解答",
    "help.search_placeholder": "🔎 搜索主题 (标题/关键词/正文)...",
    "help.all_cat": "全部",
    "help.guide": "教程",
    "help.ref": "参考",
    "help.trouble": "故障排查",
    "help.faq": "FAQ",
    "help.shortcut": "快捷键",
    "help.shortcuts_title": "键盘快捷键指南",
    "help.no_topics": "未查找到相关教程主题",

    // 制作流水线 7 步标题与副标题
    "step.intake.title": "Step 1: 原始视频与素材导入",
    "step.intake.desc": "选择或拖拽本地解说视频，系统将自动进行格式校验与分辨率分析。",
    "step.detect.title": "Step 2: AI 智能拆条与镜头检测",
    "step.detect.desc": "结合 FFmpeg 镜头切换探测算法，精准分割精彩剧情高光切片。",
    "step.script.title": "Step 3: AI 第一人称解说脚本编排",
    "step.script.desc": "以主角第一人称心理视角组织叙事，打造强钩子、高情绪沉浸感的爆款文案。",
    "step.voice.title": "Step 4: TTS 语音合成与人声克隆",
    "step.voice.desc": "多引擎 TTS 自然配音，支持 Edge-TTS 免密钥合成与 GPT-SoVITS 零样本人声克隆。",
    "step.subtitle.title": "Step 5: 智能字幕识别与动态特效",
    "step.subtitle.desc": "基于 VAD 语音端点检测生成精准时间轴字幕，支持花字与双语对照。",
    "step.compose.title": "Step 6: 画面与音频精确对齐",
    "step.compose.desc": "多轨时间轴可视化，智能对齐叙事高潮帧与背景音乐混音比例。",
    "step.export.title": "Step 7: 多平台预设与剪映草稿导出",
    "step.export.desc": "一键导出剪映工程草稿 (.draft) 及各大短视频平台标准分辨率。",

    // Step 4 Voice 专门词条
    "voice.voice_select": "音色选择",
    "voice.preview_title": "配音实时播放与波形",
    "voice.preview_btn": "▶ 试听试样",
    "voice.preview_playing": "▶ 播放中...",
    "voice.preview_ready": "已加载音频",
    "voice.preview_wait": "在当前页面试听音色",
    "voice.engine_label": "TTS 引擎选型",
    "voice.speed_label": "语速",
    "voice.pitch_label": "音调",
    "voice.synthesize_btn": "合成全部配音",
    "voice.next_step": "进入 Step 5: 字幕合成 →",

    // Step 3 Script 专门词条
    "script.prompt_label": "解说创作提示词 (Prompt)",
    "script.style_label": "解说风格",
    "script.regenerate_btn": "重新生成脚本",
    "script.copy_btn": "复制文本",
  },
  "en-US": {
    // Navigation
    "nav.home": "Dashboard",
    "nav.production": "Pipeline",
    "nav.assets": "Assets Hub",
    "nav.settings": "LLM & Engine Center",
    "nav.help": "Help Center",

    // TopBar
    "topbar.help": "Help & Support",
    "topbar.docs": "Documentation",
    "topbar.about": "About splicr",
    "topbar.search_placeholder": "Search commands & projects...",
    "topbar.search_title": "Open Command Palette ⌘K",
    "topbar.connected": "Connected",
    "topbar.disconnected": "Disconnected",

    // Actions
    "action.save": "Save Settings",
    "action.cancel": "Cancel",
    "action.create": "New Narrative Project",
    "action.import": "Batch Scan Import",
    "action.delete": "Delete Project",
    "action.start": "Start 7-Step Pipeline",
    "action.stop": "Cancel / Stop Pipeline",
    "action.enter": "Enter Workbench →",

    // Home Dashboard
    "home.welcome_title": "splicr AI Narrative Video Studio",
    "home.welcome_subtitle": "Create cinematic short drama monologues & video commentary with automated 7-step pipeline",
    "home.recent_title": "Recent Video Projects",
    "home.see_all": "View Assets Hub →",
    "home.no_project": "No Recent Projects",
    "home.no_project_sub": "Click below to create your first 7-step AI narrative project",
    "home.create_project": "➕ New Narrative Project",
    "home.project_file_tag": "Project File · Local Processing",
    "home.pipeline_title": "7-Step AI Narrative Pipeline",
    "home.quick_actions": "Quick Control Center",
    "home.action_new": "New Narrative Project",
    "home.action_scan": "Batch Scan Directory",
    "home.action_settings": "LLM & Engine Config",
    "home.action_help": "Guides & Tutorials",

    // Projects Page
    "assets.title": "Projects & Media Hub",
    "assets.subtitle": "Manage narrative projects, HD media assets, AI scripts and export drafts",
    "assets.stat_projects": "Total Projects",
    "assets.stat_media": "Video & Audio Files",
    "assets.stat_scripts": "AI Narrative Scripts",
    "assets.stat_renders": "Exported Drafts",
    "assets.recent": "Project History",
    "assets.recent_subtitle": "Sorted by last edit time",
    "assets.no_project": "No Active Project",
    "assets.create_now": "Create New Project",
    "assets.batch_import": "Batch Scan Directory",
    "assets.single_import": "📥 Import Media File",
    "assets.search_placeholder": "🔎 Search asset filename...",
    "assets.delete_confirm": "Confirm delete this project?",
    "assets.media_list_title": "Active Project Media Library",

    // Settings Page
    "settings.title": "LLM & Engine Center",
    "settings.subtitle": "Configure 11 LLM Provider Keys, TTS Voice Engines, and FFmpeg Render Paths",
    "settings.tab_llm": "🤖 LLM Providers",
    "settings.tab_tts": "🎙️ TTS Synthesis",
    "settings.tab_ffmpeg": "⚙️ FFmpeg Engine",
    "settings.tab_appearance": "🎨 Theme & Language",
    "settings.language": "Interface Language",
    "settings.theme": "Theme Mode",
    "settings.saved": "✓ Settings Saved",
    "settings.llm_provider": "LLM Provider",
    "settings.api_key": "API Key",
    "settings.base_url": "Custom Base URL (Optional)",
    "settings.model_name": "Model Identifier",
    "settings.tts_engine": "TTS Voice Engine",
    "settings.voice_select": "Default Speaker",
    "settings.probe_btn": "🔌 Test Connectivity",
    "settings.probe_ok": "✓ Operational",

    // Help Center
    "help.title": "Help Center & Tutorials",
    "help.subtitle": "Access 7-step AI narrative workflow guides, shortcuts and troubleshooting FAQs",
    "help.search_placeholder": "🔎 Search tutorials, FAQs or keywords...",
    "help.all_cat": "All",
    "help.guide": "Guides",
    "help.ref": "Reference",
    "help.trouble": "Troubleshooting",
    "help.faq": "FAQ",
    "help.shortcut": "Shortcuts",
    "help.shortcuts_title": "Keyboard Shortcuts",
    "help.no_topics": "No matching help topics found",

    // Pipeline Steps
    "step.intake.title": "Step 1: Raw Video & Media Intake",
    "step.intake.desc": "Import local video assets for format validation and resolution analysis.",
    "step.detect.title": "Step 2: Scene Cut & Highlight Detection",
    "step.detect.desc": "FFmpeg-based scene transition detection for keyframe highlight extraction.",
    "step.script.title": "Step 3: AI Monologue Script Writing",
    "step.script.desc": "Craft first-person perspective narrative scripts with high emotional hooks.",
    "step.voice.title": "Step 4: TTS Voice Synth & Audio Audition",
    "step.voice.desc": "Multi-engine TTS voice synthesis with Edge-TTS and GPT-SoVITS voice cloning.",
    "step.subtitle.title": "Step 5: Subtitle Sync & Karaoke FX",
    "step.subtitle.desc": "VAD endpoint detection for subtitle timing and dynamic word highlighting.",
    "step.compose.title": "Step 6: Timeline Sync & BGM Mixing",
    "step.compose.desc": "Multi-track timeline alignment for video frames and background audio.",
    "step.export.title": "Step 7: Multi-Platform & CapCut Draft Export",
    "step.export.desc": "Export CapCut project drafts (.draft) and multi-platform presets.",

    // Step 4 Voice
    "voice.voice_select": "Voice Selection",
    "voice.preview_title": "In-Place Audition & Waveform",
    "voice.preview_btn": "▶ Audition",
    "voice.preview_playing": "▶ Playing...",
    "voice.preview_ready": "Audio Loaded",
    "voice.preview_wait": "Audition in current page",
    "voice.engine_label": "TTS Engine",
    "voice.speed_label": "Speed",
    "voice.pitch_label": "Pitch",
    "voice.synthesize_btn": "Synthesize Full Audio",
    "voice.next_step": "Proceed to Step 5: Subtitles →",

    // Step 3 Script
    "script.prompt_label": "Creation Prompt",
    "script.style_label": "Narration Style",
    "script.regenerate_btn": "Regenerate Script",
    "script.copy_btn": "Copy Text",
  },
};

export function t(key: string, locale: string = "zh-CN"): string {
  const loc = (locale === "en-US" ? "en-US" : "zh-CN") as Locale;
  return TRANSLATIONS[loc]?.[key] ?? TRANSLATIONS["zh-CN"]?.[key] ?? key;
}
