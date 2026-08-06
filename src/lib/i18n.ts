/**
 * Vynaro v1.0.0 · 全量双语 (i18n) 字典与翻译函数
 */

export type Locale = "zh-CN" | "en-US";

export const TRANSLATIONS: Record<Locale, Record<string, string>> = {
  "zh-CN": {
    // 基础导航
    "nav.home": "工作台",
    "nav.production": "制作流水线",
    "nav.assets": "项目管理",
    "nav.settings": "设置",

    // 顶栏
    "topbar.help": "帮助与支持",
    "topbar.docs": "官方文档",
    "topbar.about": "关于 Vynaro",
    "topbar.search_placeholder": "搜索",
    "topbar.search_title": "打开命令面板 ⌘K",
    "topbar.connected": "已连接",
    "topbar.disconnected": "未连接",

    // 常用动作
    "action.save": "保存",
    "action.cancel": "取消",
    "action.create": "新建空白项目",
    "action.import": "导入素材",
    "action.delete": "删除",
    "action.start": "启动 7 步流水线",

    // 项目管理页
    "assets.title": "项目管理",
    "assets.subtitle": "管理项目、媒体、脚本与导出",
    "assets.recent": "最近的项目",
    "assets.recent_subtitle": "最多保留 20 条",
    "assets.no_project": "还没有项目",
    "assets.create_now": "立即创建",
    "assets.batch_import": "批量扫描导入",
    "assets.delete_confirm": "确认删除此项目？",

    // 设置页
    "settings.title": "应用设置",
    "settings.subtitle": "配置大语言模型 (LLM)、TTS 语音引擎与系统偏好",
    "settings.language": "界面语言 (Language)",
    "settings.theme": "外观与语言",
    "settings.saved": "✓ 设置已保存",
    "settings.llm_section": "大语言模型",
    "settings.tts_section": "语音合成引擎",

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
    "nav.assets": "Projects",
    "nav.settings": "Settings",

    // TopBar
    "topbar.help": "Help & Support",
    "topbar.docs": "Documentation",
    "topbar.about": "About Vynaro",
    "topbar.search_placeholder": "Search",
    "topbar.search_title": "Open Command Palette ⌘K",
    "topbar.connected": "Connected",
    "topbar.disconnected": "Disconnected",

    // Actions
    "action.save": "Save",
    "action.cancel": "Cancel",
    "action.create": "New Project",
    "action.import": "Import Media",
    "action.delete": "Delete",
    "action.start": "Start 7-Step Pipeline",

    // Projects Page
    "assets.title": "Project Management",
    "assets.subtitle": "Manage projects, media assets, scripts and exports",
    "assets.recent": "Recent Projects",
    "assets.recent_subtitle": "Up to 20 recent records",
    "assets.no_project": "No Active Project",
    "assets.create_now": "Create Now",
    "assets.batch_import": "Batch Directory Scan",
    "assets.delete_confirm": "Confirm delete project?",

    // Settings Page
    "settings.title": "Application Settings",
    "settings.subtitle": "Configure LLM Providers, TTS Engines, and System Preferences",
    "settings.language": "Interface Language",
    "settings.theme": "Appearance & Language",
    "settings.saved": "✓ Settings Saved",
    "settings.llm_section": "Large Language Models",
    "settings.tts_section": "TTS Synthesis Engines",

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
