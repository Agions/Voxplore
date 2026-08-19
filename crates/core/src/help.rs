//! splicr-core · help — 帮助文档与 FAQ 注册表

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum HelpCategory {
    Guide,
    Reference,
    Shortcut,
    Faq,
    Troubleshooting,
}

impl HelpCategory {
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "guide" => Some(Self::Guide),
            "reference" => Some(Self::Reference),
            "shortcut" => Some(Self::Shortcut),
            "faq" => Some(Self::Faq),
            "troubleshooting" => Some(Self::Troubleshooting),
            _ => None,
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Guide => "guide",
            Self::Reference => "reference",
            Self::Shortcut => "shortcut",
            Self::Faq => "faq",
            Self::Troubleshooting => "troubleshooting",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HelpTopic {
    pub id: String,
    pub title: String,
    pub summary: Option<String>,
    pub category: HelpCategory,
    pub keywords: Vec<String>,
    pub content: String,
    pub related: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchHit {
    pub id: String,
    pub topic_id: String,
    pub title: String,
    pub score: u32,
    pub snippet: String,
}

#[derive(Debug, Default)]
pub struct HelpRegistry {
    topics: HashMap<String, HelpTopic>,
}

impl HelpRegistry {
    pub fn new() -> Self {
        Self {
            topics: HashMap::new(),
        }
    }

    pub fn with_defaults() -> Self {
        let mut reg = Self::new();

        // 1. 教程指南 (Guide)
        reg.register(HelpTopic {
            id: "guide-quick-start".into(),
            title: "🚀 第一人称 AI 影视叙事从零上手全流程".into(),
            summary: Some("从素材装载、6 大智能体协同到 AI 配音与字幕精准对齐的全自动化创作指南。".into()),
            category: HelpCategory::Guide,
            keywords: vec!["入门".into(), "快速开始".into(), "工作流".into(), "第一人称".into()],
            content: r#"# 第一人称 AI 影视解说快速上手全流程

splicr 是一款专为全自动第一人称短视频解说打造的桌面级 AI 创作系统。本指南将引导您在 3 分钟内完成首个解说视频的制作。

---

## 核心 Multi-Agent 智能体协同创作流

### ① 🎬 总控导演 (DirectorAgent)
- 全局任务拆解与管线编排，实时调度视觉、编剧、调音与剪辑各专家智能体。

### ② 👁️ 画面视觉分析师 (VisualCriticAgent)
- 调用 FFmpeg 探针智能分析镜头切点、情绪反转与高能段落，完成精准多模态切片。

### ③ ✍️ 金牌编剧 (ScreenwriterAgent)
- 结合镜头切片与自反思完播率评分机制，撰写 0~3s 黄金 Hook 与第一人称高能剧情独白。

### ④ 🎙️ 声乐调音师 (VoiceArtistAgent)
- 智能匹配 Edge-TTS / GPT-SoVITS 深度克隆音色，合成 48kHz 高保真独白音频并挂载 A1 轨。

### ⑤ 🎛️ 混音剪辑师 (SoundEngineerAgent)
- 5 轨磁性多轨时间轴毫秒级对齐（音画偏差 < 8ms），自动挂载 BGM -18% 智能闪避。

### ⑥ 🔍 质量验收员 (QualityReviewerAgent)
- 严格核验字幕逐字对齐公差、多轨剪映草稿兼容性与违禁词，输出最终 `.draft` 工程。
"#.into(),
            related: vec!["guide-detect-master".into(), "guide-script-copilot".into(), "guide-tts-cloning".into()],
        });

        reg.register(HelpTopic {
            id: "guide-detect-master".into(),
            title: "🎞️ 智能拆条与镜头分割高阶技巧".into(),
            summary: Some("深入理解场景变色、光影突变与多视角镜头精准切分参数与技巧。".into()),
            category: HelpCategory::Guide,
            keywords: vec![
                "拆条".into(),
                "镜头分割".into(),
                "转场检测".into(),
                "帧率".into(),
            ],
            content: r#"# 智能拆条与镜头分割高阶指南

镜头拆条是第一人称解说制作的根基。精准的拆条能大幅提升剪辑的卡点节奏感。

---

## 拆条阈值设置建议

1. **标准电影/电视剧 (阈值 27~30)**
   适用于镜头剪辑较慢、光影过渡自然的影视作品。
2. **动漫/高帧率游戏 (阈值 32~35)**
   由于动画转场颜色对比剧烈，建议适当提高拆条敏感度，防止误切。
3. **低画质/老电影 (阈值 22~25)**
   老旧影片噪声较多，降低阈值可防止漏切关键镜头。

---

## 技巧与注意事项
- **静音段预处理**: 开启“自动裁切片头片尾静音”，可提升 15% 的算法分析效率。
- **关键帧锁定**: 拆条完成后，可在预览面板上手动微调切点或合并相邻短镜头。
"#
            .into(),
            related: vec!["guide-quick-start".into(), "guide-compose-timeline".into()],
        });

        reg.register(HelpTopic {
            id: "guide-script-copilot".into(),
            title: "📝 AI 文案大模型与第一人称独白调优".into(),
            summary: Some("如何利用内置 Prompt 模板撰写爆款第一人称电影解说脚本。".into()),
            category: HelpCategory::Guide,
            keywords: vec![
                "文案".into(),
                "脚本".into(),
                "第一人称".into(),
                "Prompt".into(),
                "大模型".into(),
            ],
            content: r#"# AI 文案大模型与第一人称独白调优

第一人称解说不同于传统旁白，它要求文案以“主人公自身视角的内心独白”切入，建立极强的人设带入感。

---

## 第一人称脚本黄金三要素

### 1. 黄金前 3 秒 Hook 钩子
- *示例*: “当我睁开眼时，发现自己身处 3000 米深的深海废墟，而氧气只剩最后 40 秒……”
- *法则*: 直奔危机时刻，不要做平铺直叙的背景介绍。

### 2. 情感起伏与内心情绪
- 在 AI 脚本面板中选择「沉浸心理独白」预设。
- 加入拟态助词与情绪转折（如：“我犹豫了”、“那一刻，我的血液仿佛冻结了”）。

### 3. 字数与语速匹配
- 推荐语速: 280 ~ 320 字/分钟。
- 单个镜头文案长度控制在 15~35 字，确保播放时不拖泥带水。
"#
            .into(),
            related: vec!["guide-tts-cloning".into(), "guide-quick-start".into()],
        });

        reg.register(HelpTopic {
            id: "guide-tts-cloning".into(),
            title: "🎙️ 音色克隆与 TTS 高保真情感配音指南".into(),
            summary: Some("零样本 10 秒音色克隆、情感语调控制与采样率配置最佳实践。".into()),
            category: HelpCategory::Guide,
            keywords: vec![
                "TTS".into(),
                "配音".into(),
                "音色克隆".into(),
                "情感语调".into(),
                "采样率".into(),
            ],
            content: r#"# 音色克隆与 TTS 高保真情感配音指南

splicr 搭载了基于神经网络的 24kHz 高保真语音合成引擎与零样本（Zero-Shot）音色克隆模块。

---

## 零样本音色克隆 3 步法

1. **录制/上传高质量参考音频**
   - 长度: 5 ~ 15 秒（清晰无杂音）。
   - 内容: 保持朗读语调平稳自然，无背景音乐干扰。
2. **提取音频声学特征向量**
   - 系统将自动去除背景噪音并提取音色 Speaker Embedding。
3. **试听与预设保存**
   - 试听生成的专属音色，命名并保存至您的个人音色库中。

---

## 情感与语调调节提示
- **悬疑解说**: 将语速调至 `0.9x`，适当降低音调 `Pitch -2`。
- **热血动漫**: 将语速调至 `1.15x`，提升音高 `Pitch +3`。
"#
            .into(),
            related: vec![
                "guide-subtitle-styling".into(),
                "guide-script-copilot".into(),
            ],
        });

        reg.register(HelpTopic {
            id: "guide-subtitle-styling".into(),
            title: "🎨 电影级字幕与双语动态特效配置".into(),
            summary: Some("定制电影感金黄描边、高对比底纹与卡拉 OK 逐字亮色字幕样式。".into()),
            category: HelpCategory::Guide,
            keywords: vec![
                "字幕".into(),
                "特效".into(),
                "双语".into(),
                "描边".into(),
                "字体".into(),
            ],
            content: r#"# 电影级字幕与双语动态特效配置

专业的字幕渲染能大幅提升视频的高级感与完播率。

---

## 推荐配色与样式配置

### 1. 经典电影琥珀金 (Filmmaker Amber Gold)
- **字体**: Inter / Noto Sans SC (ExtraBold)
- **主字颜色**: `#F5C842` (琥珀金)
- **描边颜色**: `#0B0B0D` (3px 黑色硬描边)
- **阴影发光**: `0px 4px 16px rgba(245, 200, 66, 0.4)`

### 2. 双语对照字幕 (Bilingual Subtitles)
- 顶部放大中文主字幕（字号 24pt），底部放置英文对照字幕（字号 14pt，半透明 `#A1A1AA`）。
- 开启「逐字卡点亮色」，音频播报到当前字词时自动变为高亮白色。
"#
            .into(),
            related: vec!["guide-tts-cloning".into(), "guide-export-preset".into()],
        });

        reg.register(HelpTopic {
            id: "guide-compose-timeline".into(),
            title: "🔀 音画自动精准对齐与卡点混剪算法".into(),
            summary: Some("了解音频波形匹配、静音切除与 B-Roll 画面智能覆盖机制。".into()),
            category: HelpCategory::Guide,
            keywords: vec![
                "对齐".into(),
                "卡点".into(),
                "混剪".into(),
                "波形".into(),
                "时间轴".into(),
            ],
            content: r#"# 音画自动精准对齐与卡点混剪算法

splicr 的自动对齐引擎能够自动将合成的语音脚本与视频镜头时间轴进行毫秒级匹配。

---

## 对齐算法的工作原理

1. **Voice VAD 静音切除**: 自动分析配音语音中的无声间隙，去除无效停顿。
2. **镜头时长重映射 (Time Stretch & Retime)**:
   - 若镜头比配音长: 自动切除尾帧或插入平滑慢动作。
   - 若镜头比配音短: 智能补帧或从素材库无缝抽调 B-Roll 补充画面。
3. **卡点音频交叉淡入淡出**: 视频背景音乐（BGM）在有独白语音时自动降低 `6dB`（Ducking 闪避）。
"#
            .into(),
            related: vec!["guide-export-preset".into(), "guide-detect-master".into()],
        });

        reg.register(HelpTopic {
            id: "guide-export-preset".into(),
            title: "📤 短视频平台多分辨率与高清渲染 Preset".into(),
            summary: Some("抖音、快手、B站、YouTube Shorts 等平台最佳导出参数手册。".into()),
            category: HelpCategory::Guide,
            keywords: vec!["导出".into(), "渲染".into(), "4K".into(), "短视频".into(), "Preset".into(), "H.264".into()],
            content: r#"# 短视频平台高清导出预设手册

针对不同播放平台，使用匹配的编码参数可避免视频上传后被平台二次压缩抹糊。

---

## 平台参数配置速查表

| 目标平台 | 分辨率 | 宽高比 | 帧率 | 推荐码率 (Bitrate) | 编码格式 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **抖音 / 快手 / Shorts** | 1080x1920 | 9:16 (竖屏) | 60 fps | 12,000 kbps (CBR) | H.264 / AAC |
| **B站 / YouTube (4K)** | 3840x2160 | 16:9 (横屏) | 60 fps | 35,000 kbps (VBR) | HEVC (H.265) |
| **小红书 / 微信视频号** | 1080x1440 | 3:4 (竖屏) | 30 fps | 10,000 kbps (CBR) | H.264 / AAC |

> **提示**: 勾选「硬件加速 (Hardware Acceleration)」，Apple Silicon 芯片将使用 VideoToolbox 硬编，速度提升 5 倍以上。
"#.into(),
            related: vec!["trouble-ffmpeg-cuda".into(), "guide-quick-start".into()],
        });

        // 2. 技术参考 (Reference)
        reg.register(HelpTopic {
            id: "ref-project-schema".into(),
            title: "📖 `.splicr.json` 工程结构与数据契约规范".into(),
            summary: Some("splicr 核心工程文件格式规范、轨道契约与本地 JSON 模式描述。".into()),
            category: HelpCategory::Reference,
            keywords: vec!["工程文件".into(), "JSON".into(), "Schema".into(), "数据契约".into()],
            content: r#"# `.splicr.json` 工程文件规范描述

splicr 的工程文件采用轻量且跨平台兼容的 JSON 数据格式保存。每个解说工程对应一个独立的 `.splicr.json` 结构。

```json
{
  "id": "prj_9a746e9",
  "name": "太阳神纪元 第01集",
  "version": "1.0.1",
  "created_at": "2026-08-06T12:00:00Z",
  "media_files": [
    { "id": "m1", "path": "/media/scene1.mp4", "kind": "video", "duration": 42.5 }
  ],
  "timeline": {
    "tracks": [
      { "id": "track_video", "kind": "video", "clips": [] },
      { "id": "track_audio", "kind": "audio", "clips": [] }
    ]
  }
}
```

---

## 关键字段说明
- `media_files`: 保存所有导入原始音视频素材的本地绝对路径与 Probe 探针元数据。
- `scripts`: 保存 AI 导出的每一句分镜头解说文案、TTS 语音文件路径与时间偏移。
"#.into(),
            related: vec!["ref-keyboard-shortcuts".into(), "faq-local-privacy".into()],
        });

        reg.register(HelpTopic {
            id: "ref-keyboard-shortcuts".into(),
            title: "⌨️ 效率极客快捷键全景图".into(),
            summary: Some("提升创作速度的全键盘快捷键映射与命令面板呼出。".into()),
            category: HelpCategory::Reference,
            keywords: vec![
                "快捷键".into(),
                "组合键".into(),
                "效率".into(),
                "命令面板".into(),
            ],
            content: r#"# 效率极客快捷键速查表

熟练使用快捷键可大幅减少鼠标点击，将工作流效率提升 300%。

---

## 常用核心快捷键

- `⌘ + K` / `Ctrl + K`: **呼出全局命令面板 (Command Palette)**
- `⌘ + R` / `Ctrl + R`: **启动 Multi-Agent 智能体创作团队**
- `⌘ + .` / `Ctrl + .`: **立即终止 / 取消当前正在运行的流水线**
- `⌘ + S` / `Ctrl + S`: **保存当前解说工程到磁盘**
- `⌘ + N` / `Ctrl + N`: **新建空白解说工程**
- `⌘ + O` / `Ctrl + O`: **打开批量素材导入选择器**
- `⌘ + ,` / `Ctrl + ,`: **打开系统偏好设置**
- `Esc`: **关闭当前打开的弹窗或 Modal**
"#
            .into(),
            related: vec!["guide-quick-start".into()],
        });

        // 3. 故障排查 (Troubleshooting)
        reg.register(HelpTopic {
            id: "trouble-ffmpeg-cuda".into(),
            title: "⚡ 硬件加速与 FFmpeg 编解码驱动诊断".into(),
            summary: Some("解决 FFmpeg 编解码器未找到、GPU 硬编失败或预览卡顿的诊断指南。".into()),
            category: HelpCategory::Troubleshooting,
            keywords: vec![
                "FFmpeg".into(),
                "硬件加速".into(),
                "GPU".into(),
                "NVENC".into(),
                "Metal".into(),
                "卡顿".into(),
            ],
            content: r#"# 硬件加速与 FFmpeg 编解码诊断指南

如果遇到视频渲染缓慢、预览卡顿或提示“Encoder Not Found”，请参考本指南排查。

---

## 常见硬件加速驱动配置

### 1. macOS (Apple Silicon M1/M2/M3/M4)
- **硬编引擎**: VideoToolbox (默认开启)
- **检查状态**: 打开设置 -> 诊断引擎 -> 检查 `h264_videotoolbox` 是否为 Green。

### 2. Windows / Linux (NVIDIA 显卡)
- **硬编引擎**: NVENC (`h264_nvenc` / `hevc_nvenc`)
- **要求**: 需安装最新 NVIDIA 显卡驱动 (Driver version ≥ 535.xx)。

### 3. CPU 软编回退 (Fallback)
若 GPU 驱动不可用，系统会自动安全回退至高品质 `libx264` 软编模式。
"#
            .into(),
            related: vec![
                "trouble-path-permission".into(),
                "guide-export-preset".into(),
            ],
        });

        reg.register(HelpTopic {
            id: "trouble-path-permission".into(),
            title: "🛡️ 磁盘存储与访问权限修复指南".into(),
            summary: Some("解决 macOS 沙盒权限限制、路径不存在与工程文件只读错误。".into()),
            category: HelpCategory::Troubleshooting,
            keywords: vec!["权限".into(), "沙盒".into(), "磁盘".into(), "macOS".into(), "文件丢失".into()],
            content: r#"# 磁盘存储与访问权限修复指南

当应用提示“无法写入文件”、“只读权限”或素材导入失败时，请检查以下设置：

---

## 修复步骤

1. **检查目录读写权限**
   确保工程存储目录位于用户的主目录（如 `~/Documents` 或 `~/Desktop`），避免保存在系统根目录 `/` 或临时目录 `/tmp` 中。

2. **macOS 隐私与安全性授权**
   - 打开系统设置 -> 隐私与安全性 -> 文件和文件夹。
   - 确保给 **splicr** 勾选了「文稿」与「Downloads」读取权限。

3. **修复丢失的素材**
   若移动了原始视频文件的位置，可以在「媒体资产中心」点击「重新关联路径」一键批量修复。
"#.into(),
            related: vec!["ref-project-schema".into(), "faq-local-privacy".into()],
        });

        // 4. FAQ (常见问题)
        reg.register(HelpTopic {
            id: "faq-local-privacy".into(),
            title: "🔒 本地离线部署与数据隐私安全 FAQ".into(),
            summary: Some("关于数据隐私、离线运行与大模型 Token 消耗的常见疑难解答。".into()),
            category: HelpCategory::Faq,
            keywords: vec!["隐私".into(), "数据安全".into(), "离线".into(), "云端".into(), "FAQ".into()],
            content: r#"# 本地离线部署与数据隐私安全 FAQ

### Q1: splicr 会上传我的视频素材到云端服务器吗？
**答**: 绝对不会。splicr 是一款 100% 本地桌面软件。您的所有视频文件、帧分析、语音音频以及生成的字幕均仅保存在您本地的电脑磁盘上。

### Q2: 软件可以在断网（无网络连接）的环境下使用吗？
**答**: 可以。智能拆条、FFmpeg 剪辑、TTS 语音合成与导出渲染均支持完全离线运行。

### Q3: 应用需要用户登录或注册账号吗？
**答**: 不需要。splicr 坚守无登录设计原则（No-Login Policy），打开即用，无任何个人数据收集。
"#.into(),
            related: vec!["faq-supported-formats".into(), "ref-project-schema".into()],
        });

        reg.register(HelpTopic {
            id: "faq-supported-formats".into(),
            title: "🎬 适配媒体格式与编码规范 FAQ".into(),
            summary: Some("主流视频封装格式（MP4/MOV/MKV）、音频编码与色彩空间支持说明。".into()),
            category: HelpCategory::Faq,
            keywords: vec!["格式".into(), "MP4".into(), "MOV".into(), "MKV".into(), "4K".into(), "HDR".into()],
            content: r#"# 适配媒体格式与编码规范 FAQ

### Q1: 哪些视频格式支持最好的解说体验？
**答**: 推荐使用 `MP4 (H.264/AAC)` 或 `MOV` 格式。系统原生针对此格式进行了 GPU 硬解码加速优化。

### Q2: 支持 HDR 视频或 10-bit 色深素材吗？
**答**: 支持。splicr 底层集成了 FFmpeg 7.0+ 引擎，在处理 HDR10 / Dolby Vision 素材时，会自动色彩映射（Color Tone-mapping）至 SDR 标准 SDR BT.709，防止导出后色彩偏灰发白。
"#.into(),
            related: vec!["guide-export-preset".into(), "trouble-ffmpeg-cuda".into()],
        });

        reg.register(HelpTopic {
            id: "faq-perf-optimization".into(),
            title: "🚀 渲染性能调优与多核并行计算 FAQ".into(),
            summary: Some("内存占用优化、GPU 缓存清理与长视频渲染加速技巧。".into()),
            category: HelpCategory::Faq,
            keywords: vec![
                "性能".into(),
                "优化".into(),
                "内存".into(),
                "缓存".into(),
                "多核".into(),
            ],
            content: r#"# 渲染性能调优与多核并行计算 FAQ

### Q1: 处理 2 小时以上的长视频时感到轻微卡顿怎么办？
**答**:
1. 在设置中开启「分块并行处理 (Chunked Parallel Execution)」。
2. 定期在设置 -> 存储管理 中点击「一键清理 FFmpeg 临帧缓存」。

### Q2: 多核 CPU 资源如何全速调用？
**答**: splicr 基于 Tokio 异步多线程架构，默认会自动分配所有物理 CPU 核心参与音视频并发编解码。
"#
            .into(),
            related: vec!["trouble-ffmpeg-cuda".into(), "guide-quick-start".into()],
        });

        reg
    }

    pub fn register(&mut self, topic: HelpTopic) {
        self.topics.insert(topic.id.clone(), topic);
    }

    pub fn list_all(&self) -> Vec<&HelpTopic> {
        let mut list: Vec<&HelpTopic> = self.topics.values().collect();
        list.sort_by(|a, b| a.id.cmp(&b.id));
        list
    }

    pub fn list_by_category(&self, cat: HelpCategory) -> Vec<&HelpTopic> {
        let mut list: Vec<&HelpTopic> =
            self.topics.values().filter(|t| t.category == cat).collect();
        list.sort_by(|a, b| a.id.cmp(&b.id));
        list
    }

    pub fn get(&self, id: &str) -> Result<&HelpTopic, anyhow::Error> {
        self.topics
            .get(id)
            .ok_or_else(|| anyhow::anyhow!("未找到帮助主题: {id}"))
    }

    pub fn search(&self, query: &str) -> Vec<SearchHit> {
        if query.trim().is_empty() {
            return vec![];
        }
        let q = query.to_lowercase();
        let mut hits = vec![];
        for t in self.topics.values() {
            let mut score = 0;
            if t.title.to_lowercase().contains(&q) {
                score += 10;
            }
            if t.keywords.iter().any(|k| k.to_lowercase().contains(&q)) {
                score += 5;
            }
            if t.content.to_lowercase().contains(&q) {
                score += 1;
            }
            if score > 0 {
                hits.push(SearchHit {
                    id: t.id.clone(),
                    topic_id: t.id.clone(),
                    title: t.title.clone(),
                    score,
                    snippet: t.content.chars().take(80).collect(),
                });
            }
        }
        hits.sort_by(|a, b| {
            b.score
                .cmp(&a.score)
                .then_with(|| a.topic_id.cmp(&b.topic_id))
        });
        hits
    }
}
